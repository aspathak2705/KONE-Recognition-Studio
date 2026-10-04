import uuid
from io import BytesIO
from typing import List
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from app.schemas.template import (
    TextShapeInfo,
    ImageRegionInfo,
    EmployeeSlotInfo,
    RepeatingGroupInfo,
    SlideLayoutModel,
    SlideType,
    SlideInfo,
    TemplateInspectionResponse,
)

# 1 inch = 914400 EMUs
EMU_PER_INCH = 914400.0


def analyze_slide_layout(
    slide_number: int,
    total_slides: int,
    text_shapes: List[TextShapeInfo],
    image_shapes: List[ImageRegionInfo],
    groups_count: int,
) -> SlideLayoutModel:
    """Analyze text shapes and image frames to determine slide classification, employee slots, and capacity."""
    # Determine slide type heuristic
    if slide_number == 1 and (len(text_shapes) <= 3 or any("welcome" in s.text.lower() or "title" in s.shape_name.lower() or "kone" in s.text.lower() for s in text_shapes)):
        slide_type = SlideType.COVER
    elif slide_number == total_slides and total_slides > 1 and len(text_shapes) <= 2:
        slide_type = SlideType.CLOSING
    elif not text_shapes and not image_shapes:
        slide_type = SlideType.STATIC
    else:
        slide_type = SlideType.CONTENT

    # Dynamic slot detection: Group text shapes spatially or by group hierarchy
    # Look for repeating shape patterns (e.g. Employee_Name_1, Employee_Name_2, or shape clusters)
    # Check shape names for numeric indexes like "_1", "_2", " (1)", " 1"
    import re
    indexed_slots: Dict[int, List[TextShapeInfo]] = {}
    indexed_images: Dict[int, List[ImageRegionInfo]] = {}
    unindexed_text: List[TextShapeInfo] = []
    unindexed_images: List[ImageRegionInfo] = []

    index_pattern = re.compile(r'(?:_|\s|#)(\d+)$')

    for ts in text_shapes:
        m = index_pattern.search(ts.shape_name)
        if m:
            idx = int(m.group(1)) - 1  # Convert 1-based to 0-based
            indexed_slots.setdefault(idx, []).append(ts)
        else:
            unindexed_text.append(ts)

    for img in image_shapes:
        m = index_pattern.search(img.shape_name)
        if m:
            idx = int(m.group(1)) - 1
            indexed_images.setdefault(idx, []).append(img)
        else:
            unindexed_images.append(img)

    slots_info: List[EmployeeSlotInfo] = []
    all_slot_indices = sorted(set(indexed_slots.keys()).union(set(indexed_images.keys())))

    if all_slot_indices:
        # Multi-card layout detected via named shape indices
        slide_type = SlideType.REPEATING_CONTENT if len(all_slot_indices) > 1 else slide_type
        for slot_idx in all_slot_indices:
            t_list = indexed_slots.get(slot_idx, [])
            i_list = indexed_images.get(slot_idx, [])
            
            # Compute bounding box
            min_left = min([t.left_inches for t in t_list] + [i.left_inches for i in i_list] + [999.0])
            min_top = min([t.top_inches for t in t_list] + [i.top_inches for i in i_list] + [999.0])
            max_right = max([t.left_inches + t.width_inches for t in t_list] + [i.left_inches + i.width_inches for i in i_list] + [0.0])
            max_bottom = max([t.top_inches + t.height_inches for t in t_list] + [i.top_inches + i.height_inches for i in i_list] + [0.0])
            
            bbox = [min_left, min_top, round(max_right - min_left, 2), round(max_bottom - min_top, 2)] if min_left != 999.0 else None

            slots_info.append(
                EmployeeSlotInfo(
                    slot_index=slot_idx,
                    bounding_box=bbox,
                    text_shapes=t_list,
                    image_regions=i_list,
                )
            )
        capacity = len(slots_info)
    else:
        # Single card layout per slide
        capacity = 1 if text_shapes else 0
        slots_info.append(
            EmployeeSlotInfo(
                slot_index=0,
                text_shapes=unindexed_text,
                image_regions=unindexed_images,
            )
        )
        unindexed_text = []
        unindexed_images = []

    return SlideLayoutModel(
        slide_type=slide_type,
        capacity=capacity,
        employee_slots=slots_info,
        static_text_shapes=unindexed_text,
        static_images=unindexed_images,
    )


