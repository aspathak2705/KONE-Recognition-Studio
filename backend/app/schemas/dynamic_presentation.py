from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from app.schemas.photo_matching import EmployeePhotoMatch


class AwardGroup(BaseModel):
    award_name: str
    normalized_award_name: str
    employee_count: int
    employees: List[EmployeePhotoMatch] = Field(default_factory=list)


class DynamicLayoutConfig(BaseModel):
    columns: int
    rows: int
    max_cards_per_slide: int
    card_width_in: float
    card_height_in: float
    margin_left_in: float
    margin_top_in: float
    gap_x_in: float
    gap_y_in: float
    image_size_in: float
    name_font_size_pt: float
    meta_font_size_pt: float


class SlideGeometryFinding(BaseModel):
    slide_index: int
    severity: str  # PASS, WARNING, ERROR
    issue_type: str
    message: str


class DynamicGenerationResponse(BaseModel):
    generation_id: str
    session_id: str
    slide_count: int
    total_employees: int
    award_categories_count: int
    award_groups: List[AwardGroup] = Field(default_factory=list)
    download_url: str
    pptx_path: str
    is_valid: bool = True
    validation_findings: List[SlideGeometryFinding] = Field(default_factory=list)
    rendered_slide_urls: List[str] = Field(default_factory=list)
    delivery_status: str = "READY"
    can_download: bool = True
    created_at: str


class PresentationHistoryItem(BaseModel):
    generation_id: str
    presentation_name: str
    created_at: str
    record_count: int
    award_categories_count: int
    slide_count: int
    status: str
    delivery_status: str
    can_download: bool
    download_url: str
    rendered_slide_urls: List[str] = Field(default_factory=list)


class PresentationHistoryResponse(BaseModel):
    total_count: int
    items: List[PresentationHistoryItem] = Field(default_factory=list)
