import re
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse

from app.schemas.template_mimic import (
    TemplateMimicConfig,
    TemplateUploadResponse,
    UpdateElementRoleRequest,
    ConfigureLayoutRequest,
    RoleCandidate,
)
from app.services.template_mimic_service import TemplateMimicService
from app.core.config import settings

router = APIRouter(prefix="/api/templates/mimic", tags=["Template Mimic"])

HEX_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


@router.get("", response_model=List[TemplateMimicConfig])
def list_mimic_templates():
    """Returns all analyzed template mimic configurations."""
    return TemplateMimicService.list_template_configs()


@router.post("/upload", response_model=TemplateUploadResponse)
async def upload_and_analyze_template(file: UploadFile = File(...)):
    """
    Ingests and analyzes a generic PowerPoint template.
    Extracts visual layout, theme colors, typography, element geometry, and candidate roles.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    ext = Path(file.filename).suffix.lower()
    if ext != ".pptx":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PowerPoint presentations (.pptx) are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    try:
        config = TemplateMimicService.analyze_and_register_template(file.filename, content)
        return TemplateUploadResponse(
            success=True,
            template_id=config.template_id,
            message="Template analyzed and registered successfully.",
            config=config,
            warnings=config.validation_warnings,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze template: {str(e)}")


@router.get("/{template_id}", response_model=TemplateMimicConfig)
def get_mimic_template(template_id: str):
    if not HEX_ID_PATTERN.match(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID format.")

    config = TemplateMimicService.load_template_config(template_id)
    if not config:
        raise HTTPException(status_code=404, detail="Template configuration not found.")
    return config


@router.post("/{template_id}/role", response_model=TemplateMimicConfig)
def update_element_role_endpoint(template_id: str, req: UpdateElementRoleRequest):
    """
    Allows HR to confirm or toggle an element's role between STATIC, REPLACEABLE_TEXT, REPLACEABLE_IMAGE, etc.
    """
    if not HEX_ID_PATTERN.match(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID format.")

    try:
        updated_config = TemplateMimicService.update_element_role(
            template_id=template_id,
            slide_index=req.slide_index,
            element_id=req.element_id,
            new_role=req.role,
            user_confirmed=req.user_confirmed,
            notes=req.notes,
        )
        if req.target_field:
            TemplateMimicService.configure_slide_layout(
                template_id=template_id,
                slide_index=req.slide_index,
                field_mappings={req.element_id: req.target_field},
            )
            updated_config = TemplateMimicService.load_template_config(template_id)
        return updated_config
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/{template_id}/layout", response_model=TemplateMimicConfig)
def configure_slide_layout_endpoint(template_id: str, req: ConfigureLayoutRequest):
    """
    Configures slide layout role (COVER, CONTENT, CLOSING) and explicit field bindings.
    """
    if not HEX_ID_PATTERN.match(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID format.")

    try:
        updated_config = TemplateMimicService.configure_slide_layout(
            template_id=template_id,
            slide_index=req.slide_index,
            layout_role=req.layout_role,
            field_mappings=req.field_mappings,
        )
        return updated_config
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/{template_id}/renders/{filename}")
def get_template_slide_render(template_id: str, filename: str):
    """Safely serves rendered slide PNG previews."""
    if not HEX_ID_PATTERN.match(template_id):
        raise HTTPException(status_code=400, detail="Invalid template ID format.")

    clean_filename = Path(filename).name
    render_dir = TemplateMimicService.get_template_storage_dir(template_id) / "renders"
    target_path = (render_dir / clean_filename).resolve()

    if not str(target_path).startswith(str(render_dir)) or not target_path.exists():
        raise HTTPException(status_code=404, detail="Rendered slide preview not found.")

    return FileResponse(path=target_path, media_type="image/png")
