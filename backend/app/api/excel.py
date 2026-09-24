from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.recognition import ExcelValidationResponse, SchemaResponse
from app.services.excel_parser import parse_and_validate_excel, get_schema_info
from app.services.file_storage import save_uploaded_file
from app.core.config import settings

router = APIRouter(prefix="/api/recognitions", tags=["Recognitions"])


@router.get("/schema", response_model=SchemaResponse)
def get_excel_schema():
    return get_schema_info()


@router.post("/validate-excel", response_model=ExcelValidationResponse)
async def validate_excel_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
        
    saved_path = None
    saved_file_path, file_id = save_uploaded_file(
        file,
        settings.EXCEL_UPLOADS_DIR,
        allowed_extensions={".xlsx"},
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
    )

    file.file.seek(0)
    content = await file.read()
    
    result = parse_and_validate_excel(content, file.filename)
    result.file_id = file_id
    result.saved_path = None  # Do not expose absolute local filesystem path
    return result

