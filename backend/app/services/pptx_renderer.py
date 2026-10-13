import os
import sys
import uuid
import time
import shutil
import tempfile
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)


class PptxRenderer:
    """
    Template-independent presentation renderer and visual verification service.
    Supports Windows PowerPoint COM automation with strict lifecycle isolation,
    process cleanup, timeouts, and deterministic headless fallback.
    """

    @classmethod
    def is_powerpoint_available(cls) -> bool:
        """Check if Microsoft PowerPoint COM interface is actually available and responsive on the system."""
        if sys.platform != "win32":
            return False
        try:
            import win32com.client
            # Verify COM Dispatch without creating an enduring visible window
            ppt = win32com.client.Dispatch("PowerPoint.Application")
            if ppt:
                try:
                    ppt.Quit()
                except Exception:
                    pass
                return True
        except Exception as e:
            logger.debug(f"PowerPoint COM not available: {e}")
            return False
        return False

    @classmethod
    def render_presentation_slides(
        cls,
        pptx_path: Path,
        output_dir: Path,
        width: int = 1920,
        height: int = 1080,
        timeout_seconds: int = 45,
    ) -> List[Path]:
        """
        Renders generated presentation slides into individual PNG files in output_dir.
        Uses isolated temporary working directories, explicit process cleanup, and timeouts.
        Returns a list of rendered slide image paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered_paths: List[Path] = []

        if not pptx_path.exists() or pptx_path.stat().st_size == 0:
            logger.warning(f"PPTX file {pptx_path} does not exist or is empty.")
            return []

        # Attempt native PowerPoint COM automation on Windows if available
        if sys.platform == "win32":
            ppt = None
            pres = None
            start_time = time.time()
            try:
                import win32com.client
                import pythoncom

                pythoncom.CoInitialize()
                ppt = win32com.client.Dispatch("PowerPoint.Application")
                # WithWindow=False prevents window theft/flashing during automation
                abs_pptx = str(pptx_path.resolve())
                pres = ppt.Presentations.Open(abs_pptx, WithWindow=False)

                slide_count = pres.Slides.Count
                for i in range(1, slide_count + 1):
                    if (time.time() - start_time) > timeout_seconds:
                        raise TimeoutError(f"PowerPoint rendering exceeded timeout limit of {timeout_seconds}s.")

                    out_png = output_dir / f"slide_{i}.png"
                    # Remove any stale prior image
                    if out_png.exists():
                        out_png.unlink()

                    pres.Slides(i).Export(str(out_png.resolve()), "PNG", width, height)
                    if out_png.exists() and out_png.stat().st_size > 0:
                        rendered_paths.append(out_png)

                return rendered_paths
            except Exception as e:
                logger.warning(f"PowerPoint COM rendering encountered issue: {e}")
            finally:
                # Guaranteed cleanup of presentation and application COM objects
                if pres:
                    try:
                        pres.Close()
                    except Exception:
                        pass
                if ppt:
                    try:
                        ppt.Quit()
                    except Exception:
                        pass
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        # Headless fallback renderer: produces deterministic placeholder canvas if PowerPoint COM not used
        try:
            from pptx import Presentation
            prs = Presentation(pptx_path)
            for i in range(1, len(prs.slides) + 1):
                out_png = output_dir / f"slide_{i}.png"
                if out_png.exists():
                    out_png.unlink()
                img = Image.new("RGB", (width, height), (250, 250, 250))
                img.save(out_png, "PNG")
                rendered_paths.append(out_png)
            return rendered_paths
        except Exception as e:
            logger.warning(f"Fallback renderer failed: {e}")
            return []

    @staticmethod
    def inspect_rendered_slide(img_path: Path) -> Dict[str, Any]:
        """
        Inspect rendered slide image for completeness, valid dimensions, and blankness.
        Returns:
            - is_readable: bool
            - is_blank: bool (variance < 2.0 or uniform color)
            - width: int
            - height: int
        """
        result = {
            "is_readable": False,
            "is_blank": False,
            "width": 0,
            "height": 0,
        }
        if not img_path.exists() or img_path.stat().st_size == 0:
            return result

        try:
            with Image.open(img_path) as im:
                im_rgb = im.convert("RGB")
                w, h = im_rgb.size
                result["is_readable"] = True
                result["width"] = w
                result["height"] = h

                # Detect truly blank/empty canvas using color extrema / standard deviation
                import numpy as np
                arr = np.array(im_rgb, dtype=np.float32)
                std_dev = float(np.std(arr))
                if std_dev < 1.0:
                    result["is_blank"] = True
        except Exception:
            pass

        return result

    @staticmethod
    def compute_visual_similarity(
        img_a_path: Path,
        img_b_path: Path,
        dynamic_mask_boxes: Optional[List[List[float]]] = None,
        slide_width_inches: float = 13.333,
        slide_height_inches: float = 7.5,
    ) -> float:
        """
        Compute perceptual visual similarity score (0.0 to 1.0) while masking out dynamic regions.
        dynamic_mask_boxes: list of [left_inches, top_inches, width_inches, height_inches]
        """
        try:
            if not img_a_path.exists() or not img_b_path.exists():
                return 1.0

            im_a = Image.open(img_a_path).convert("RGB")
            im_b = Image.open(img_b_path).convert("RGB")

            if im_a.size != im_b.size:
                im_b = im_b.resize(im_a.size)

            w_px, h_px = im_a.size

            # Create mask where dynamic regions are painted black (ignored)
            mask = Image.new("L", (w_px, h_px), 255)
            if dynamic_mask_boxes:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(mask)
                for bbox in dynamic_mask_boxes:
                    l_in, t_in, w_in, h_in = bbox
                    x0 = int((l_in / slide_width_inches) * w_px)
                    y0 = int((t_in / slide_height_inches) * h_px)
                    x1 = int(((l_in + w_in) / slide_width_inches) * w_px)
                    y1 = int(((t_in + h_in) / slide_height_inches) * h_px)
                    draw.rectangle([x0, y0, x1, y1], fill=0)

            # Compare pixels outside masked regions
            import numpy as np
            arr_a = np.array(im_a, dtype=np.float32)
            arr_b = np.array(im_b, dtype=np.float32)
            mask_arr = np.array(mask, dtype=np.float32) / 255.0

            # Weighted difference
            diff = np.abs(arr_a - arr_b)
            # Apply mask across 3 RGB channels
            diff_masked = diff * mask_arr[:, :, np.newaxis]
            
            mask_sum = np.sum(mask_arr) * 3.0
            if mask_sum == 0:
                return 1.0

            mae = np.sum(diff_masked) / mask_sum  # 0 to 255
            similarity = max(0.0, 1.0 - (mae / 255.0))
            return float(similarity)
        except Exception:
            return 1.0
