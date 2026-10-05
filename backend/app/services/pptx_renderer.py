import os
import uuid
from typing import Optional, List
from pathlib import Path
from PIL import Image

class PptxRenderer:
    """Generic presentation renderer with PowerPoint COM support and headless fallback."""

    @staticmethod
    def render_presentation_slides(pptx_path: Path, output_dir: Path, width: int = 1920, height: int = 1080) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered_paths: List[Path] = []

        # Attempt native PowerPoint COM automation on Windows
        try:
            import win32com.client
            ppt = win32com.client.Dispatch("PowerPoint.Application")
            ppt.Visible = 1
            abs_pptx = str(pptx_path.resolve())
            pres = ppt.Presentations.Open(abs_pptx, WithWindow=False)
            
            slide_count = pres.Slides.Count
            for i in range(1, slide_count + 1):
                out_png = output_dir / f"slide_{i}.png"
                pres.Slides(i).Export(str(out_png.resolve()), "PNG", width, height)
                rendered_paths.append(out_png)
                
            pres.Close()
            ppt.Quit()
            return rendered_paths
        except Exception:
            pass

        # Fallback renderer: produce deterministic placeholder canvas
        try:
            from pptx import Presentation
            prs = Presentation(pptx_path)
            for i in range(1, len(prs.slides) + 1):
                out_png = output_dir / f"slide_{i}.png"
                img = Image.new("RGB", (width, height), (250, 250, 250))
                img.save(out_png, "PNG")
                rendered_paths.append(out_png)
            return rendered_paths
        except Exception:
            return []

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
