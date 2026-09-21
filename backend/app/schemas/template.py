from pydantic import BaseModel, Field
from typing import List, Optional


class TextShapeInfo(BaseModel):
    shape_name: str
    shape_type: str
    text: str
    left_inches: float
    top_inches: float
    width_inches: float
    height_inches: float
    is_placeholder: bool = False
    placeholder_type: Optional[str] = None


class SlideInfo(BaseModel):
    slide_number: int
    shape_count: int
    text_shapes: List[TextShapeInfo] = Field(default_factory=list)
    placeholders_count: int = 0


class TemplateInspectionResponse(BaseModel):
    valid: bool
    template_id: str
    filename: str
    slide_count: int
    slide_width_inches: float
    slide_height_inches: float
    aspect_ratio: str
    slides: List[SlideInfo] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    saved_path: Optional[str] = None
