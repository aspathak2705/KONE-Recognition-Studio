from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.schemas.template import TemplateInspectionResponse
from app.schemas.mapping import FieldMappingConfig, TemplateReadinessResponse
from app.schemas.template_registry import (
    TemplateMetadata,
    TemplateVersion,
    TemplateRegistrationResponse,
)
from app.services.template_registry_service import template_registry
from app.services.template_inspector import inspect_powerpoint_template
from app.services.file_storage import save_uploaded_file
from app.core.config import settings

router = APIRouter(prefix="/api/templates", tags=["Templates & Registry"])


@router.get("", response_model=List[TemplateMetadata])
def list_registered_templates(include_archived: bool = False):
    return template_registry.list_templates(include_archived=include_archived)


@router.get("/{template_id}", response_model=TemplateMetadata)
def get_registered_template(template_id: str):
    meta = template_registry.get_template(template_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
    return meta


@router.post("/register", response_model=TemplateRegistrationResponse)
async def register_template(
    name: str = Form(...),
    file: UploadFile = File(...),
    existing_template_id: Optional[str] = Form(None),
):
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PowerPoint (.pptx) templates are allowed.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded template file is empty.")

    return template_registry.register_or_update_template(
        name=name,
        content=content,
        filename=file.filename,
        existing_template_id=existing_template_id,
    )


@router.put("/{template_id}/mapping", response_model=TemplateMetadata)
def update_template_mapping_endpoint(
    template_id: str,
    mapping: FieldMappingConfig,
    version_number: Optional[int] = None,
):
    return template_registry.update_template_mapping(
        template_id=template_id,
        mapping=mapping,
        version_number=version_number,
    )


@router.post("/{template_id}/archive", response_model=TemplateMetadata)
def archive_template_endpoint(template_id: str):
    return template_registry.archive_template(template_id)


# Legacy & helper endpoints
@router.post("/inspect", response_model=TemplateInspectionResponse)
async def inspect_template_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    saved_file_path, file_id = save_uploaded_file(
        file,
        settings.TEMPLATE_UPLOADS_DIR,
        allowed_extensions={".pptx"},
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
    )

    file.file.seek(0)
    content = await file.read()

    result = inspect_powerpoint_template(content, file.filename)
    result.template_id = file_id
    result.saved_path = None
    return result
