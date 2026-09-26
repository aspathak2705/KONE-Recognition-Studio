from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum


class ErrorDetail(BaseModel):
    code: str
    field: Optional[str] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class TextLengthWarningDetail(BaseModel):
    code: str = "TEXT_LENGTH_WARNING"
    field: str
    slide_number: int
    character_count: int
    threshold: int = 40
    message: str


class FieldMappingDetail(BaseModel):
    shape_name: str
    shape_id: Optional[str] = None
    placeholder_index: Optional[int] = None
    required: bool = True


class FieldMappingConfig(BaseModel):
    employee_name: Optional[FieldMappingDetail] = None
    designation: Optional[FieldMappingDetail] = None
    branch: Optional[FieldMappingDetail] = None
    award_name: Optional[FieldMappingDetail] = None
    template_slide_index: int = 0  # 0-based slide index for generation source layout


class InspectionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class MappingStatus(str, Enum):
    NOT_CONFIGURED = "not_configured"
    PARTIALLY_CONFIGURED = "partially_configured"
    VALID = "valid"
    INVALID = "invalid"


class GenerationReadiness(str, Enum):
    REQUIRES_TEMPLATE = "requires_template"
    REQUIRES_MAPPING = "requires_mapping"
    BLOCKED_BY_VALIDATION = "blocked_by_validation"
    READY_FOR_GENERATION = "ready_for_generation"


class MappingValidationResponse(BaseModel):
    valid: bool
    mapping_status: MappingStatus
    errors: List[str] = Field(default_factory=list)
    structured_errors: List[ErrorDetail] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class TemplateReadinessResponse(BaseModel):
    template_id: str
    filename: str
    inspection_status: InspectionStatus
    mapping_status: MappingStatus
    generation_readiness: GenerationReadiness
    configured_mapping: Optional[FieldMappingConfig] = None
    suggested_mapping: Optional[FieldMappingConfig] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    structured_errors: List[ErrorDetail] = Field(default_factory=list)


class GenerationRequest(BaseModel):
    excel_file_id: str
    template_file_id: str
    mapping_config: FieldMappingConfig


class GenerationResponse(BaseModel):
    generation_id: str
    source_template_file_id: str
    source_excel_file_id: str
    generated_file_id: str
    record_count: int
    slide_count: int
    status: str = "completed"
    warnings: List[str] = Field(default_factory=list)
    structured_warnings: List[TextLengthWarningDetail] = Field(default_factory=list)
    download_url: str
