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
    # In real KONE templates, each card is either a single multi-line text frame (like New Joiner or Q4 Text Placeholder 8)
    # or multiple text shapes (Name, Role, Location) grouped per card.
    # We group text shapes by proximity into cards.
    valid_texts = []
    static_texts: List[TextShapeInfo] = []
    for ts in text_shapes:
        txt = ts.text.strip().lower()
        if not txt:
            continue
        if any(kw in txt for kw in ["welcome to", "rewards & recognition", "congratulations", "quarterly", "q4 2025", "xoxo", "kei west", "http", "#onehr"]):
            static_texts.append(ts)
        else:
            valid_texts.append(ts)

    # If shapes have matching prefixes or are close in left_inches, cluster them
    # Group valid_texts by horizontal/vertical proximity
    clustered_cards: List[List[TextShapeInfo]] = []
    for ts in valid_texts:
        assigned = False
        for cluster in clustered_cards:
            ref = cluster[0]
            # If same vertical column or close in both left and top (within 1.5 inches)
            if abs(ref.left_inches - ts.left_inches) < 1.0 and abs(ref.top_inches - ts.top_inches) < 2.0:
                cluster.append(ts)
                assigned = True
                break
        if not assigned:
            clustered_cards.append([ts])

    # Classify slide type
    if slide_number == 1 and total_slides > 1 and len(clustered_cards) == 0:
        slide_type = SlideType.COVER
    elif slide_number == total_slides and total_slides > 1 and len(clustered_cards) == 0:
        slide_type = SlideType.CLOSING
    elif not text_shapes and not image_shapes:
        slide_type = SlideType.STATIC
    elif len(clustered_cards) > 1:
        slide_type = SlideType.REPEATING_CONTENT
    else:
        slide_type = SlideType.CONTENT


    sample_photos = [img for img in image_shapes if img.is_sample_photo]
    static_imgs = [img for img in image_shapes if not img.is_sample_photo]

    slots_info: List[EmployeeSlotInfo] = []


    if clustered_cards and slide_type not in (SlideType.COVER, SlideType.CLOSING, SlideType.STATIC):
        # Sort cards spatially (top to bottom, left to right) using primary shape
        sorted_card_clusters = sorted(clustered_cards, key=lambda cluster: (round(cluster[0].top_inches, 1), round(cluster[0].left_inches, 1)))
        used_photo_ids = set()

        for slot_idx, card_shapes in enumerate(sorted_card_clusters):
            primary_card = card_shapes[0]
            c_cx = primary_card.left_inches + primary_card.width_inches / 2.0
            c_cy = primary_card.top_inches + primary_card.height_inches / 2.0

            best_p = None
            best_dist = float("inf")
            for p in sample_photos:
                p_id = p.shape_id or p.shape_name
                if p_id in used_photo_ids:
                    continue
                p_cx = p.left_inches + p.width_inches / 2.0
                p_cy = p.top_inches + p.height_inches / 2.0
                dist = ((p_cx - c_cx) ** 2 + (p_cy - c_cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_p = p

            paired_imgs = []
            if best_p and best_dist < 4.0:  # within 4 inches
                used_photo_ids.add(best_p.shape_id or best_p.shape_name)
                paired_imgs.append(best_p)

            min_left = min([s.left_inches for s in card_shapes] + ([paired_imgs[0].left_inches] if paired_imgs else []))
            min_top = min([s.top_inches for s in card_shapes] + ([paired_imgs[0].top_inches] if paired_imgs else []))
            max_right = max([s.left_inches + s.width_inches for s in card_shapes] + ([paired_imgs[0].left_inches + paired_imgs[0].width_inches] if paired_imgs else []))
            max_bottom = max([s.top_inches + s.height_inches for s in card_shapes] + ([paired_imgs[0].top_inches + paired_imgs[0].height_inches] if paired_imgs else []))

            bbox = [round(min_left, 2), round(min_top, 2), round(max_right - min_left, 2), round(max_bottom - min_top, 2)]

            slots_info.append(
                EmployeeSlotInfo(
                    slot_index=slot_idx,
                    bounding_box=bbox,
                    text_shapes=card_shapes,
                    image_regions=paired_imgs,
                )
            )

        capacity = len(slots_info)
        if capacity > 1:
            slide_type = SlideType.REPEATING_CONTENT
    else:
        capacity = 1 if text_shapes else 0
        if text_shapes or image_shapes:
            slots_info.append(
                EmployeeSlotInfo(
                    slot_index=0,
                    text_shapes=text_shapes,
                    image_regions=image_shapes,
                )
            )

    return SlideLayoutModel(
        slide_type=slide_type,
        capacity=capacity,
        employee_slots=slots_info,
        static_text_shapes=static_texts,
        static_images=static_imgs,
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
                        shape_id=str(shape.shape_id) if hasattr(shape, "shape_id") else None,
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


