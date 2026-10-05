import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.schemas.recognition import RecognitionRecord, ExcelValidationResponse
from app.schemas.template import TemplateInspectionResponse
from app.schemas.mapping import FieldMappingConfig, GenerationResponse, TextLengthWarningDetail
from app.services.template_inspector import inspect_powerpoint_template
from app.core.config import settings


import copy
from PIL import Image

def copy_slide_elements(source_slide, target_slide):
    """Deep clone native shapes from source slide to target slide, preserving relationships, pictures, vector paths, formatting."""
    # Remove any default shapes in target_slide
    for shp in list(target_slide.shapes):
        sp = shp._element
        sp.getparent().remove(sp)

    for shp in source_slide.shapes:
        elem = copy.deepcopy(shp._element)
        if shp.shape_type == MSO_SHAPE_TYPE.PICTURE:
            blips = elem.xpath('.//a:blip')
            if blips:
                old_rid = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if old_rid and old_rid in source_slide.part.rels:
                    rel = source_slide.part.rels[old_rid]
                    new_rid = target_slide.part.relate_to(rel.target_part, rel.reltype)
                    blips[0].set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', new_rid)
        target_slide.shapes._spTree.append(elem)


def substitute_text_in_shape(shape, new_text: str, card_data: Optional[Dict[str, str]] = None) -> bool:
    if not shape.has_text_frame:
        return False

    tf = shape.text_frame
    if not tf.paragraphs:
        p = tf.add_paragraph()
        p.text = new_text
        return True

    # Check if shape is a multi-line card containing separate paragraphs for name, designation, branch
    if card_data and len(tf.paragraphs) >= 2:
        field_order = ["employee_name", "designation", "branch", "award_name"]
        for p_idx, p in enumerate(tf.paragraphs):
            if p_idx < len(field_order):
                f_key = field_order[p_idx]
                line_val = card_data.get(f_key, "")
                if p.runs:
                    font_name = p.runs[0].font.name
                    font_size = p.runs[0].font.size
                    font_bold = p.runs[0].font.bold
                    font_italic = p.runs[0].font.italic
                    font_color = p.runs[0].font.color.rgb if (p.runs[0].font.color and hasattr(p.runs[0].font.color, "rgb")) else None
                    alignment = p.alignment

                    p.text = line_val
                    if p.runs:
                        r = p.runs[0]
                        if font_name: r.font.name = font_name
                        if font_size: r.font.size = font_size
                        if font_bold is not None: r.font.bold = font_bold
                        if font_italic is not None: r.font.italic = font_italic
                        if font_color: r.font.color.rgb = font_color
                        p.alignment = alignment
                else:
                    p.text = line_val
        return True

    # Standard single-field substitution: Preserve formatting of first run
    first_p = tf.paragraphs[0]
    if first_p.runs:
        font_name = first_p.runs[0].font.name
        font_size = first_p.runs[0].font.size
        font_bold = first_p.runs[0].font.bold
        font_italic = first_p.runs[0].font.italic
        font_color = (
            first_p.runs[0].font.color.rgb
            if (first_p.runs[0].font.color and hasattr(first_p.runs[0].font.color, "rgb"))
            else None
        )
        alignment = first_p.alignment

        first_p.text = new_text

        # Re-apply font styling to the updated paragraph run
        if first_p.runs:
            r = first_p.runs[0]
            if font_name:
                r.font.name = font_name
            if font_size:
                r.font.size = font_size
            if font_bold is not None:
                r.font.bold = font_bold
            if font_italic is not None:
                r.font.italic = font_italic
            if font_color:
                r.font.color.rgb = font_color
            first_p.alignment = alignment
    else:
        first_p.text = new_text

    return True


def find_shape_by_name(shapes, shape_name: str):
    for shape in shapes:
        if shape.name == shape_name:
            return shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            nested = find_shape_by_name(shape.shapes, shape_name)
            if nested:
                return nested
    return None


