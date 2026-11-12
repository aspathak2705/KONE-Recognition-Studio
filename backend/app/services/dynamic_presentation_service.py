import io
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from app.core.config import settings
from app.services.file_storage import atomic_write_json
from app.services.award_grouping_service import group_employees_by_award
from app.services.dynamic_layout_engine import (
    calculate_optimal_slide_layout,
    paginate_award_group,
    SLIDE_WIDTH_IN,
    SLIDE_HEIGHT_IN,
    SIDE_MARGIN_IN,
)
from app.schemas.photo_matching import EmployeePhotoMatch
from app.schemas.dynamic_presentation import (
    DynamicGenerationResponse,
    SlideGeometryFinding,
    AwardGroup,
)

# KONE Enterprise Design System Palette
COLOR_KONE_BLUE = RGBColor(0, 47, 108)         # Deep Corporate Navy
COLOR_KONE_LIGHT_BLUE = RGBColor(0, 114, 206)   # KONE Vibrant Blue
COLOR_SLATE_DARK = RGBColor(30, 41, 59)         # Text Primary
COLOR_SLATE_MUTED = RGBColor(100, 116, 139)     # Text Secondary / Metadata
COLOR_CARD_BG = RGBColor(248, 250, 252)         # Card background
COLOR_CARD_BORDER = RGBColor(226, 232, 240)     # Card subtle border
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_AMBER_ACCENT = RGBColor(217, 119, 6)      # Award pill accent
COLOR_BG_GRADIENT = RGBColor(241, 245, 249)     # Soft canvas background

FONT_FAMILY_PRIMARY = "Segoe UI"


