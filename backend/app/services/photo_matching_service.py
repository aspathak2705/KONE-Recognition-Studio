import io
import re
import os
import uuid
import zipfile
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from PIL import Image, ImageOps

from app.core.config import settings
from app.services.file_storage import atomic_write_json
from app.schemas.recognition import RecognitionRecord
from app.schemas.photo_matching import (
    PhotoMatchStatus,
    PhotoFileMetadata,
    EmployeePhotoMatch,
    PhotoMatchingSessionResponse,
)

SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB max per image


def normalize_string_for_matching(text: str) -> str:
    """
    Normalizes string by removing accents, extra spaces, special punctuation, and lowercasing.
    Handles 'Rahul  Sharma' -> 'rahul sharma', 'Matti Nykänen' -> 'matti nykanen'.
    """
    if not text:
        return ""
    # Normalize unicode to NFKD to strip accents/diacritics
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Replace separators/underscores with space and remove non-alphanumeric except spaces
    cleaned = re.sub(r"[_\-\.]+", " ", stripped)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    # Collapse consecutive whitespace and lowercase
    return " ".join(cleaned.lower().split())


def inspect_and_validate_image_bytes(
    content: bytes, original_filename: str
) -> Tuple[bool, Optional[str], int, int, str]:
    """
    Validates actual image decodability using PIL (not trusting file extension alone).
    Returns (is_valid, error_msg, width, height, format_name).
    """
    if not content:
        return False, "Image file is empty (0 bytes).", 0, 0, ""

    if len(content) > MAX_IMAGE_SIZE_BYTES:
        return False, f"Image file exceeds maximum size of 25MB.", 0, 0, ""

    try:
        with Image.open(io.BytesIO(content)) as img:
            img_format = (img.format or "").upper()
            width, height = img.size

            if img_format not in SUPPORTED_IMAGE_FORMATS:
                return False, f"Unsupported image format: {img_format}. Supported: JPG, JPEG, PNG, WEBP.", 0, 0, img_format

            if width <= 0 or height <= 0:
                return False, "Invalid image dimensions.", width, height, img_format

            # Verify image data integrity by loading raw pixel buffer
            img.verify()

        # Reopen to ensure full decodability (verify() leaves stream in unusable state)
        with Image.open(io.BytesIO(content)) as img:
            img.load()

        return True, None, width, height, img_format
    except Exception as e:
        return False, f"Corrupted or invalid image: {str(e)}", 0, 0, ""