def clear_sample_photo(shape, slide):
    """Clear sample photo content while strictly preserving the photo slot geometry and frame."""
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        blips = shape._element.xpath('.//a:blip')
        if blips:
            rId = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rId and rId in slide.part.rels:
                try:
                    part = slide.part.related_part(rId)
                    # Replace with neutral 1x1 blank image bytes
                    blank = Image.new('RGB', (100, 100), (248, 248, 248))
                    bio = BytesIO()
                    blank.save(bio, format='PNG')
                    part._blob = bio.getvalue()
                except Exception:
                    pass


def clear_shape_content(shape, slide=None):
    """Clear text or photo placeholder content while retaining frames and geometry."""
    if shape.has_text_frame:
        shape.text_frame.text = ""
    elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        if slide:
            clear_sample_photo(shape, slide)
        else:
            try:
                sp = shape._element
                sp.getparent().remove(sp)
            except Exception:
                pass


def generate_powerpoint_presentation(
    template_content: bytes,
    template_filename: str,
    excel_records: List[RecognitionRecord],
    mapping_config: FieldMappingConfig,
    source_excel_file_id: str,
    source_template_file_id: str,
) -> GenerationResponse:
    warnings: List[str] = []
    structured_warnings: List[TextLengthWarningDetail] = []
    
    if not excel_records:
        raise ValueError("Cannot generate presentation from an empty recognition dataset.")

    valid_records = [r for r in excel_records if r.is_valid]
    if not valid_records:
        raise ValueError("No valid recognition records found in the uploaded Excel file.")

    prs = Presentation(BytesIO(template_content))
    if not prs.slides:
        raise ValueError("Source template presentation contains no slides.")

    slide_idx = mapping_config.template_slide_index if mapping_config else 0
    if slide_idx < 0 or slide_idx >= len(prs.slides):
        raise ValueError(f"Configured template_slide_index {slide_idx} is out of bounds (slide count: {len(prs.slides)}).")

    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
    template_slide_source = prs.slides[slide_idx]

    # Multi-card slot mode vs Single-card legacy mode
    slots_config = mapping_config.slots if (mapping_config and mapping_config.slots) else []
    cards_per_slide = len(slots_config) if slots_config else 1

    if cards_per_slide > 1:
        # Multi-card capacity mode (e.g. 2, 4, 7, 8 cards/slide)
        num_records = len(valid_records)
        num_slides_needed = (num_records + cards_per_slide - 1) // cards_per_slide

        for s_idx in range(num_slides_needed):
            if s_idx == 0 and slide_idx == 0:
                current_slide = template_slide_source
            else:
                current_slide = prs.slides.add_slide(blank_layout)
                copy_slide_elements(template_slide_source, current_slide)

            rec_start = s_idx * cards_per_slide
            for card_slot_idx in range(cards_per_slide):
                rec_idx = rec_start + card_slot_idx
                slot_mapping = slots_config[card_slot_idx] if card_slot_idx < len(slots_config) else None

                if rec_idx < num_records:
                    rec = valid_records[rec_idx]
                    record_dict = {
                        "employee_name": rec.employee_name,
                        "designation": rec.designation,
                        "branch": rec.branch,
                        "award_name": rec.award_name,
                    }

                    if slot_mapping:
                        field_map = {
                            "employee_name": slot_mapping.employee_name.shape_name if slot_mapping.employee_name else None,
                            "designation": slot_mapping.designation.shape_name if slot_mapping.designation else None,
                            "branch": slot_mapping.branch.shape_name if slot_mapping.branch else None,
                            "award_name": slot_mapping.award_name.shape_name if slot_mapping.award_name else None,
                        }
                        for field_name, s_name in field_map.items():
                            if s_name:
                                shape = find_shape_by_name(current_slide.shapes, s_name)
                                val = record_dict.get(field_name, "")
                                if len(val) > 40:
                                    warn_msg = f"TEXT_LENGTH_WARNING: Slide #{s_idx+1} slot #{card_slot_idx+1} field '{field_name}' length ({len(val)} chars) exceeds threshold (40 chars); verify layout fit."
                                    warnings.append(warn_msg)
                                    structured_warnings.append(
                                        TextLengthWarningDetail(
                                            field=field_name,
                                            slide_number=s_idx + 1,
                                            character_count=len(val),
                                            threshold=40,
                                            message=warn_msg,
                                        )
                                    )
                                if shape:
                                    substitute_text_in_shape(shape, val)

                        # Clear sample photo if specified
                        if slot_mapping.photo_placeholder and slot_mapping.photo_placeholder.shape_name:
                            p_shape = find_shape_by_name(current_slide.shapes, slot_mapping.photo_placeholder.shape_name)
                            if p_shape:
                                clear_shape_content(p_shape)
                else:
                    # Unfilled card slot on last slide: clear text shapes and sample photo placeholders
                    if slot_mapping:
                        field_map = {
                            "employee_name": slot_mapping.employee_name.shape_name if slot_mapping.employee_name else None,
                            "designation": slot_mapping.designation.shape_name if slot_mapping.designation else None,
                            "branch": slot_mapping.branch.shape_name if slot_mapping.branch else None,
                            "award_name": slot_mapping.award_name.shape_name if slot_mapping.award_name else None,
                            "photo_placeholder": slot_mapping.photo_placeholder.shape_name if slot_mapping.photo_placeholder else None,
                        }
                        for s_name in field_map.values():
                            if s_name:
                                shape = find_shape_by_name(current_slide.shapes, s_name)
                                if shape:
                                    clear_shape_content(shape)
    else:
        # Legacy single-card mode (1 record per slide)
        field_map = {
            "employee_name": mapping_config.employee_name.shape_name if mapping_config.employee_name else None,
            "designation": mapping_config.designation.shape_name if mapping_config.designation else None,
            "branch": mapping_config.branch.shape_name if mapping_config.branch else None,
            "award_name": mapping_config.award_name.shape_name if mapping_config.award_name else None,
        }

        for idx, rec in enumerate(valid_records):
            if idx == 0 and slide_idx == 0:
                target_slide = template_slide_source
            else:
                target_slide = prs.slides.add_slide(blank_layout)
                copy_slide_elements(template_slide_source, target_slide)

            record_dict = {
                "employee_name": rec.employee_name,
                "designation": rec.designation,
                "branch": rec.branch,
                "award_name": rec.award_name,
            }

            for field_name, s_name in field_map.items():
                if s_name:
                    shape = find_shape_by_name(target_slide.shapes, s_name)
                    val = record_dict.get(field_name, "")
                    
                    if len(val) > 40:
                        warn_msg = f"TEXT_LENGTH_WARNING: Slide #{idx+1} field '{field_name}' length ({len(val)} chars) exceeds threshold (40 chars); verify layout fit."
                        warnings.append(warn_msg)
                        structured_warnings.append(
                            TextLengthWarningDetail(
                                field=field_name,
                                slide_number=idx + 1,
                                character_count=len(val),
                                threshold=40,
                                message=warn_msg,
                            )
                        )

                    if shape:
                        substitute_text_in_shape(shape, val)

    generation_id = uuid.uuid4().hex
    generated_filename = f"{generation_id}.pptx"
    
    settings.GENERATED_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = settings.GENERATED_OUTPUTS_DIR / generated_filename

    output_bio = BytesIO()
    prs.save(output_bio)
    file_bytes = output_bio.getvalue()

    with open(destination, "wb") as f:
        f.write(file_bytes)

    # Re-verify generated output presentation readability
    verification = inspect_powerpoint_template(file_bytes, generated_filename)
    if not verification.valid:
        raise ValueError("Generated PowerPoint presentation failed post-build readability inspection.")

    response = GenerationResponse(
        generation_id=generation_id,
        source_template_file_id=source_template_file_id,
        source_excel_file_id=source_excel_file_id,
        generated_file_id=generation_id,
        record_count=len(valid_records),
        slide_count=len(prs.slides),
        status="completed",
        warnings=warnings,
        structured_warnings=structured_warnings,
        download_url=f"/api/generations/{generation_id}/download",
    )

    # Persist job metadata JSON file for historical integrity
    job_meta_path = settings.GENERATED_OUTPUTS_DIR / f"{generation_id}.json"
    import json
    with open(job_meta_path, "w", encoding="utf-8") as f:
        json.dump(response.dict(), f, indent=2)

    return response

