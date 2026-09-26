import pytest
from app.schemas.template import TemplateInspectionResponse, SlideInfo, TextShapeInfo
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail, MappingStatus, GenerationReadiness
from app.services.mapping_service import auto_suggest_mapping, validate_mapping_config, calculate_template_readiness


def mock_inspection(shapes: list) -> TemplateInspectionResponse:
    text_shapes = [
        TextShapeInfo(
            shape_name=name,
            shape_type="TEXT_BOX",
            text=text,
            left_inches=1.0,
            top_inches=1.0,
            width_inches=3.0,
            height_inches=1.0,
        )
        for name, text in shapes
    ]
    slide = SlideInfo(
        slide_number=1,
        shape_count=len(shapes),
        text_shapes=text_shapes,
        placeholders_count=0,
    )
    return TemplateInspectionResponse(
        valid=True,
        template_id="tpl123",
        filename="template.pptx",
        slide_count=1,
        slide_width_inches=13.33,
        slide_height_inches=7.5,
        aspect_ratio="16:9",
        slides=[slide],
    )


def test_auto_suggest_mapping():
    inspection = mock_inspection([
        ("EmployeeName", "John Doe"),
        ("Designation", "Manager"),
        ("Branch", "Chennai"),
        ("AwardName", "Star Award"),
    ])
    suggested = auto_suggest_mapping(inspection)
    assert suggested.employee_name.shape_name == "EmployeeName"
    assert suggested.designation.shape_name == "Designation"
    assert suggested.branch.shape_name == "Branch"
    assert suggested.award_name.shape_name == "AwardName"


def test_validate_mapping_config_valid():
    inspection = mock_inspection([
        ("EmployeeName", "John Doe"),
        ("Designation", "Manager"),
        ("Branch", "Chennai"),
        ("AwardName", "Star Award"),
    ])
    cfg = auto_suggest_mapping(inspection)
    res = validate_mapping_config(cfg, inspection)
    assert res.valid is True
    assert res.mapping_status == MappingStatus.VALID
    assert len(res.errors) == 0


def test_validate_mapping_config_conflicting():
    inspection = mock_inspection([("Shape1", "Sample Text")])
    cfg = FieldMappingConfig(
        employee_name=FieldMappingDetail(shape_name="Shape1"),
        designation=FieldMappingDetail(shape_name="Shape1"),  # conflict
    )
    res = validate_mapping_config(cfg, inspection)
    assert res.valid is False
    assert res.mapping_status == MappingStatus.INVALID
    assert "Conflicting mapping" in res.errors[0]


def test_calculate_template_readiness():
    inspection = mock_inspection([
        ("EmployeeName", "John Doe"),
        ("Designation", "Manager"),
        ("Branch", "Chennai"),
        ("AwardName", "Star Award"),
    ])
    readiness = calculate_template_readiness(inspection)
    assert readiness.generation_readiness == GenerationReadiness.READY_FOR_GENERATION
