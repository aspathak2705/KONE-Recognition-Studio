import pytest
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail, SlotMappingDetail
from app.services.template_registry_service import template_registry
from app.services.mapping_service import validate_mapping_config, calculate_template_readiness

Q4_TEMPLATE_ID = "f45e5538d2184bac921bf070270caa95"


def test_q4_multilayout_mapping_ready():
    """Verify Q4 R&R multi-layout mapping validates and sets generation_readiness = 'ready_for_generation'."""
    meta = template_registry.get_template(Q4_TEMPLATE_ID)
    assert meta is not None

    tpl_dir = template_registry._get_template_dir(Q4_TEMPLATE_ID)
    import json
    from app.schemas.template import TemplateInspectionResponse
    with open(tpl_dir / "inspection_v1.json", "r", encoding="utf-8") as f:
        inspection = TemplateInspectionResponse(**json.load(f))

    # Map Slide 2 (2-card layout)
    slots = [
        SlotMappingDetail(slot_index=0, employee_name=FieldMappingDetail(shape_name="Text Placeholder 8"), photo_placeholder=FieldMappingDetail(shape_name="Picture 17")),
        SlotMappingDetail(slot_index=1, employee_name=FieldMappingDetail(shape_name="Text Placeholder 8"), photo_placeholder=FieldMappingDetail(shape_name="Picture 9")),
    ]
    mapping = FieldMappingConfig(template_slide_index=1, slots=slots)

    val_res = validate_mapping_config(mapping, inspection)
    assert val_res.valid is True
    assert val_res.mapping_status == "valid"

    updated = template_registry.update_template_mapping(Q4_TEMPLATE_ID, mapping, version_number=1)
    assert updated.mapping_status == "valid"
    assert updated.generation_readiness == "ready_for_generation"
    assert updated.versions[0].generation_readiness == "ready_for_generation"
