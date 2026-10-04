import pytest
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail, SlotMappingDetail
from app.services.template_registry_service import template_registry
from app.services.mapping_service import validate_mapping_config, calculate_template_readiness

NJ_TEMPLATE_ID = "046f2871d4ee4c53b2ee3d469a795432"


def test_original_bug_multi_card_mapping_validation_and_readiness_convergence():
    """
    REGRESSION TEST FOR ORIGINAL BUG:
    Saving a valid SlotMappingDetail-based multi-card mapping must produce:
    mapping_status = 'valid' AND generation_readiness = 'ready_for_generation'
    """
    meta = template_registry.get_template(NJ_TEMPLATE_ID)
    assert meta is not None

    version_obj = meta.versions[0]
    tpl_dir = template_registry._get_template_dir(NJ_TEMPLATE_ID)
    
    # Load version inspection data
    import json
    from app.schemas.template import TemplateInspectionResponse
    with open(tpl_dir / "inspection_v1.json", "r", encoding="utf-8") as f:
        inspection = TemplateInspectionResponse(**json.load(f))

    # Construct valid multi-card slot mapping WITHOUT top-level single-card fields
    slots = [
        SlotMappingDetail(
            slot_index=i,
            employee_name=FieldMappingDetail(shape_name=f"TextBox {shape_id}"),
            photo_placeholder=FieldMappingDetail(shape_name=f"Picture {pic_id}"),
        )
        for i, (shape_id, pic_id) in enumerate([
            (8, 24), (12, 26), (16, 28), (18, 30), (20, 32), (22, 34), (40, 42)
        ])
    ]
    mapping = FieldMappingConfig(template_slide_index=0, slots=slots)

    # Validate mapping config against inspection
    val_res = validate_mapping_config(mapping, inspection)
    assert val_res.valid is True
    assert val_res.mapping_status == "valid"

    # Calculate readiness
    readiness_res = calculate_template_readiness(inspection, mapping)
    assert readiness_res.mapping_status == "valid"
    assert readiness_res.generation_readiness == "ready_for_generation"

    # Update template registry mapping
    updated_meta = template_registry.update_template_mapping(NJ_TEMPLATE_ID, mapping, version_number=1)
    assert updated_meta.mapping_status == "valid"
    assert updated_meta.generation_readiness == "ready_for_generation"
    assert updated_meta.versions[0].generation_readiness == "ready_for_generation"


from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_endpoint_readiness_convergence():
    """Verify GET /api/templates, GET /api/templates/{id}, and GET /api/templates/{id}/readiness converge."""
    res_list = client.get("/api/templates")
    assert res_list.status_code == 200
    meta_from_list = next((t for t in res_list.json() if t["template_id"] == NJ_TEMPLATE_ID), None)
    assert meta_from_list is not None

    res_single = client.get(f"/api/templates/{NJ_TEMPLATE_ID}")
    assert res_single.status_code == 200
    meta_single = res_single.json()

    res_readiness = client.get(f"/api/templates/{NJ_TEMPLATE_ID}/readiness")
    assert res_readiness.status_code == 200
    readiness_single = res_readiness.json()

    # All 3 endpoints must agree
    assert meta_from_list["generation_readiness"] == meta_single["generation_readiness"]
    assert meta_single["generation_readiness"] == readiness_single["generation_readiness"]
    assert meta_single["mapping_status"] == readiness_single["mapping_status"]
