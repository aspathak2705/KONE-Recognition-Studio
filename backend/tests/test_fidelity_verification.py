import io
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.fidelity import TemplateFidelityManifest, VerificationStatus
from app.services.template_registry_service import template_registry
from app.services.template_fidelity_validator import TemplateFidelityValidator
from app.core.config import settings

client = TestClient(app)


def test_fidelity_validator_detects_defective_pptx():
    """Negative regression test: Verify that defective PPTX missing photo regions is detected and BLOCKED."""
    # Find New Joiner registered template
    templates = template_registry.list_templates()
    nj_tpl = next((t for t in templates if "New Joiner" in t.name), None)
    assert nj_tpl is not None, "New Joiner template must be registered"

    manifest = template_registry.get_template_fidelity_manifest(nj_tpl.template_id, nj_tpl.current_version)
    assert manifest is not None, "Fidelity manifest must exist for registered New Joiner template"

    # Defective generated file path
    bad_pptx_path = Path(r"C:\Users\athar\Downloads\KONE_Recognition_e3e01648.pptx")
    if not bad_pptx_path.exists():
        pytest.skip("Reference bad PPTX fixture not found in Downloads")

    with open(bad_pptx_path, "rb") as f:
        bad_bytes = f.read()

    # Run validation
    report = TemplateFidelityValidator.validate_presentation(
        generated_pptx_bytes=bad_bytes,
        manifest=manifest,
        expected_records_count=34,
    )

    # Must be BLOCKED due to missing photo regions
    assert report.verification_status == VerificationStatus.BLOCKED
    assert report.photo_slot_result == "FAIL"
    photo_failures = [f for f in report.failures if f.failure_type == "MISSING_PHOTO_REGION"]
    assert len(photo_failures) > 0, "Validator must flag MISSING_PHOTO_REGION on defective generated output"


def test_download_gate_blocks_unverified_generation():
    """Verify that GET /api/generations/{id}/download rejects downloads when validation_status is BLOCKED."""
    fake_gen_id = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    settings.GENERATED_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write mock pptx
    fake_pptx = settings.GENERATED_OUTPUTS_DIR / f"{fake_gen_id}.pptx"
    fake_pptx.write_bytes(b"PK\x03\x04mockpptx")

    # Write mock metadata with BLOCKED status
    fake_meta = settings.GENERATED_OUTPUTS_DIR / f"{fake_gen_id}.json"
    with open(fake_meta, "w", encoding="utf-8") as f:
        json.dump({
            "generation_id": fake_gen_id,
            "status": "completed",
            "validation_status": "BLOCKED",
            "validation_score": 0.4,
        }, f)

    res = client.get(f"/api/generations/{fake_gen_id}/download")
    assert res.status_code == 403
    data = res.json()
    assert "detail" in data
    assert data["detail"]["error"] == "PRESENTATION_NOT_VERIFIED"

    # Cleanup mock files
    fake_pptx.unlink(missing_ok=True)
    fake_meta.unlink(missing_ok=True)


def test_validation_endpoint_returns_report():
    """Verify that GET /api/generations/{id}/validation returns the persisted report."""
    fake_gen_id = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"
    settings.GENERATED_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    fake_report_path = settings.GENERATED_OUTPUTS_DIR / f"{fake_gen_id}_validation.json"
    with open(fake_report_path, "w", encoding="utf-8") as f:
        json.dump({
            "generation_id": fake_gen_id,
            "verification_status": "VERIFIED",
            "overall_score": 1.0,
            "slides_checked": 2,
            "slides_passed": 2,
            "slides_failed": 0,
            "failures": [],
            "warnings": [],
        }, f)

    res = client.get(f"/api/generations/{fake_gen_id}/validation")
    assert res.status_code == 200
    data = res.json()
    assert data["generation_id"] == fake_gen_id
    assert data["verification_status"] == "VERIFIED"

    # Cleanup
    fake_report_path.unlink(missing_ok=True)
