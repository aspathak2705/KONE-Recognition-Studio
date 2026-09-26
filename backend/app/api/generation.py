from pathlib import Path
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import FileResponse

from app.schemas.mapping import (
    FieldMappingConfig,
    MappingValidationResponse,
    TemplateReadinessResponse,
    GenerationRequest,
    GenerationResponse,
)
from app.schemas.template import TemplateInspectionResponse
from app.services.template_inspector import inspect_powerpoint_template
from app.services.excel_parser import parse_and_validate_excel
from app.services.mapping_service import (
    validate_mapping_config,
    calculate_template_readiness,
)
from app.services.pptx_generator import generate_powerpoint_presentation
from app.core.config import settings

router = APIRouter(tags=["Generation & Mapping"])


import re

HEX_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


def get_stored_file_path(file_id: str, subfolder: str, extension: str) -> Path:
    # Reject file IDs that fail 32-char hex UUID format validation
    if not file_id or not HEX_ID_PATTERN.match(file_id):
        raise HTTPException(status_code=400, detail="Invalid file identifier format: Expected 32-character hex ID.")
        
    target_dir = settings.STORAGE_DIR / subfolder
    target_path = (target_dir / f"{file_id}{extension}").resolve()
    
    # Ensure resolved path is within STORAGE_DIR
    if not str(target_path).startswith(str(settings.STORAGE_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Access denied: invalid file path.")

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"File identifier '{file_id}' not found.")
    return target_path


@router.get("/api/templates/{file_id}/readiness", response_model=TemplateReadinessResponse)
def get_template_readiness(file_id: str):
    tpl_path = get_stored_file_path(file_id, "uploads/templates", ".pptx")
    with open(tpl_path, "rb") as f:
        content = f.read()
    
    inspection = inspect_powerpoint_template(content, tpl_path.name)
    inspection.template_id = file_id
    return calculate_template_readiness(inspection)


@router.post("/api/templates/mapping/validate", response_model=MappingValidationResponse)
def validate_mapping_endpoint(file_id: str, mapping_config: FieldMappingConfig):
    tpl_path = get_stored_file_path(file_id, "uploads/templates", ".pptx")
    with open(tpl_path, "rb") as f:
        content = f.read()

    inspection = inspect_powerpoint_template(content, tpl_path.name)
    return validate_mapping_config(mapping_config, inspection)


@router.post("/api/recognitions/generate", response_model=GenerationResponse)
def generate_presentation_endpoint(req: GenerationRequest):
    excel_path = get_stored_file_path(req.excel_file_id, "uploads/excel", ".xlsx")

    with open(excel_path, "rb") as f:
        excel_content = f.read()

    excel_res = parse_and_validate_excel(excel_content, excel_path.name)
    if not excel_res.valid or not excel_res.records:
        raise HTTPException(
            status_code=400,
            detail="Uploaded Excel file is invalid or contains no valid recognition records.",
        )

    # 1. Check if template_file_id is a registered template in template_registry
    from app.services.template_registry_service import template_registry
    registered_meta = template_registry.get_template(req.template_file_id)
    
    if registered_meta:
        tpl_content, active_version = template_registry.get_template_version_pptx(
            req.template_file_id, req.template_version
        )
        tpl_filename = active_version.filename
        mapping = req.mapping_config or active_version.mapping_config
        if not mapping:
            raise HTTPException(status_code=400, detail="Template mapping configuration is missing.")
    else:
        # Fallback to direct uploads/templates path for backwards compatibility
        tpl_path = get_stored_file_path(req.template_file_id, "uploads/templates", ".pptx")
        with open(tpl_path, "rb") as f:
            tpl_content = f.read()
        tpl_filename = tpl_path.name
        mapping = req.mapping_config

        tpl_inspection = inspect_powerpoint_template(tpl_content, tpl_filename)
        readiness = calculate_template_readiness(tpl_inspection, mapping)
        if readiness.generation_readiness == "blocked_by_validation":
            raise HTTPException(
                status_code=400,
                detail=f"Template mapping is invalid: {'; '.join(readiness.errors)}",
            )

    try:
        gen_res = generate_powerpoint_presentation(
            template_content=tpl_content,
            template_filename=tpl_filename,
            excel_records=excel_res.records,
            mapping_config=mapping,
            source_excel_file_id=req.excel_file_id,
            source_template_file_id=req.template_file_id,
        )
        if registered_meta:
            gen_res.template_version = active_version.version_number
            gen_res.template_file_hash = active_version.file_hash

            # Update persisted job metadata JSON file
            job_meta_path = settings.GENERATED_OUTPUTS_DIR / f"{gen_res.generation_id}.json"
            import json
            with open(job_meta_path, "w", encoding="utf-8") as f:
                json.dump(gen_res.dict(), f, indent=2)

        return gen_res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presentation generation failed: {str(e)}")


@router.get("/api/generations/{generation_id}/download")
def download_generated_presentation(generation_id: str):
    if not generation_id or not HEX_ID_PATTERN.match(generation_id):
        raise HTTPException(status_code=400, detail="Invalid generation identifier format: Expected 32-character hex ID.")

    gen_dir = settings.GENERATED_OUTPUTS_DIR.resolve()
    gen_path = (gen_dir / f"{generation_id}.pptx").resolve()
    
    if not str(gen_path).startswith(str(gen_dir)):
        raise HTTPException(status_code=400, detail="Access denied: invalid file path.")

    if not gen_path.exists():
        raise HTTPException(status_code=404, detail="Generated presentation file not found.")

    return FileResponse(
        path=gen_path,
        filename=f"KONE_Recognition_{generation_id[:8]}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )

