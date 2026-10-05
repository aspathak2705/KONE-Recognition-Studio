from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.mapping import (
    FieldMappingConfig,
    InspectionStatus,
    MappingStatus,
    GenerationReadiness,
    TemplateRequirements,
)
from app.schemas.template import TemplateInspectionResponse


class TemplateVersion(BaseModel):
    version_number: int
    file_hash: str
    filename: str
    pptx_rel_path: str
    inspection_status: InspectionStatus = InspectionStatus.SUCCESS
    mapping_status: MappingStatus = MappingStatus.NOT_CONFIGURED
    generation_readiness: GenerationReadiness = GenerationReadiness.REQUIRES_MAPPING
    requirements: Optional[TemplateRequirements] = None
    mapping_config: Optional[FieldMappingConfig] = None
    inspection_data: Optional[TemplateInspectionResponse] = None
    manifest_rel_path: Optional[str] = None
    created_at: str


class TemplateMetadata(BaseModel):
    template_id: str
    name: str
    current_version: int = 1
    file_hash: str
    inspection_status: InspectionStatus = InspectionStatus.SUCCESS
    mapping_status: MappingStatus = MappingStatus.NOT_CONFIGURED
    generation_readiness: GenerationReadiness = GenerationReadiness.REQUIRES_MAPPING
    aspect_ratio: str = "16:9"
    requirements: Optional[TemplateRequirements] = None
    supported_capacities: List[int] = Field(default_factory=list)
    has_photo_support: bool = False
    versions: List[TemplateVersion] = Field(default_factory=list)
    is_archived: bool = False
    created_at: str
    updated_at: str



class TemplateRegistrationRequest(BaseModel):
    name: str
    existing_template_id: Optional[str] = None


class TemplateRegistrationResponse(BaseModel):
    template: TemplateMetadata
    active_version: TemplateVersion
    is_new_version: bool
    is_duplicate_hash: bool
    message: str


class PresentationJobModel(BaseModel):
    job_id: str
    template_id: str
    template_version: int
    recognition_file_id: str
    generated_file_id: str
    status: str = "completed"
    created_at: str