class PhotoMatchingService:
    @classmethod
    def get_session_dir(cls, session_id: str) -> Path:
        session_dir = settings.PHOTO_SESSIONS_DIR.resolve() / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    @classmethod
    def save_photo_file(
        cls, session_id: str, original_filename: str, content: bytes
    ) -> PhotoFileMetadata:
        """
        Saves uploaded photo into the session directory with safe UUID filename.
        """
        clean_name = Path(original_filename).name  # Prevent path traversal
        ext = Path(clean_name).suffix.lower()
        stem = Path(clean_name).stem
        normalized_stem = normalize_string_for_matching(stem)

        file_id = uuid.uuid4().hex
        safe_disk_filename = f"{file_id}{ext}"
        session_dir = cls.get_session_dir(session_id)
        photos_dir = session_dir / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        dest_path = photos_dir / safe_disk_filename

        is_valid, err_msg, width, height, fmt = inspect_and_validate_image_bytes(content, clean_name)

        if is_valid:
            try:
                # Transpose EXIF orientation tags so photos never save rotated
                with Image.open(io.BytesIO(content)) as raw_img:
                    transposed_img = ImageOps.exif_transpose(raw_img)
                    width, height = transposed_img.size

                    # WEBP handling: PowerPoint desktop versions prior to Office 365
                    # or certain native drivers do not support embedded WEBP directly.
                    # Convert WEBP to PNG to guarantee 100% PowerPoint compatibility.
                    if fmt == "WEBP" or ext == ".webp":
                        ext = ".png"
                        safe_disk_filename = f"{file_id}.png"
                        dest_path = photos_dir / safe_disk_filename
                        transposed_img.save(dest_path, format="PNG")
                        fmt = "PNG"
                    elif fmt in ("JPEG", "JPG") or ext in (".jpg", ".jpeg"):
                        # Convert to RGB to safely drop any CMYK or invalid color spaces
                        if transposed_img.mode != "RGB":
                            transposed_img = transposed_img.convert("RGB")
                        transposed_img.save(dest_path, format="JPEG", quality=95)
                    elif fmt == "PNG" or ext == ".png":
                        transposed_img.save(dest_path, format="PNG")
                    else:
                        with open(dest_path, "wb") as f:
                            f.write(content)
            except Exception as e:
                # Fallback to direct write if transposition fails
                with open(dest_path, "wb") as f:
                    f.write(content)

        return PhotoFileMetadata(
            file_id=file_id,
            original_filename=clean_name,
            normalized_stem=normalized_stem,
            extension=ext,
            file_size_bytes=dest_path.stat().st_size if is_valid and dest_path.exists() else len(content),
            width=width,
            height=height,
            format=fmt,
            relative_path=f"photos/{safe_disk_filename}" if is_valid else "",
            preview_url=f"/api/photos/{session_id}/{file_id}/preview" if is_valid else "",
            is_valid=is_valid,
            error_message=err_msg,
        )

    @classmethod
    def extract_photos_from_zip(cls, session_id: str, zip_bytes: bytes) -> List[PhotoFileMetadata]:
        """
        Extracts photos from a ZIP archive uploaded by HR as folder fallback.
        """
        photos: List[PhotoFileMetadata] = []
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                for entry in zf.infolist():
                    if entry.is_dir():
                        continue
                    clean_name = Path(entry.filename).name
                    if clean_name.startswith((".", "__MACOSX")):
                        continue  # Skip hidden/OS metadata files
                    ext = Path(clean_name).suffix.lower()
                    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                        continue
                    content = zf.read(entry)
                    photo_meta = cls.save_photo_file(session_id, clean_name, content)
                    photos.append(photo_meta)
        except Exception as e:
            raise ValueError(f"Failed to process photo ZIP archive: {str(e)}")
        return photos

    @classmethod
    def match_photos_to_employees(
        cls,
        session_id: str,
        records: List[RecognitionRecord],
        uploaded_photos: List[PhotoFileMetadata],
    ) -> PhotoMatchingSessionResponse:
        """
        Core photograph matching engine.
        Implements all 11 matching rules and duplicate employee name protection.
        """
        valid_photos = [p for p in uploaded_photos if p.is_valid]
        invalid_photos = [p for p in uploaded_photos if not p.is_valid]

        # Index valid photos by normalized stem
        photos_by_norm: Dict[str, List[PhotoFileMetadata]] = {}
        for p in valid_photos:
            photos_by_norm.setdefault(p.normalized_stem, []).append(p)

        # Detect multiple employee records sharing the same normalized name
        norm_name_counts: Dict[str, int] = {}
        for rec in records:
            n_name = normalize_string_for_matching(rec.employee_name)
            norm_name_counts[n_name] = norm_name_counts.get(n_name, 0) + 1

        employee_matches: List[EmployeePhotoMatch] = []
        assigned_file_ids: Set[str] = set()

        for idx, rec in enumerate(records):
            norm_name = normalize_string_for_matching(rec.employee_name)
            candidates = photos_by_norm.get(norm_name, [])

            # Rule 8: If multiple employees share the exact same name, mark DUPLICATE_EMPLOYEE_NAME
            if norm_name_counts.get(norm_name, 0) > 1:
                match = EmployeePhotoMatch(
                    employee_record_index=idx,
                    employee_name=rec.employee_name,
                    designation=rec.designation or "",
                    branch=rec.branch or "",
                    award_name=rec.award_name,
                    normalized_name=norm_name,
                    match_status=PhotoMatchStatus.DUPLICATE_EMPLOYEE_NAME,
                    assigned_file=None,
                    candidate_files=candidates,
                    issue_message=f"Multiple employees share the name '{rec.employee_name}'. Filename matching is ambiguous; manual confirmation required.",
                    is_resolved=False,
                )
            elif len(candidates) == 1:
                # Rule 3, 4, 5: Exact 1-to-1 normalized match
                candidate = candidates[0]
                match = EmployeePhotoMatch(
                    employee_record_index=idx,
                    employee_name=rec.employee_name,
                    designation=rec.designation or "",
                    branch=rec.branch or "",
                    award_name=rec.award_name,
                    normalized_name=norm_name,
                    match_status=PhotoMatchStatus.MATCHED,
                    assigned_file=candidate,
                    candidate_files=candidates,
                    issue_message=None,
                    is_resolved=True,
                )
                assigned_file_ids.add(candidate.file_id)
            elif len(candidates) > 1:
                # Rule 7: Multiple files matching one employee
                match = EmployeePhotoMatch(
                    employee_record_index=idx,
                    employee_name=rec.employee_name,
                    designation=rec.designation or "",
                    branch=rec.branch or "",
                    award_name=rec.award_name,
                    normalized_name=norm_name,
                    match_status=PhotoMatchStatus.AMBIGUOUS,
                    assigned_file=None,
                    candidate_files=candidates,
                    issue_message=f"{len(candidates)} photo files match this employee name ({', '.join([c.original_filename for c in candidates])}). Please select the intended photo.",
                    is_resolved=False,
                )
            else:
                # Rule 9: Missing photograph
                match = EmployeePhotoMatch(
                    employee_record_index=idx,
                    employee_name=rec.employee_name,
                    designation=rec.designation or "",
                    branch=rec.branch or "",
                    award_name=rec.award_name,
                    normalized_name=norm_name,
                    match_status=PhotoMatchStatus.MISSING,
                    assigned_file=None,
                    candidate_files=[],
                    issue_message=f"No matching photograph found for '{rec.employee_name}'.",
                    is_resolved=False,
                )
            employee_matches.append(match)

        # Rule 10: Detect files that do not correspond to any employee
        unmatched_files = [p for p in valid_photos if p.file_id not in assigned_file_ids]

        matched_count = sum(1 for m in employee_matches if m.match_status == PhotoMatchStatus.MATCHED)
        missing_count = sum(1 for m in employee_matches if m.match_status == PhotoMatchStatus.MISSING)
        ambiguous_count = sum(1 for m in employee_matches if m.match_status == PhotoMatchStatus.AMBIGUOUS)
        dup_name_count = sum(1 for m in employee_matches if m.match_status == PhotoMatchStatus.DUPLICATE_EMPLOYEE_NAME)

        is_dataset_ready = (
            len(employee_matches) > 0
            and all(m.is_resolved for m in employee_matches)
            and all(m.assigned_file is not None for m in employee_matches)
        )

        response = PhotoMatchingSessionResponse(
            session_id=session_id,
            total_employees=len(records),
            matched_count=matched_count,
            missing_count=missing_count,
            ambiguous_count=ambiguous_count,
            duplicate_name_count=dup_name_count,
            unmatched_files_count=len(unmatched_files),
            invalid_images_count=len(invalid_photos),
            is_dataset_ready=is_dataset_ready,
            employee_matches=employee_matches,
            unmatched_files=unmatched_files,
            all_valid_photos=valid_photos,
        )

        # Persist session state atomically
        cls.save_session_state(session_id, response, uploaded_photos)
        return response

    @classmethod
    def save_session_state(
        cls,
        session_id: str,
        session_response: PhotoMatchingSessionResponse,
        all_photos: List[PhotoFileMetadata],
    ) -> None:
        session_dir = cls.get_session_dir(session_id)
        state_file = session_dir / "session.json"
        data = {
            "session_response": session_response.dict(),
            "all_photos": [p.dict() for p in all_photos],
        }
        atomic_write_json(state_file, data)

    @classmethod
    def load_session_state(
        cls, session_id: str
    ) -> Tuple[Optional[PhotoMatchingSessionResponse], List[PhotoFileMetadata]]:
        session_dir = cls.get_session_dir(session_id)
        state_file = session_dir / "session.json"
        if not state_file.exists():
            return None, []
        import json
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        session_res = PhotoMatchingSessionResponse(**data["session_response"])
        all_photos = [PhotoFileMetadata(**p) for p in data["all_photos"]]
        return session_res, all_photos

    @classmethod
    def resolve_association(
        cls,
        session_id: str,
        employee_record_index: int,
        file_id: Optional[str],
        confirm_reuse: bool = False,
    ) -> PhotoMatchingSessionResponse:
        session_res, all_photos = cls.load_session_state(session_id)
        if not session_res:
            raise ValueError(f"Session '{session_id}' not found.")

        if employee_record_index < 0 or employee_record_index >= len(session_res.employee_matches):
            raise ValueError(f"Invalid employee index: {employee_record_index}")

        photo_map = {p.file_id: p for p in all_photos if p.is_valid}
        target_match = session_res.employee_matches[employee_record_index]

        if file_id is None:
            # HR explicitly cleared or set as missing
            target_match.assigned_file = None
            target_match.match_status = PhotoMatchStatus.MISSING
            target_match.issue_message = "Photograph removed by HR."
            target_match.is_resolved = False
            target_match.is_reused_override = False
        else:
            if file_id not in photo_map:
                raise ValueError(f"Photograph ID '{file_id}' not found or invalid.")

            selected_photo = photo_map[file_id]

            # Check if this photo is already assigned to a DIFFERENT employee
            already_assigned_other = [
                m for m in session_res.employee_matches
                if m.employee_record_index != employee_record_index and m.assigned_file and m.assigned_file.file_id == file_id
            ]

            if already_assigned_other and not confirm_reuse:
                other_names = ", ".join([o.employee_name for o in already_assigned_other])
                raise ValueError(
                    f"CONFIRMATION_REQUIRED: Photo '{selected_photo.original_filename}' is already assigned to {other_names}. "
                    f"Please confirm explicit reuse if intended."
                )

            target_match.assigned_file = selected_photo
            target_match.match_status = PhotoMatchStatus.MATCHED
            target_match.issue_message = None
            target_match.is_resolved = True
            target_match.is_reused_override = bool(already_assigned_other)

        # Recalculate assigned files and unmatched files
        assigned_file_ids = {
            m.assigned_file.file_id for m in session_res.employee_matches if m.assigned_file is not None
        }
        valid_photos = [p for p in all_photos if p.is_valid]
        session_res.unmatched_files = [p for p in valid_photos if p.file_id not in assigned_file_ids]
        session_res.unmatched_files_count = len(session_res.unmatched_files)

        # Recalculate summary counts
        session_res.matched_count = sum(1 for m in session_res.employee_matches if m.match_status == PhotoMatchStatus.MATCHED)
        session_res.missing_count = sum(1 for m in session_res.employee_matches if m.match_status == PhotoMatchStatus.MISSING)
        session_res.ambiguous_count = sum(1 for m in session_res.employee_matches if m.match_status == PhotoMatchStatus.AMBIGUOUS)
        session_res.duplicate_name_count = sum(1 for m in session_res.employee_matches if m.match_status == PhotoMatchStatus.DUPLICATE_EMPLOYEE_NAME)

        session_res.is_dataset_ready = (
            len(session_res.employee_matches) > 0
            and all(m.is_resolved for m in session_res.employee_matches)
            and all(m.assigned_file is not None for m in session_res.employee_matches)
        )

        cls.save_session_state(session_id, session_res, all_photos)
        return session_res
