import io
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from fastapi.testclient import TestClient

from app.main import app
from app.services.template_mimic_service import TemplateMimicService
from app.schemas.template_mimic import RoleCandidate, ElementType


def _create_sample_master_pptx() -> bytes:
    """Creates an in-memory sample 16:9 widescreen master template."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.500)
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Cover slide
    s1 = prs.slides.add_slide(blank_layout)
    tb1 = s1.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(2.0))
    p1 = tb1.text_frame.paragraphs[0]
    r1 = p1.add_run()
    r1.text = "Enterprise Presentation Title"
    r1.font.name = "Arial"
    r1.font.size = Pt(40)
    r1.font.color.rgb = RGBColor(0, 47, 108)

    # Slide 2: Two card layout
    s2 = prs.slides.add_slide(blank_layout)
    # Header
    tb_hdr = s2.shapes.add_textbox(Inches(1.0), Inches(0.5), Inches(11.3), Inches(0.8))
    p_hdr = tb_hdr.text_frame.paragraphs[0]
    r_hdr = p_hdr.add_run()
    r_hdr.text = "CATEGORY SHOWCASE"
    r_hdr.font.name = "Arial"
    r_hdr.font.size = Pt(22)
    r_hdr.font.color.rgb = RGBColor(0, 47, 108)

    # Card 1 container
    card1 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(2.0), Inches(4.5), Inches(4.0))
    card1.fill.solid()
    card1.fill.fore_color.rgb = RGBColor(240, 244, 248)

    # Card 1 text
    c1_txt = s2.shapes.add_textbox(Inches(1.8), Inches(2.5), Inches(3.8), Inches(2.0))
    p_c1 = c1_txt.text_frame.add_paragraph()
    p_c1.text = "Sample Employee Name\nSenior Engineer\nCity Office"
    p_c1.font.size = Pt(14)

    # Card 2 container
    card2 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.5), Inches(2.0), Inches(4.5), Inches(4.0))
    card2.fill.solid()
    card2.fill.fore_color.rgb = RGBColor(240, 244, 248)

    # Card 2 text
    c2_txt = s2.shapes.add_textbox(Inches(6.8), Inches(2.5), Inches(3.8), Inches(2.0))
    p_c2 = c2_txt.text_frame.add_paragraph()
    p_c2.text = "Second Candidate Record\nLead Architect\nRegional Hub"
    p_c2.font.size = Pt(14)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_template_mimic_analysis_and_serialization():
    content = _create_sample_master_pptx()
    config = TemplateMimicService.analyze_and_register_template("corporate_master.pptx", content)

    assert config.is_valid is True
    assert config.slide_count == 2
    assert config.aspect_ratio == "16:9"
    assert config.slide_width_in == 13.333
    assert config.slide_height_in == 7.500
    assert "002F6C" in config.theme.detected_colors
    assert "F0F4F8" in config.theme.detected_colors
    assert "Arial" in config.theme.detected_fonts

    # Verify Slide 2 layout analysis
    slide2 = config.slides[1]
    assert len(slide2.elements) >= 5
    assert len(slide2.content_clusters) == 2

    # Verify reload from disk
    reloaded = TemplateMimicService.load_template_config(config.template_id)
    assert reloaded is not None
    assert reloaded.template_id == config.template_id
    assert len(reloaded.slides) == 2


def test_template_mimic_api_workflow():
    client = TestClient(app)
    content = _create_sample_master_pptx()

    # Test Upload
    res = client.post(
        "/api/templates/mimic/upload",
        files={"file": ("test_master.pptx", content, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    template_id = data["template_id"]

    # Test Get
    get_res = client.get(f"/api/templates/mimic/{template_id}")
    assert get_res.status_code == 200
    cfg = get_res.json()
    assert cfg["name"] == "Test Master"

    # Test Update Role
    first_elem = cfg["slides"][1]["elements"][0]
    elem_id = first_elem["element_id"]
    role_res = client.post(
        f"/api/templates/mimic/{template_id}/role",
        json={
            "slide_index": 1,
            "element_id": elem_id,
            "role": "STATIC",
            "user_confirmed": True,
            "notes": "Verified company brand container",
        },
    )
    assert role_res.status_code == 200
    updated = role_res.json()
    updated_elem = next(e for e in updated["slides"][1]["elements"] if e["element_id"] == elem_id)
    assert updated_elem["role"] == "STATIC"
    assert updated_elem["user_confirmed"] is True


def test_invalid_template_rejection():
    client = TestClient(app)
    # 1. Non-pptx file
    res1 = client.post(
        "/api/templates/mimic/upload",
        files={"file": ("corrupted.pdf", b"%PDF-1.4 dummy content", "application/pdf")},
    )
    assert res1.status_code == 400
    assert "Only PowerPoint" in res1.json()["detail"]

    # 2. Corrupted pptx bytes
    res2 = client.post(
        "/api/templates/mimic/upload",
        files={"file": ("broken.pptx", b"NOT_A_VALID_ZIP_OR_PPTX", "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
    )
    assert res2.status_code == 400
    assert "not a valid PPTX" in res2.json()["detail"]
