from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.template import TemplateInspectionResponse
from app.services.template_inspector import inspect_powerpoint_template
from app.services.file_storage import save_uploaded_file
from app.core.config import settings

router = APIRouter(prefix="/api/templates", tags=["Templates"])


@router.post("/inspect", response_model=TemplateInspectionResponse)
async def inspect_template_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    saved_path = None
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
    result.saved_path = None  # Do not expose absolute local filesystem path
    return result