def inspect_powerpoint_template(file_content: bytes, filename: str) -> TemplateInspectionResponse:
    template_id = uuid.uuid4().hex
    warnings: List[str] = []

    try:
        prs = Presentation(BytesIO(file_content))
    except Exception as e:
        return TemplateInspectionResponse(
            valid=False,
            template_id=template_id,
            filename=filename,
            slide_count=0,
            slide_width_inches=0.0,
            slide_height_inches=0.0,
            aspect_ratio="unknown",
            slides=[],
            warnings=[f"Corrupted or invalid PowerPoint presentation: {str(e)}"],
        )

    width_in = round(prs.slide_width / EMU_PER_INCH, 2)
    height_in = round(prs.slide_height / EMU_PER_INCH, 2)
    
    # Calculate aspect ratio
    ratio_val = width_in / height_in if height_in > 0 else 0
    if abs(ratio_val - (16 / 9)) < 0.1:
        aspect_ratio = "16:9"
    elif abs(ratio_val - (4 / 3)) < 0.1:
        aspect_ratio = "4:3"
    else:
        aspect_ratio = f"{width_in}:{height_in}"

    slides_info: List[SlideInfo] = []
    total_placeholders = 0
    total_shapes = 0
    total_text_shapes = 0
    total_tables = 0
    total_groups = 0

    def process_shape_list(shapes, text_shapes_list, image_shapes_list, stats_dict):
        for shape in shapes:
            stats_dict["total_shapes"] += 1

            # Check if group shape
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                stats_dict["total_groups"] += 1
                try:
                    process_shape_list(shape.shapes, text_shapes_list, image_shapes_list, stats_dict)
                except Exception:
                    pass
                continue

            # Check if table
            if shape.has_table:
                stats_dict["total_tables"] += 1
                continue

            # Check if picture / image placeholder
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE or (hasattr(shape, "is_placeholder") and shape.is_placeholder and str(shape.placeholder_format.type) == "PICTURE (18)"):
                shape_name = shape.name or f"Picture_{shape.shape_id}"
                is_ph = getattr(shape, "is_placeholder", False)
                # Sample employee photo heuristic: shape name contains 'photo', 'avatar', 'picture', or is picture placeholder
                is_sample = any(kw in shape_name.lower() for kw in ["photo", "avatar", "picture", "employee", "profile"]) or is_ph
                
                image_shapes_list.append(
                    ImageRegionInfo(
                        shape_name=shape_name,
                        shape_id=str(shape.shape_id) if hasattr(shape, "shape_id") else None,
                        left_inches=round(shape.left / EMU_PER_INCH, 2),
                        top_inches=round(shape.top / EMU_PER_INCH, 2),
                        width_inches=round(shape.width / EMU_PER_INCH, 2),
                        height_inches=round(shape.height / EMU_PER_INCH, 2),
                        is_placeholder=is_ph,
                        is_sample_photo=is_sample,
                    )
                )

            is_text = shape.has_text_frame
            text_content = shape.text.strip() if is_text and shape.text else ""
            
            is_ph = shape.is_placeholder
            ph_type_str = None
            if is_ph:
                try:
                    ph_type_str = str(shape.placeholder_format.type)
                except Exception:
                    ph_type_str = "PLACEHOLDER"

            if is_text or is_ph:
                stats_dict["total_text_shapes"] += 1
                shape_name = shape.name or f"Shape_{shape.shape_id}"
                shape_type_str = str(shape.shape_type) if hasattr(shape, "shape_type") else "TEXT"

                text_shapes_list.append(
                    TextShapeInfo(
                        shape_name=shape_name,
                        shape_type=shape_type_str,
                        text=text_content,
                        left_inches=round(shape.left / EMU_PER_INCH, 2),
                        top_inches=round(shape.top / EMU_PER_INCH, 2),
                        width_inches=round(shape.width / EMU_PER_INCH, 2),
                        height_inches=round(shape.height / EMU_PER_INCH, 2),
                        unit="inches",
                        is_placeholder=is_ph,
                        placeholder_type=ph_type_str,
                    )
                )

    total_slides_count = len(prs.slides)
    for idx, slide in enumerate(prs.slides, start=1):
        text_shapes: List[TextShapeInfo] = []
        image_shapes: List[ImageRegionInfo] = []
        placeholder_count = len(slide.placeholders)
        total_placeholders += placeholder_count

        slide_stats = {
            "total_shapes": 0,
            "total_text_shapes": 0,
            "total_tables": 0,
            "total_groups": 0,
        }

        process_shape_list(slide.shapes, text_shapes, image_shapes, slide_stats)

        total_shapes += slide_stats["total_shapes"]
        total_text_shapes += slide_stats["total_text_shapes"]
        total_tables += slide_stats["total_tables"]
        total_groups += slide_stats["total_groups"]

        layout_model = analyze_slide_layout(
            slide_number=idx,
            total_slides=total_slides_count,
            text_shapes=text_shapes,
            image_shapes=image_shapes,
            groups_count=slide_stats["total_groups"],
        )

        slides_info.append(
            SlideInfo(
                slide_number=idx,
                shape_count=slide_stats["total_shapes"],
                text_shapes=text_shapes,
                image_shapes=image_shapes,
                placeholders_count=placeholder_count,
                tables_count=slide_stats["total_tables"],
                groups_count=slide_stats["total_groups"],
                layout_model=layout_model,
            )
        )

    if total_placeholders == 0:
        warnings.append(
            "No standard PowerPoint placeholders found. Template elements rely on text shapes or custom frames."
        )

    if total_groups > 0:
        warnings.append(
            f"Found {total_groups} grouped shape(s). Grouped shapes were recursively inspected for text frames."
        )

    warnings.append(
        "No dynamic field mapping established yet. Manual mapping is required before Phase 2 generation."
    )

    if len(slides_info) == 0:
        warnings.append("Presentation contains no slides.")

    return TemplateInspectionResponse(
        valid=True,
        template_id=template_id,
        filename=filename,
        slide_count=len(slides_info),
        slide_width_inches=width_in,
        slide_height_inches=height_in,
        unit="inches",
        aspect_ratio=aspect_ratio,
        total_shapes_count=total_shapes,
        total_text_shapes_count=total_text_shapes,
        total_placeholders_count=total_placeholders,
        total_tables_count=total_tables,
        total_groups_count=total_groups,
        slides=slides_info,
        warnings=warnings,
    )


