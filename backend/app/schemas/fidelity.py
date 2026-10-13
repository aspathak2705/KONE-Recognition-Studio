from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


class RegionBBox(BaseModel):
    left_inches: float
    top_inches: float
    width_inches: float
    height_inches: float


class DynamicRegionManifest(BaseModel):
    region_id: str
    slot_index: int
    field_key: str  # e.g., 'employee_name', 'designation', 'branch', 'photo_placeholder'
    shape_name: str
    shape_id: Optional[str] = None
    bbox: RegionBBox
    is_multiline_card: bool = False
    card_line_index: Optional[int] = None  # 0: name, 1: designation, 2: location if in single multi-line card


class StaticRegionManifest(BaseModel):
    shape_name: str
    shape_id: Optional[str] = None
    shape_type: str
    bbox: RegionBBox
    has_text: bool = False
    text_content: Optional[str] = None
    is_image: bool = False
    is_background: bool = False
    z_order_index: int = 0


class SlideLayoutManifest(BaseModel):
    layout_variant_id: str
    source_slide_index: int
    slide_type: str  # COVER, CONTENT, REPEATING_CONTENT, CLOSING
    capacity: int
    static_regions: List[StaticRegionManifest] = Field(default_factory=list)
    dynamic_regions: List[DynamicRegionManifest] = Field(default_factory=list)
    photo_regions: List[DynamicRegionManifest] = Field(default_factory=list)


class TemplateFidelityManifest(BaseModel):
    manifest_id: str
    template_id: str
    template_version: int
    source_file_hash: str
    slide_width_inches: float
    slide_height_inches: float
    aspect_ratio: str
    total_source_slides: int
    layouts: List[SlideLayoutManifest] = Field(default_factory=list)
    created_at: str


class FailureSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QualityClassification(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    REPAIRABLE = "REPAIRABLE"
    CRITICAL = "CRITICAL"


class DeliveryStatus(str, Enum):
    READY = "READY"
    READY_WITH_WARNING = "READY_WITH_WARNING"
    REPAIR_PENDING = "REPAIR_PENDING"
    BLOCKED = "BLOCKED"


class ValidationFailureDetail(BaseModel):
    slide_number: int
    region: str
    failure_type: str
    severity: FailureSeverity
    expected: str
    actual: str
    message: str
    is_repairable: bool = False
    is_conclusive: bool = True


class SlideValidationResult(BaseModel):
    slide_number: int
    source_layout_variant_id: str
    passed: bool
    structural_score: float = 1.0
    geometry_score: float = 1.0
    static_asset_score: float = 1.0
    semantic_score: float = 1.0
    photo_slot_score: float = 1.0
    visual_score: float = 1.0
    failures: List[ValidationFailureDetail] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class DeliveryDecision(BaseModel):
    delivery_status: DeliveryStatus
    can_download: bool
    reason: str
    hr_message: str
    quality_classification: QualityClassification
    decision_timestamp: Optional[str] = None


class FidelityValidationReport(BaseModel):
    generation_id: str
    verification_status: VerificationStatus  # VERIFIED or BLOCKED (backwards compatible)
    quality_classification: QualityClassification = QualityClassification.PASS
    delivery_status: DeliveryStatus = DeliveryStatus.READY
    delivery_decision: Optional[DeliveryDecision] = None
    overall_score: float
    slides_checked: int
    slides_passed: int
    slides_failed: int
    structural_result: str = "PASS"
    geometry_result: str = "PASS"
    static_asset_result: str = "PASS"
    semantic_result: str = "PASS"
    photo_slot_result: str = "PASS"
    visual_result: str = "PASS"  # PASS, WARNING, UNAVAILABLE, or FAIL
    visual_verification_executed: bool = False
    failures: List[ValidationFailureDetail] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    slide_reports: List[SlideValidationResult] = Field(default_factory=list)

