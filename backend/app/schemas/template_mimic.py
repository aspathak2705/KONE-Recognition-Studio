from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ElementType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    SHAPE = "SHAPE"
    TABLE = "TABLE"
    GROUP = "GROUP"
    UNKNOWN = "UNKNOWN"


class RoleCandidate(str, Enum):
    STATIC = "STATIC"                      # Kept as-is (backgrounds, logos, decorative borders)
    CONTAINER = "CONTAINER"                # Card / background bounding box enclosing other elements
    REPLACEABLE_TEXT = "REPLACEABLE_TEXT"  # Text box candidate for replacement
    REPLACEABLE_IMAGE = "REPLACEABLE_IMAGE"# Image frame / placeholder for photo
    UNCONFIGURED = "UNCONFIGURED"          # Ambiguous element needing confirmation


class ElementCapability(str, Enum):
    TEXT_EDIT = "TEXT_EDIT"
    IMAGE_REPLACE = "IMAGE_REPLACE"
    STYLE_SOURCE = "STYLE_SOURCE"
    IMMUTABLE = "IMMUTABLE"


class TextStyleInfo(BaseModel):
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    color_rgb: Optional[str] = None  # e.g. "002F6C"
    color_theme: Optional[str] = None
    alignment: Optional[str] = None  # LEFT, CENTER, RIGHT, JUSTIFY
    line_spacing: Optional[float] = None


class VisualElementConfig(BaseModel):
    element_id: str  # Stable UUID or shape key
    original_shape_id: Optional[int] = None
    shape_name: str
    element_type: ElementType
    left_in: float
    top_in: float
    width_in: float
    height_in: float
    z_order: int = 0
    
    # Visual Styling
    fill_color_rgb: Optional[str] = None
    line_color_rgb: Optional[str] = None
    line_width_pt: Optional[float] = None
    opacity: Optional[float] = 1.0
    text_sample: Optional[str] = None
    text_style: Optional[TextStyleInfo] = None
    
    # Mimic Role Decision
    role: RoleCandidate = RoleCandidate.UNCONFIGURED
    capabilities: List[ElementCapability] = Field(default_factory=list)
    confidence_score: float = 0.5  # Heuristic confidence in candidate role
    user_confirmed: bool = False
    notes: Optional[str] = None
    target_field: Optional[str] = None  # Generic content field key to populate (e.g., 'primary_text', 'secondary_text', 'photo')


class ContentCluster(BaseModel):
    """
    Spike / cluster of related elements (e.g., photo frame + title + subtitle)
    detected via spatial proximity, without assuming domain semantics.
    """
    cluster_id: str
    bounding_box_in: List[float]  # [left, top, width, height]
    element_ids: List[str] = Field(default_factory=list)
    suggested_role: str = "RECORD_CARD"
    is_repeating_unit: bool = False
    field_mappings: Dict[str, str] = Field(default_factory=dict)  # element_id -> generic field key


class SlideLayoutConfig(BaseModel):
    slide_index: int
    slide_width_in: float
    slide_height_in: float
    background_color_rgb: Optional[str] = None
    background_image_path: Optional[str] = None
    is_suitable_for_content: bool = True
    elements: List[VisualElementConfig] = Field(default_factory=list)
    content_clusters: List[ContentCluster] = Field(default_factory=list)
    layout_signature: str = ""  # Hash of normalized layout topology
    layout_role: Optional[str] = None  # "COVER", "CONTENT", "CLOSING", or None (auto-classified)


class TemplateThemePalette(BaseModel):
    primary_color_rgb: Optional[str] = None
    secondary_color_rgb: Optional[str] = None
    accent_color_rgb: Optional[str] = None
    background_color_rgb: Optional[str] = None
    card_bg_color_rgb: Optional[str] = None
    primary_font: Optional[str] = None
    secondary_font: Optional[str] = None
    detected_colors: List[str] = Field(default_factory=list)
    detected_fonts: List[str] = Field(default_factory=list)


class TemplateMimicConfig(BaseModel):
    template_id: str
    filename: str
    name: str
    version: int = 1
    created_at: str
    updated_at: str
    slide_count: int
    slide_width_in: float
    slide_height_in: float
    aspect_ratio: str  # "16:9", "4:3", etc.
    theme: TemplateThemePalette
    slides: List[SlideLayoutConfig] = Field(default_factory=list)
    is_valid: bool = True
    validation_warnings: List[str] = Field(default_factory=list)
    raw_storage_path: str
    preview_slide_urls: List[str] = Field(default_factory=list)


class TemplateUploadResponse(BaseModel):
    success: bool
    template_id: str
    message: str
    config: Optional[TemplateMimicConfig] = None
    warnings: List[str] = Field(default_factory=list)


class UpdateElementRoleRequest(BaseModel):
    slide_index: int
    element_id: str
    role: RoleCandidate
    user_confirmed: bool = True
    notes: Optional[str] = None
    target_field: Optional[str] = None


class ConfigureLayoutRequest(BaseModel):
    slide_index: int
    layout_role: Optional[str] = None  # "COVER", "CONTENT", "CLOSING"
    field_mappings: Optional[Dict[str, str]] = None  # element_id -> generic field key
