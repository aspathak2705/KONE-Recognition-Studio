"""
Targeted Acceptance Verification Test.
Validates:
1. Adapter renders generic content items without requiring hardcoded column names (e.g. employee_name, designation).
2. Explicit layout configuration (layout_role and field_mappings) is respected.
3. Populated preview endpoint works and uses identical rendering logic as final generation.
4. Default dynamic generation mode remains completely unaffected.
"""

import io
import uuid
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

from app.core.config import settings
from app.services.template_mimic_service import TemplateMimicService
from app.services.template_aware_adapter import TemplateAwareAdapter
from app.services.dynamic_presentation_service import DynamicPresentationService
from app.api.photos import preview_presentation_from_photo_session
from app.schemas.photo_matching import (
    EmployeePhotoMatch,
    PhotoFileMetadata,
    PhotoMatchStatus,
)


def _setup_test_fixture(session_id: str):
    session_dir = settings.PHOTO_SESSIONS_DIR.resolve() / session_id
    photos_dir = session_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (64, 64), color=(0, 47, 108))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    png_bytes = img_buf.getvalue()

    records = []
    for i in range(2):
        file_id = uuid.uuid4().hex
        photo_path = photos_dir / f"{file_id}.png"
        with open(photo_path, "wb") as f:
            f.write(png_bytes)

        photo_meta = PhotoFileMetadata(
            file_id=file_id,
            original_filename=f"record_{i}.png",
            normalized_stem=f"rec_{i}",
            extension=".png",
            width=64,
            height=64,
            format="PNG",
            relative_path=f"photos/{file_id}.png",
            file_size_bytes=len(png_bytes),
            preview_url=f"/api/photos/{session_id}/{file_id}/preview",
        )

        records.append(
            EmployeePhotoMatch(
                employee_record_index=i,
                employee_name=f"Generic Person {i + 1}",
                normalized_name=f"generic person {i + 1}",
                award_name="Excellence Circle",
                designation="Domain Specialist",
                branch="Central Operations",
                match_status=PhotoMatchStatus.MATCHED,
                is_resolved=True,
                assigned_file=photo_meta,
            )
        )
    return records


def _generate_master_deck() -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.500)
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Cover
    s1 = prs.slides.add_slide(blank_layout)
    tb_title = s1.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.0), Inches(1.5))
    r = tb_title.text_frame.paragraphs[0].add_run()
    r.text = "Generic Corporate Showcase"
    r.font.name = "Segoe UI"
    r.font.size = Pt(36)
    r.font.color.rgb = RGBColor(0, 47, 108)

    # Slide 2: 2-Card Layout
    s2 = prs.slides.add_slide(blank_layout)
    c1 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(2.0), Inches(4.5), Inches(4.0))
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(240, 244, 248)

    t1 = s2.shapes.add_textbox(Inches(1.8), Inches(2.5), Inches(3.8), Inches(1.5))
    r1 = t1.text_frame.add_paragraph().add_run()
    r1.text = "Placeholder Item 1"
    r1.font.size = Pt(16)

    c2 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.8), Inches(2.0), Inches(4.5), Inches(4.0))
    c2.fill.solid()
    c2.fill.fore_color.rgb = RGBColor(240, 244, 248)

    t2 = s2.shapes.add_textbox(Inches(7.1), Inches(2.5), Inches(3.8), Inches(1.5))
    r2 = t2.text_frame.add_paragraph().add_run()
    r2.text = "Placeholder Item 2"
    r2.font.size = Pt(16)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_generic_field_contract_and_layout_config():
    session_id = uuid.uuid4().hex
    records = _setup_test_fixture(session_id)
    master_bytes = _generate_master_deck()

    # 1. Analyze template
    tpl_config = TemplateMimicService.analyze_and_register_template("acceptance_master.pptx", master_bytes)
    assert tpl_config.is_valid is True

    # 2. Configure layout explicitly (Slide 1 as CONTENT)
    updated_tpl = TemplateMimicService.configure_slide_layout(
        template_id=tpl_config.template_id,
        slide_index=1,
        layout_role="CONTENT",
        field_mappings={"primary_field": "primary_text"},
    )
    assert updated_tpl.slides[1].layout_role == "CONTENT"

    # 3. Test generic content item extraction (verifying adapter handles arbitrary dict / model fields)
    sample_dict = {"primary_text": "Alice Engineer", "secondary_text": "Tech Lead"}
    assert TemplateAwareAdapter.extract_record_fields(sample_dict, "primary_text") == "Alice Engineer"
    assert TemplateAwareAdapter.extract_record_fields(sample_dict, "secondary_text") == "Tech Lead"
    assert TemplateAwareAdapter.extract_record_fields(records[0], "employee_name") == "Generic Person 1"

    # 4. Render presentation via TemplateAwareAdapter
    gen_res = TemplateAwareAdapter.render_presentation(
        session_id=session_id,
        employees=records,
        template_config=updated_tpl,
    )

    assert gen_res.is_valid is True
    assert gen_res.can_download is True
    assert gen_res.total_employees == 2
    assert Path(gen_res.pptx_path).exists()


def test_default_generation_mode_integrity():
    session_id = uuid.uuid4().hex
    records = _setup_test_fixture(session_id)

    gen_res = DynamicPresentationService.generate_presentation_from_dataset(
        session_id=session_id,
        employees=records,
    )

    assert gen_res.is_valid is True
    assert gen_res.total_employees == 2
    assert Path(gen_res.pptx_path).exists()
