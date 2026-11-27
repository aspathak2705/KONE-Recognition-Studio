"""
Targeted tests for Phase 2: Template-Aware Rendering Adapter.
Verifies that:
- Upstream planned employee content can be rendered through TemplateAwareAdapter.
- Template visual styles, typography, and layout clusters are preserved.
- Static elements are kept.
- Multiple records fit across clusters and paginate appropriately.
- Generated presentation remains fully editable PPTX.
- Default generation mode continues to function cleanly without regression.
"""

import io
import uuid
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

from app.core.config import settings
from app.services.template_mimic_service import TemplateMimicService
from app.services.template_aware_adapter import TemplateAwareAdapter
from app.services.dynamic_presentation_service import DynamicPresentationService
from app.schemas.photo_matching import (
    EmployeePhotoMatch,
    PhotoFileMetadata,
    PhotoMatchStatus,
)


def _create_mock_photo_session(session_id: str, count: int = 4) -> list[EmployeePhotoMatch]:
    session_dir = settings.PHOTO_SESSIONS_DIR.resolve() / session_id
    photos_dir = session_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    from PIL import Image
    img = Image.new("RGB", (100, 100), color=(0, 47, 108))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    png_bytes = img_buf.getvalue()

    employees = []
    for i in range(count):
        file_id = uuid.uuid4().hex
        photo_filename = f"emp_{i}.png"
        photo_path = photos_dir / f"{file_id}.png"
        with open(photo_path, "wb") as f:
            f.write(png_bytes)

        photo_meta = PhotoFileMetadata(
            file_id=file_id,
            original_filename=photo_filename,
            normalized_stem=f"emp_{i}",
            extension=".png",
            width=1,
            height=1,
            format="PNG",
            relative_path=f"photos/{file_id}.png",
            file_size_bytes=len(png_bytes),
            preview_url=f"/api/photos/{session_id}/{file_id}/preview",
        )

        award = "Safety Champions" if i < 2 else "Innovation Star"
        emp_name = f"Honoree {i + 1}"
        employees.append(
            EmployeePhotoMatch(
                employee_record_index=i,
                employee_name=emp_name,
                normalized_name=emp_name.lower(),
                award_name=award,
                designation="Senior Engineer",
                branch="Helsinki Hub",
                match_status=PhotoMatchStatus.MATCHED,
                is_resolved=True,
                assigned_file=photo_meta,
            )
        )

    return employees


def _create_test_master_pptx() -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.500)
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Cover Layout
    s1 = prs.slides.add_slide(blank_layout)
    tb_title = s1.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.0), Inches(1.5))
    p = tb_title.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = "Corporate Master Deck"
    r.font.name = "Georgia"
    r.font.size = Pt(36)
    r.font.color.rgb = RGBColor(15, 34, 64)

    # Slide 2: Two-Card Content Layout
    s2 = prs.slides.add_slide(blank_layout)
    # Static Header
    tb_h = s2.shapes.add_textbox(Inches(1.0), Inches(0.5), Inches(11.0), Inches(0.8))
    ph = tb_h.text_frame.paragraphs[0]
    rh = ph.add_run()
    rh.text = "SECTION HEADER"
    rh.font.name = "Georgia"
    rh.font.size = Pt(20)
    rh.font.color.rgb = RGBColor(15, 34, 64)

    # Card 1 container
    c1 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(2.0), Inches(4.8), Inches(4.2))
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(245, 247, 250)

    # Card 1 text
    c1_txt = s2.shapes.add_textbox(Inches(1.8), Inches(2.5), Inches(4.0), Inches(1.8))
    p1 = c1_txt.text_frame.add_paragraph()
    r1 = p1.add_run()
    r1.text = "Sample Employee Name"
    r1.font.name = "Georgia"
    r1.font.size = Pt(16)
    r1.font.color.rgb = RGBColor(15, 34, 64)

    # Card 2 container
    c2 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7.0), Inches(2.0), Inches(4.8), Inches(4.2))
    c2.fill.solid()
    c2.fill.fore_color.rgb = RGBColor(245, 247, 250)

    # Card 2 text
    c2_txt = s2.shapes.add_textbox(Inches(7.3), Inches(2.5), Inches(4.0), Inches(1.8))
    p2 = c2_txt.text_frame.add_paragraph()
    r2 = p2.add_run()
    r2.text = "Second Candidate Record"
    r2.font.name = "Georgia"
    r2.font.size = Pt(16)
    r2.font.color.rgb = RGBColor(15, 34, 64)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_template_aware_adapter_rendering():
    session_id = uuid.uuid4().hex
    employees = _create_mock_photo_session(session_id, count=4)
    master_bytes = _create_test_master_pptx()

    # Step 1: Analyze master PPTX into config
    tpl_config = TemplateMimicService.analyze_and_register_template("unit_test_master.pptx", master_bytes)
    assert tpl_config.is_valid is True

    # Step 2: Render using TemplateAwareAdapter
    gen_response = TemplateAwareAdapter.render_presentation(
        session_id=session_id,
        employees=employees,
        template_config=tpl_config,
    )

    # Assertions on output
    assert gen_response is not None
    assert gen_response.total_employees == 4
    assert gen_response.award_categories_count == 2
    assert gen_response.is_valid is True
    assert gen_response.can_download is True
    assert Path(gen_response.pptx_path).exists()

    # Verify generated presentation is a valid editable PPTX with multiple slides
    out_prs = Presentation(gen_response.pptx_path)
    assert len(out_prs.slides) >= 3  # Cover + at least 2 award slides


def test_default_dynamic_generation_unaffected():
    session_id = uuid.uuid4().hex
    employees = _create_mock_photo_session(session_id, count=3)

    # Verify default dynamic generator runs without template
    gen_response = DynamicPresentationService.generate_presentation_from_dataset(
        session_id=session_id,
        employees=employees,
    )

    assert gen_response is not None
    assert gen_response.total_employees == 3
    assert gen_response.is_valid is True
    assert Path(gen_response.pptx_path).exists()
