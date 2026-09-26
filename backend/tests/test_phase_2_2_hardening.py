import pytest
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail
from app.services.mapping_service import validate_mapping_config
from tests.test_mapping_service import mock_inspection


def test_invalid_template_slide_index():
    inspection = mock_inspection([("Shape1", "Sample Text")])
    cfg = FieldMappingConfig(
        template_slide_index=5,  # Out of bounds (inspection slide count is 1)
        employee_name=FieldMappingDetail(shape_name="Shape1"),
    )
    res = validate_mapping_config(cfg, inspection)
    assert res.valid is False
    assert len(res.structured_errors) > 0
    assert res.structured_errors[0].code == "INVALID_SLIDE_INDEX"


def test_structured_error_details():
    inspection = mock_inspection([("Shape1", "Text1")])
    cfg = FieldMappingConfig(
        employee_name=FieldMappingDetail(shape_name="Shape1"),
        designation=FieldMappingDetail(shape_name="Shape1"),  # Ambiguous
    )
    res = validate_mapping_config(cfg, inspection)
    assert res.valid is False
    assert len(res.structured_errors) > 0
    assert res.structured_errors[0].code == "AMBIGUOUS_SHAPE_MAPPING"
    assert res.structured_errors[0].field == "designation"
