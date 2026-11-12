from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class PhotoMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"
    INVALID_IMAGE = "INVALID_IMAGE"
    UNMATCHED_FILE = "UNMATCHED_FILE"
    DUPLICATE_EMPLOYEE_NAME = "DUPLICATE_EMPLOYEE_NAME"


class PhotoFileMetadata(BaseModel):
    file_id: str
    original_filename: str
    normalized_stem: str
    extension: str
    file_size_bytes: int
    width: int
    height: int
    format: str
    relative_path: str
    preview_url: str
    is_valid: bool = True
    error_message: Optional[str] = None


class EmployeePhotoMatch(BaseModel):
    employee_record_index: int
    employee_name: str
    designation: Optional[str] = ""
    branch: Optional[str] = ""
    award_name: str
    normalized_name: str
    match_status: PhotoMatchStatus
    assigned_file: Optional[PhotoFileMetadata] = None
    candidate_files: List[PhotoFileMetadata] = Field(default_factory=list)
    issue_message: Optional[str] = None
    is_resolved: bool = False
    is_reused_override: bool = False


class PhotoMatchingSessionResponse(BaseModel):
    session_id: str
    total_employees: int
    matched_count: int
    missing_count: int
    ambiguous_count: int
    duplicate_name_count: int
    unmatched_files_count: int
    invalid_images_count: int
    is_dataset_ready: bool
    employee_matches: List[EmployeePhotoMatch] = Field(default_factory=list)
    unmatched_files: List[PhotoFileMetadata] = Field(default_factory=list)
    all_valid_photos: List[PhotoFileMetadata] = Field(default_factory=list)


class ResolveAssociationRequest(BaseModel):
    employee_record_index: int
    file_id: Optional[str] = None  # None indicates clearing association or acknowledging missing
    confirm_reuse: bool = False  # Explicit confirmation if file is already assigned to another employee


class DatasetFinalizeResponse(BaseModel):
    session_id: str
    is_ready: bool
    total_employees: int
    ready_employees: List[EmployeePhotoMatch] = Field(default_factory=list)
    manifest_saved_path: Optional[str] = None
