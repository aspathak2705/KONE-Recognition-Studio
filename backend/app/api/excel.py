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
    try:
        saved_file_path = save_uploaded_file(
            file,
            settings.EXCEL_UPLOADS_DIR,
            allowed_extensions={".xlsx"},
        )
        saved_path = str(saved_file_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded file: {str(e)}")

    file.file.seek(0)
    content = await file.read()
    
    result = parse_and_validate_excel(content, file.filename)
    result.saved_path = saved_path
    return result