class DynamicPresentationService:
    @classmethod
    def generate_presentation_from_dataset(
        cls,
        session_id: str,
        employees: List[EmployeePhotoMatch],
    ) -> DynamicGenerationResponse:
        """
        Generates an enterprise-grade recognition deck dynamically without templates.
        """
        if not employees:
            raise ValueError("Cannot generate presentation from an empty employee dataset.")

        # Validate that all employees have a resolved, existing photograph
        session_dir = settings.PHOTO_SESSIONS_DIR.resolve() / session_id
        for emp in employees:
            if not emp.is_resolved or not emp.assigned_file:
                raise ValueError(
                    f"Employee '{emp.employee_name}' has no resolved photograph. All photos must be verified before generation."
                )
            photo_disk_path = session_dir / emp.assigned_file.relative_path
            if not photo_disk_path.exists():
                raise ValueError(
                    f"Photograph file for '{emp.employee_name}' was not found at {photo_disk_path}."
                )

        generation_id = uuid.uuid4().hex
        prs = Presentation()
        prs.slide_width = Inches(SLIDE_WIDTH_IN)
        prs.slide_height = Inches(SLIDE_HEIGHT_IN)
        blank_layout = prs.slide_layouts[6]  # completely blank canvas

        # Step 1: Create Cover Slide
        cls._create_cover_slide(prs, blank_layout, len(employees))

        # Step 2: Group employees by Award Category
        award_groups = group_employees_by_award(employees)

        # Step 3: Generate Dynamic Award Slides
        for group in award_groups:
            cls._create_award_slides_for_group(prs, blank_layout, group, session_dir)

        # Step 4: Create Closing Slide
        cls._create_closing_slide(prs, blank_layout)

        # Step 5: Save PPTX File
        settings.GENERATED_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        out_filename = f"{generation_id}.pptx"
        dest_pptx_path = settings.GENERATED_OUTPUTS_DIR / out_filename
        prs.save(str(dest_pptx_path))

        # Step 6: Verify Geometry
        findings = cls._validate_presentation_geometry(prs)

        # Step 7: Persist Generation Metadata
        now_iso = datetime.datetime.utcnow().isoformat()
        response = DynamicGenerationResponse(
            generation_id=generation_id,
            session_id=session_id,
            slide_count=len(prs.slides),
            total_employees=len(employees),
            award_categories_count=len(award_groups),
            award_groups=award_groups,
            download_url=f"/api/generations/{generation_id}/download",
            pptx_path=str(dest_pptx_path),
            is_valid=all(f.severity != "ERROR" for f in findings),
            validation_findings=findings,
            created_at=now_iso,
        )

        job_meta_path = settings.GENERATED_OUTPUTS_DIR / f"{generation_id}.json"
        meta_data = {
            "generation_id": generation_id,
            "session_id": session_id,
            "status": "completed",
            "delivery_status": "READY",
            "validation_status": "VERIFIED",
            "slide_count": len(prs.slides),
            "record_count": len(employees),
            "award_categories_count": len(award_groups),
            "created_at": now_iso,
            "download_url": f"/api/generations/{generation_id}/download",
        }
        atomic_write_json(job_meta_path, meta_data)

        return response

    @classmethod
    def _create_cover_slide(cls, prs, layout, total_employees: int):
        slide = prs.slides.add_slide(layout)

        # Background accent rectangle (Left navy accent bar)
        accent_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), Inches(SLIDE_HEIGHT_IN))
        accent_bar.fill.solid()
        accent_bar.fill.fore_color.rgb = COLOR_KONE_BLUE
        accent_bar.line.color.rgb = COLOR_KONE_BLUE

        # Top KONE pill header
        kone_pill = slide.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(3.0), Inches(0.5))
        tf_pill = kone_pill.text_frame
        p_pill = tf_pill.paragraphs[0]
        p_pill.text = "KONE RECOGNITION STUDIO"
        p_pill.font.name = FONT_FAMILY_PRIMARY
        p_pill.font.size = Pt(13)
        p_pill.font.bold = True
        p_pill.font.color.rgb = COLOR_KONE_LIGHT_BLUE

        # Main Title Box
        title_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(10.5), Inches(2.2))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = "Celebrating Excellence &\nOutstanding Contributions"
        p_title.font.name = FONT_FAMILY_PRIMARY
        p_title.font.size = Pt(40)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_KONE_BLUE

        # Subtitle details
        sub_box = slide.shapes.add_textbox(Inches(1.0), Inches(4.5), Inches(9.0), Inches(1.0))
        tf_sub = sub_box.text_frame
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = f"Honoring {total_employees} Recognized Team Members Across All Categories"
        p_sub.font.name = FONT_FAMILY_PRIMARY
        p_sub.font.size = Pt(18)
        p_sub.font.color.rgb = COLOR_SLATE_MUTED

    @classmethod
    def _create_award_slides_for_group(
        cls,
        prs,
        layout,
        group: AwardGroup,
        session_dir: Path,
    ):
        # Paginate group into balanced slices
        slide_slices = paginate_award_group(group.employee_count, max_density_per_slide=8)
        curr_emp_idx = 0

        for page_idx, count_on_slide in enumerate(slide_slices):
            slice_employees = group.employees[curr_emp_idx : curr_emp_idx + count_on_slide]
            curr_emp_idx += count_on_slide

            slide = prs.slides.add_slide(layout)

            # Slide Header: Category Name + Pagination
            header_box = slide.shapes.add_textbox(Inches(SIDE_MARGIN_IN), Inches(0.4), Inches(11.5), Inches(1.1))
            tf_h = header_box.text_frame
            tf_h.word_wrap = True
            p_cat = tf_h.paragraphs[0]
            p_cat.text = group.award_name.upper()
            p_cat.font.name = FONT_FAMILY_PRIMARY
            p_cat.font.size = Pt(22)
            p_cat.font.bold = True
            p_cat.font.color.rgb = COLOR_KONE_BLUE

            p_sub = tf_h.add_paragraph()
            page_text = f" • Part {page_idx + 1} of {len(slide_slices)}" if len(slide_slices) > 1 else ""
            p_sub.text = f"Award Category{page_text} ({group.employee_count} Recognized)"
            p_sub.font.name = FONT_FAMILY_PRIMARY
            p_sub.font.size = Pt(12)
            p_sub.font.color.rgb = COLOR_SLATE_MUTED

            # Compute dynamic card layout
            max_name_len = max([len(e.employee_name) for e in slice_employees], default=20)
            max_meta_len = max([len(f"{e.designation or ''} {e.branch or ''}") for e in slice_employees], default=25)
            layout_cfg = calculate_optimal_slide_layout(count_on_slide, max_name_len, max_meta_len)

            # Render Cards
            for card_idx, emp in enumerate(slice_employees):
                col = card_idx % layout_cfg.columns
                row = card_idx // layout_cfg.columns

                x_in = layout_cfg.margin_left_in + (col * (layout_cfg.card_width_in + layout_cfg.gap_x_in))
                y_in = layout_cfg.margin_top_in + (row * (layout_cfg.card_height_in + layout_cfg.gap_y_in))

                cls._render_employee_card(
                    slide=slide,
                    emp=emp,
                    session_dir=session_dir,
                    x_in=x_in,
                    y_in=y_in,
                    w_in=layout_cfg.card_width_in,
                    h_in=layout_cfg.card_height_in,
                    image_size_in=layout_cfg.image_size_in,
                    name_font_size=layout_cfg.name_font_size_pt,
                    meta_font_size=layout_cfg.meta_font_size_pt,
                )

    @classmethod
    def _render_employee_card(
        cls,
        slide,
        emp: EmployeePhotoMatch,
        session_dir: Path,
        x_in: float,
        y_in: float,
        w_in: float,
        h_in: float,
        image_size_in: float,
        name_font_size: float,
        meta_font_size: float,
    ):
        # 1. Card container background shape (Rounded rectangle)
        card_rect = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x_in),
            Inches(y_in),
            Inches(w_in),
            Inches(h_in),
        )
        card_rect.fill.solid()
        card_rect.fill.fore_color.rgb = COLOR_CARD_BG
        card_rect.line.color.rgb = COLOR_CARD_BORDER
        card_rect.line.width = Pt(1.0)

        # 2. Insert Employee Photograph
        photo_disk_path = session_dir / emp.assigned_file.relative_path
        photo_x = x_in + 0.15
        photo_y = y_in + (h_in - image_size_in) / 2.0

        slide.shapes.add_picture(
            str(photo_disk_path),
            Inches(photo_x),
            Inches(photo_y),
            width=Inches(image_size_in),
            height=Inches(image_size_in),
        )

        # 3. Employee Text Content (Name, Role, Location)
        text_x = photo_x + image_size_in + 0.15
        text_w = w_in - (image_size_in + 0.35)
        text_box = slide.shapes.add_textbox(
            Inches(text_x),
            Inches(photo_y),
            Inches(text_w),
            Inches(image_size_in),
        )
        tf = text_box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE

        # Employee Name
        p_name = tf.paragraphs[0]
        p_name.text = emp.employee_name
        p_name.font.name = FONT_FAMILY_PRIMARY
        p_name.font.size = Pt(name_font_size)
        p_name.font.bold = True
        p_name.font.color.rgb = COLOR_SLATE_DARK

        # Designation / Role
        if emp.designation:
            p_desig = tf.add_paragraph()
            p_desig.text = emp.designation
            p_desig.font.name = FONT_FAMILY_PRIMARY
            p_desig.font.size = Pt(meta_font_size)
            p_desig.font.color.rgb = COLOR_SLATE_MUTED

        # Branch / Location
        if emp.branch:
            p_branch = tf.add_paragraph()
            p_branch.text = emp.branch
            p_branch.font.name = FONT_FAMILY_PRIMARY
            p_branch.font.size = Pt(max(meta_font_size - 1.0, 8.0))
            p_branch.font.color.rgb = COLOR_KONE_LIGHT_BLUE

    @classmethod
    def _create_closing_slide(cls, prs, layout):
        slide = prs.slides.add_slide(layout)

        # Right accent bar
        accent_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(SLIDE_WIDTH_IN - 0.4),
            Inches(0),
            Inches(0.4),
            Inches(SLIDE_HEIGHT_IN),
        )
        accent_bar.fill.solid()
        accent_bar.fill.fore_color.rgb = COLOR_KONE_LIGHT_BLUE
        accent_bar.line.color.rgb = COLOR_KONE_LIGHT_BLUE

        # Closing Text
        box = slide.shapes.add_textbox(Inches(1.5), Inches(2.8), Inches(10.0), Inches(2.0))
        tf = box.text_frame
        p1 = tf.paragraphs[0]
        p1.text = "Thank You for Your Dedication & Passion"
        p1.font.name = FONT_FAMILY_PRIMARY
        p1.font.size = Pt(36)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_KONE_BLUE

        p2 = tf.add_paragraph()
        p2.text = "KONE • Dedicated to People Flow"
        p2.font.name = FONT_FAMILY_PRIMARY
        p2.font.size = Pt(16)
        p2.font.color.rgb = COLOR_SLATE_MUTED

    @classmethod
    def _validate_presentation_geometry(cls, prs) -> List[SlideGeometryFinding]:
        findings: List[SlideGeometryFinding] = []
        slide_w_in = prs.slide_width.inches
        slide_h_in = prs.slide_height.inches

        for s_idx, slide in enumerate(prs.slides):
            for shape in slide.shapes:
                # Boundary check
                x = shape.left.inches
                y = shape.top.inches
                w = shape.width.inches
                h = shape.height.inches

                if x < -0.05 or y < -0.05 or (x + w) > (slide_w_in + 0.1) or (y + h) > (slide_h_in + 0.1):
                    findings.append(
                        SlideGeometryFinding(
                            slide_index=s_idx + 1,
                            severity="WARNING",
                            issue_type="SHAPE_OUT_OF_BOUNDS",
                            message=f"Shape at ({x:.2f}, {y:.2f}) slightly exceeds slide boundary.",
                        )
                    )

                # Font size validation
                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        if p.font.size and p.font.size.pt < 7.5:
                            findings.append(
                                SlideGeometryFinding(
                                    slide_index=s_idx + 1,
                                    severity="WARNING",
                                    issue_type="MINIMUM_FONT_SIZE",
                                    message=f"Text paragraph '{p.text[:20]}...' has font size {p.font.size.pt}pt below 7.5pt limit.",
                                )
                            )
        return findings
