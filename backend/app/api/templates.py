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
    try:
        saved_file_path = save_uploaded_file(
            file,
            settings.TEMPLATE_UPLOADS_DIR,
            allowed_extensions={".pptx"},
        )
        saved_path = str(saved_file_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded template: {str(e)}")

    file.file.seek(0)
    content = await file.read()

    result = inspect_powerpoint_template(content, file.filename)
    result.saved_path = saved_path
    return result
