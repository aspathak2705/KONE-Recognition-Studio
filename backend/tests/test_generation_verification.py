import pytest
import hashlib
from pptx import Presentation
from io import BytesIO
from app.schemas.recognition import RecognitionRecord
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail
from app.services.pptx_generator import generate_powerpoint_presentation
from tests.test_pptx_generator import create_mock_template_pptx


def test_source_template_immutability():
    tpl_bytes = create_mock_template_pptx()
    original_hash = hashlib.sha256(tpl_bytes).hexdigest()

    records = [
        RecognitionRecord(
            row_number=2,
            employee_name="Alice Smith",
            designation="Senior Developer",
            branch="Pune",
            award_name="Excellence Award",
        )
    ]

    cfg = FieldMappingConfig(
        employee_name=FieldMappingDetail(shape_name="EmployeeName"),
        designation=FieldMappingDetail(shape_name="Designation"),
        branch=FieldMappingDetail(shape_name="Branch"),
        award_name=FieldMappingDetail(shape_name="AwardName"),
    )

    generate_powerpoint_presentation(
        template_content=tpl_bytes,
        template_filename="test_template.pptx",
        excel_records=records,
        mapping_config=cfg,
        source_excel_file_id="exc123",
        source_template_file_id="tpl123",
    )

    post_hash = hashlib.sha256(tpl_bytes).hexdigest()
    assert original_hash == post_hash, "Source template content bytes were modified during generation!"


def test_nested_group_text_substitution():
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Create group shape
    shape1 = slide.shapes.add_textbox(100, 100, 200, 50)
    shape1.name = "NormalShape"

    # Add shapes to group
    group_shape = slide.shapes.add_group_shape()
    group_shape.name = "GroupA"
    nested_shape = group_shape.shapes.add_textbox(100, 200, 200, 50)
    nested_shape.name = "NestedEmployeeName"
    nested_shape.text_frame.text = "Original Nested Text"

    bio = BytesIO()
    prs.save(bio)
    tpl_bytes = bio.getvalue()

    records = [
        RecognitionRecord(
            row_number=2,
            employee_name="Nested Alice",
            designation="Engineer",
            branch="Pune",
            award_name="Star Award",
        )
    ]

    cfg = FieldMappingConfig(
        employee_name=FieldMappingDetail(shape_name="NestedEmployeeName"),
        designation=FieldMappingDetail(shape_name="NormalShape"),
        branch=FieldMappingDetail(shape_name="NormalShape"),
        award_name=FieldMappingDetail(shape_name="NormalShape"),
    )

    res = generate_powerpoint_presentation(
        template_content=tpl_bytes,
        template_filename="grouped_template.pptx",
        excel_records=records,
        mapping_config=cfg,
        source_excel_file_id="exc123",
        source_template_file_id="tpl123",
    )

    assert res.status == "completed"
    assert res.slide_count == 1


def test_empty_records_rejection():
    tpl_bytes = create_mock_template_pptx()
    cfg = FieldMappingConfig(
        employee_name=FieldMappingDetail(shape_name="EmployeeName"),
    )

    with pytest.raises(ValueError, match="Cannot generate presentation from an empty recognition dataset"):
        generate_powerpoint_presentation(
            template_content=tpl_bytes,
            template_filename="test.pptx",
            excel_records=[],
            mapping_config=cfg,
            source_excel_file_id="exc123",
            source_template_file_id="tpl123",
        )
