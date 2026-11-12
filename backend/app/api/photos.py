import re
import uuid
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.services.excel_parser import parse_and_validate_excel
from app.services.photo_matching_service import PhotoMatchingService
from app.schemas.photo_matching import (
    PhotoMatchingSessionResponse,
    ResolveAssociationRequest,
    DatasetFinalizeResponse,
)

router = APIRouter(prefix="/api/photos", tags=["Employee Photos"])
HEX_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


@router.post("/process-dataset", response_model=PhotoMatchingSessionResponse)
async def process_dataset(
    excel_file: UploadFile = File(...),
    photo_files: Optional[List[UploadFile]] = File(None),
    photo_zip: Optional[UploadFile] = File(None),
):
    """
    Primary HR entrypoint:
    Accepts:
    1. Excel recognition file
    2. List of photo files (directory upload) OR a ZIP folder of photos
    Executes parsing, image verification, matching, and returns the review state.
    """
    if not excel_file.filename:
        raise HTTPException(status_code=400, detail="Missing Excel file.")

    excel_bytes = await excel_file.read()
    excel_res = parse_and_validate_excel(excel_bytes, excel_file.filename)
    if not excel_res.valid or not excel_res.records:
        raise HTTPException(
            status_code=400,
            detail=f"Excel validation failed: {', '.join([e.message for e in excel_res.errors]) if excel_res.errors else 'No valid records found.'}",
        )

    session_id = uuid.uuid4().hex
    uploaded_photos = []

    # Handle directory upload of individual photo files
    if photo_files:
        for p_file in photo_files:
            if not p_file.filename:
                continue
            p_bytes = await p_file.read()
            photo_meta = PhotoMatchingService.save_photo_file(session_id, p_file.filename, p_bytes)
            uploaded_photos.append(photo_meta)

    # Handle ZIP folder fallback
    if photo_zip and photo_zip.filename:
        z_bytes = await photo_zip.read()
        zip_photos = PhotoMatchingService.extract_photos_from_zip(session_id, z_bytes)
        uploaded_photos.extend(zip_photos)

    session_res = PhotoMatchingService.match_photos_to_employees(
        session_id=session_id,
        records=excel_res.records,
        uploaded_photos=uploaded_photos,
    )
    return session_res


@router.get("/{session_id}/state", response_model=PhotoMatchingSessionResponse)
def get_session_state(session_id: str):
    if not HEX_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session identifier format.")

    session_res, _ = PhotoMatchingService.load_session_state(session_id)
    if not session_res:
        raise HTTPException(status_code=404, detail="Photo matching session not found.")
    return session_res


@router.post("/{session_id}/resolve", response_model=PhotoMatchingSessionResponse)
def resolve_association(session_id: str, req: ResolveAssociationRequest):
    if not HEX_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session identifier format.")

    try:
        updated_session = PhotoMatchingService.resolve_association(
            session_id=session_id,
            employee_record_index=req.employee_record_index,
            file_id=req.file_id,
            confirm_reuse=req.confirm_reuse,
        )
        return updated_session
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/{session_id}/{file_id}/preview")
def preview_photo(session_id: str, file_id: str):
    if not HEX_ID_PATTERN.match(session_id) or not HEX_ID_PATTERN.match(file_id):
        raise HTTPException(status_code=400, detail="Invalid session or file identifier format.")

    session_dir = PhotoMatchingService.get_session_dir(session_id)
    photos_dir = session_dir / "photos"
    candidates = list(photos_dir.glob(f"{file_id}.*"))
    if not candidates or not candidates[0].exists():
        raise HTTPException(status_code=404, detail="Photograph file not found.")

    photo_path = candidates[0].resolve()
    if not str(photo_path).startswith(str(session_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied.")

    media_type = "image/jpeg"
    ext = photo_path.suffix.lower()
    if ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"

    return FileResponse(photo_path, media_type=media_type)


@router.post("/{session_id}/finalize", response_model=DatasetFinalizeResponse)
def finalize_dataset(session_id: str):
    """
    Marks the dataset as finalized and ready for presentation generation in Phase 2.
    Ensures all employees have an assigned photograph and no unresolved ambiguities remain.
    """
    if not HEX_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session identifier format.")

    session_res, _ = PhotoMatchingService.load_session_state(session_id)
    if not session_res:
        raise HTTPException(status_code=404, detail="Session not found.")

    if not session_res.is_dataset_ready:
        unresolved = [m.employee_name for m in session_res.employee_matches if not m.is_resolved or m.assigned_file is None]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot finalize dataset: {len(unresolved)} employee(s) lack a verified photograph ({', '.join(unresolved[:5])}).",
        )

    # Save finalized manifest for Phase 2 handoff
    from app.services.file_storage import atomic_write_json
    session_dir = PhotoMatchingService.get_session_dir(session_id)
    manifest_path = session_dir / "ready_manifest.json"
    manifest_data = {
        "session_id": session_id,
        "is_ready": True,
        "total_employees": len(session_res.employee_matches),
        "ready_employees": [m.dict() for m in session_res.employee_matches],
    }
    atomic_write_json(manifest_path, manifest_data)

    return DatasetFinalizeResponse(
        session_id=session_id,
        is_ready=True,
        total_employees=len(session_res.employee_matches),
        ready_employees=session_res.employee_matches,
        manifest_saved_path=str(manifest_path),
    )


@router.post("/{session_id}/generate-presentation")
def generate_presentation_from_photo_session(session_id: str):
    """
    Phase 2 Dynamic Presentation Generator:
    Takes a finalized photo session and dynamically builds a template-independent
    editable PPTX presentation with intelligent award grouping and optimal card layout.
    """
    if not HEX_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session identifier format.")

    session_res, _ = PhotoMatchingService.load_session_state(session_id)
    if not session_res:
        raise HTTPException(status_code=404, detail="Photo matching session not found.")

    if not session_res.is_dataset_ready:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate presentation: Dataset is not fully resolved. Every employee must have an assigned photograph.",
        )

    from app.services.dynamic_presentation_service import DynamicPresentationService
    try:
        gen_res = DynamicPresentationService.generate_presentation_from_dataset(
            session_id=session_id,
            employees=session_res.employee_matches,
        )
        return gen_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dynamic presentation generation failed: {str(e)}")

