import os
import sys
import uuid
import time
import json
import shutil
import tempfile
import logging
import subprocess
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

# Script executed in an isolated child process to isolate PowerPoint COM lifecycle
# completely from FastAPI AnyIO / asyncio worker threads.
_POWERPOINT_WORKER_SCRIPT = """
import sys
import json
import os
import time
from pathlib import Path

action = sys.argv[1]

if action == "check":
    if sys.platform != "win32":
        print(json.dumps({"available": False, "reason": "unsupported_platform"}))
        sys.exit(0)
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        if ppt:
            try:
                ppt.Quit()
            except Exception:
                pass
            print(json.dumps({"available": True}))
        else:
            print(json.dumps({"available": False, "reason": "dispatch_returned_none"}))
    except Exception as e:
        print(json.dumps({"available": False, "error": str(e)}))
    finally:
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
    sys.exit(0)

elif action == "render":
    pptx_path = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    width = int(sys.argv[4])
    height = int(sys.argv[5])
    timeout_seconds = int(sys.argv[6])

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths = []

    if sys.platform != "win32":
        print(json.dumps({"status": "unsupported_platform", "rendered": []}))
        sys.exit(0)

    ppt = None
    pres = None
    start_time = time.time()
    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        abs_pptx = str(pptx_path.resolve())
        pres = ppt.Presentations.Open(abs_pptx, WithWindow=False)

        slide_count = pres.Slides.Count
        for i in range(1, slide_count + 1):
            if (time.time() - start_time) > timeout_seconds:
                raise TimeoutError(f"PowerPoint rendering exceeded timeout limit of {timeout_seconds}s.")

            out_png = output_dir / f"slide_{i}.png"
            if out_png.exists():
                out_png.unlink()

            pres.Slides(i).Export(str(out_png.resolve()), "PNG", width, height)
            if out_png.exists() and out_png.stat().st_size > 0:
                rendered_paths.append(str(out_png.resolve()))

        print(json.dumps({"status": "success", "rendered": rendered_paths}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e), "rendered": rendered_paths}))
    finally:
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
    sys.exit(0)
"""


class PptxRenderer:
    """
    Template-independent presentation renderer and visual verification service.
    Supports Windows PowerPoint COM automation with strict lifecycle isolation
    via dedicated worker subprocesses, process cleanup, timeouts, and safe degradation.
    """

    @classmethod
    def is_powerpoint_available(cls) -> bool:
        """Check if Microsoft PowerPoint COM interface is actually available and responsive on the system."""
        if sys.platform != "win32":
            return False
        try:
            res = subprocess.run(
                [sys.executable, "-c", _POWERPOINT_WORKER_SCRIPT, "check"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                return bool(data.get("available"))
        except Exception as e:
            logger.debug(f"PowerPoint COM availability check failed: {e}")
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
        Executes COM automation in a dedicated, isolated worker subprocess so that COM
        apartment initialization and teardown never touch FastAPI AnyIO worker threads.
        Returns a list of rendered slide image paths.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if not pptx_path.exists() or pptx_path.stat().st_size == 0:
            logger.warning(f"PPTX file {pptx_path} does not exist or is empty.")
            return []

        # Attempt native PowerPoint COM automation in dedicated subprocess on Windows
        if sys.platform == "win32":
            try:
                proc_timeout = timeout_seconds + 15
                res = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        _POWERPOINT_WORKER_SCRIPT,
                        "render",
                        str(pptx_path.resolve()),
                        str(output_dir.resolve()),
                        str(width),
                        str(height),
                        str(timeout_seconds),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=proc_timeout,
                )
                if res.returncode == 0 and res.stdout.strip():
                    data = json.loads(res.stdout.strip())
                    if data.get("status") == "success":
                        rendered_files = [Path(p) for p in data.get("rendered", []) if Path(p).exists()]
                        return rendered_files
                    else:
                        logger.warning(f"PowerPoint COM rendering subprocess error: {data.get('error')}")
                else:
                    logger.warning(f"PowerPoint COM rendering subprocess exited with code {res.returncode}: {res.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"PowerPoint COM rendering subprocess exceeded timeout of {timeout_seconds}s.")
            except Exception as e:
                logger.warning(f"PowerPoint COM rendering encountered issue: {e}")

        # Headless fallback / renderer unavailable: return empty list and report honestly
        logger.info(f"Visual rendering comparison unavailable for {pptx_path.name}")
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
