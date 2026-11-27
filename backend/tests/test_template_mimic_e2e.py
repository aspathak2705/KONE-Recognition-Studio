"""
End-to-end integration test for Phase 3: Complete Template Mimic Workflow.
Verifies:
1. Template ingestion and persistence.
2. Template reuse from storage.
3. Employee dataset processing & photo association.
4. Award grouping.
5. Template-aware presentation generation with slide previews.
6. Persistent presentation history entry verification.
7. Verification that default generation mode remains unaffected.
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
from app.api.generation import get_presentation_history
from app.schemas.photo_matching import (
    EmployeePhotoMatch,
    PhotoFileMetadata,
    PhotoMatchStatus,
)


def _create_mock_session_and_employees(session_id: str, count: int = 4) -> list[EmployeePhotoMatch]:
    session_dir = settings.PHOTO_SESSIONS_DIR.resolve() / session_id
    photos_dir = session_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (80, 80), color=(15, 34, 64))
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
            width=80,
            height=80,
            format="PNG",
            relative_path=f"photos/{file_id}.png",
            file_size_bytes=len(png_bytes),
            preview_url=f"/api/photos/{session_id}/{file_id}/preview",
        )

        award = "Safety Excellence" if i < 2 else "Customer Focus"
        emp_name = f"Honoree {i + 1}"
        employees.append(
            EmployeePhotoMatch(
                employee_record_index=i,
                employee_name=emp_name,
                normalized_name=emp_name.lower(),
                award_name=award,
                designation="Senior Technician",
                branch="KONE Espoo",
                match_status=PhotoMatchStatus.MATCHED,
                is_resolved=True,
                assigned_file=photo_meta,
            )
        )

    return employees


def _build_test_master_pptx() -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.500)
    blank_layout = prs.slide_layouts[6]

    # Cover Slide
    s1 = prs.slides.add_slide(blank_layout)
    tb_cov = s1.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.0), Inches(1.5))
    r_cov = tb_cov.text_frame.paragraphs[0].add_run()
    r_cov.text = "Corporate Master Deck"
    r_cov.font.name = "Georgia"
    r_cov.font.size = Pt(36)
    r_cov.font.color.rgb = RGBColor(0, 47, 108)

    # Content Slide with 2 Card Containers
    s2 = prs.slides.add_slide(blank_layout)
    # Header
    tb_h = s2.shapes.add_textbox(Inches(1.0), Inches(0.5), Inches(11.0), Inches(0.8))
    rh = tb_h.text_frame.paragraphs[0].add_run()
    rh.text = "CATEGORY BANNER"
    rh.font.name = "Georgia"
    rh.font.size = Pt(22)
    rh.font.color.rgb = RGBColor(0, 47, 108)

    # Card 1 container
    c1 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(2.0), Inches(4.8), Inches(4.2))
    c1.fill.solid()
    c1.fill.fore_color.rgb = RGBColor(245, 247, 250)

    # Card 1 text
    c1_txt = s2.shapes.add_textbox(Inches(1.8), Inches(2.5), Inches(4.0), Inches(1.8))
    r1 = c1_txt.text_frame.add_paragraph().add_run()
    r1.text = "Sample Employee Name"
    r1.font.name = "Georgia"
    r1.font.size = Pt(16)
    r1.font.color.rgb = RGBColor(0, 47, 108)

    # Card 2 container
    c2 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7.0), Inches(2.0), Inches(4.8), Inches(4.2))
    c2.fill.solid()
    c2.fill.fore_color.rgb = RGBColor(245, 247, 250)

    # Card 2 text
    c2_txt = s2.shapes.add_textbox(Inches(7.3), Inches(2.5), Inches(4.0), Inches(1.8))
    r2 = c2_txt.text_frame.add_paragraph().add_run()
    r2.text = "Second Candidate Record"
    r2.font.name = "Georgia"
    r2.font.size = Pt(16)
    r2.font.color.rgb = RGBColor(0, 47, 108)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_complete_template_mimic_e2e_workflow():
    session_id = uuid.uuid4().hex
    employees = _create_mock_session_and_employees(session_id, count=4)
    master_bytes = _build_test_master_pptx()

    # 1. Template Ingestion & Analysis
    template_config = TemplateMimicService.analyze_and_register_template(
        "global_kone_master.pptx", master_bytes
    )
    assert template_config.is_valid is True
    tpl_id = template_config.template_id

    # 2. Reusability: Load template config back from disk
    reloaded_config = TemplateMimicService.load_template_config(tpl_id)
    assert reloaded_config is not None
    assert reloaded_config.template_id == tpl_id
    assert len(reloaded_config.slides) == 2

    # 3. Render using TemplateAwareAdapter
    gen_res = TemplateAwareAdapter.render_presentation(
        session_id=session_id,
        employees=employees,
        template_config=reloaded_config,
    )

    assert gen_res.is_valid is True
    assert gen_res.can_download is True
    assert gen_res.total_employees == 4
    assert gen_res.award_categories_count == 2
    assert Path(gen_res.pptx_path).exists()

    # 4. History persistence check
    history = get_presentation_history()
    assert history.total_count >= 1
    found = next((item for item in history.items if item.generation_id == gen_res.generation_id), None)
    assert found is not None
    assert found.record_count == 4
    assert found.can_download is True
    assert "Global Kone Master" in found.presentation_name


def test_regression_default_generation_mode():
    session_id = uuid.uuid4().hex
    employees = _create_mock_session_and_employees(session_id, count=2)

    gen_res = DynamicPresentationService.generate_presentation_from_dataset(
        session_id=session_id,
        employees=employees,
    )

    assert gen_res.is_valid is True
    assert gen_res.total_employees == 2
    assert Path(gen_res.pptx_path).exists()
