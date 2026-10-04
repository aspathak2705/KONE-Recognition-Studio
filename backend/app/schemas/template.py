from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class SlideType(str, Enum):
    COVER = "COVER"
    CONTENT = "CONTENT"
    REPEATING_CONTENT = "REPEATING_CONTENT"
    CLOSING = "CLOSING"
    STATIC = "STATIC"


class ImageRegionInfo(BaseModel):
    shape_name: str
    shape_id: Optional[str] = None
    left_inches: float
    top_inches: float
    width_inches: float
    height_inches: float
    is_placeholder: bool = False
    is_sample_photo: bool = False


class TextShapeInfo(BaseModel):
    shape_name: str
    shape_type: str
    text: str
    left_inches: float
    top_inches: float
    width_inches: float
    height_inches: float
    unit: str = "inches"
    is_placeholder: bool = False
    placeholder_type: Optional[str] = None


class EmployeeSlotInfo(BaseModel):
    slot_index: int  # 0-indexed position on the slide
    group_name: Optional[str] = None
    bounding_box: Optional[List[float]] = None  # [left, top, width, height]
    text_shapes: List[TextShapeInfo] = Field(default_factory=list)
    image_regions: List[ImageRegionInfo] = Field(default_factory=list)


class RepeatingGroupInfo(BaseModel):
    group_name: str
    capacity: int  # Number of employee slots in this group
    slots: List[EmployeeSlotInfo] = Field(default_factory=list)


class SlideLayoutModel(BaseModel):
    slide_type: SlideType = SlideType.CONTENT
    capacity: int = 1  # Employee record capacity of this slide layout
    employee_slots: List[EmployeeSlotInfo] = Field(default_factory=list)
    repeating_groups: List[RepeatingGroupInfo] = Field(default_factory=list)
    static_text_shapes: List[TextShapeInfo] = Field(default_factory=list)
    static_images: List[ImageRegionInfo] = Field(default_factory=list)


class SlideInfo(BaseModel):
    slide_number: int
    shape_count: int
    text_shapes: List[TextShapeInfo] = Field(default_factory=list)
    image_shapes: List[ImageRegionInfo] = Field(default_factory=list)
    placeholders_count: int = 0
    tables_count: int = 0
    groups_count: int = 0
    layout_model: Optional[SlideLayoutModel] = None


class TemplateInspectionResponse(BaseModel):
    valid: bool
    template_id: str
    filename: str
    slide_count: int
    slide_width_inches: float
    slide_height_inches: float
    unit: str = "inches"
    aspect_ratio: str
    total_shapes_count: int = 0
    total_text_shapes_count: int = 0
    total_placeholders_count: int = 0
    total_tables_count: int = 0
    total_groups_count: int = 0
    slides: List[SlideInfo] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    saved_path: Optional[str] = None

