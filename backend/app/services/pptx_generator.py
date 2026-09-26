import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Dict
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.schemas.recognition import RecognitionRecord, ExcelValidationResponse
from app.schemas.template import TemplateInspectionResponse
from app.schemas.mapping import FieldMappingConfig, GenerationResponse, TextLengthWarningDetail
from app.services.template_inspector import inspect_powerpoint_template
from app.core.config import settings


def copy_slide_elements(source_slide, target_slide):
    """Deep clone shapes from source slide to target slide preserving position and formatting."""
    for shape in source_slide.shapes:
        if shape.has_text_frame:
            # Create matching text box
            new_shape = target_slide.shapes.add_textbox(
                shape.left, shape.top, shape.width, shape.height
            )
            new_shape.name = shape.name
            tf = new_shape.text_frame
            tf.word_wrap = shape.text_frame.word_wrap

            for p_idx, p in enumerate(shape.text_frame.paragraphs):
                if p_idx == 0:
                    new_p = tf.paragraphs[0]
                else:
                    new_p = tf.add_paragraph()
                
                new_p.alignment = p.alignment
                for r in p.runs:
                    new_r = new_p.add_run()
                    new_r.text = r.text
                    if r.font.name:
                        new_r.font.name = r.font.name
                    if r.font.size:
                        new_r.font.size = r.font.size
                    if r.font.bold is not None:
                        new_r.font.bold = r.font.bold
                    if r.font.italic is not None:
                        new_r.font.italic = r.font.italic
                    if r.font.color and hasattr(r.font.color, "rgb") and r.font.color.rgb:
                        new_r.font.color.rgb = r.font.color.rgb


def substitute_text_in_shape(shape, new_text: str) -> bool:
    if not shape.has_text_frame:
        return False

    tf = shape.text_frame
    if not tf.paragraphs:
        p = tf.add_paragraph()
        p.text = new_text
        return True

    # Preserve formatting of first run
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

    # Map required shapes on each slide
    field_map = {
        "employee_name": mapping_config.employee_name.shape_name if mapping_config.employee_name else None,
        "designation": mapping_config.designation.shape_name if mapping_config.designation else None,
        "branch": mapping_config.branch.shape_name if mapping_config.branch else None,
        "award_name": mapping_config.award_name.shape_name if mapping_config.award_name else None,
    }

    # Populate slides: 1 slide per employee record
    for idx, rec in enumerate(valid_records):
        if idx == 0 and slide_idx == 0:
            target_slide = template_slide_source
        else:
            target_slide = prs.slides.add_slide(blank_layout)
            copy_slide_elements(template_slide_source, target_slide)

        # Substitute mapped fields
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
                
                # Check for long text length warning heuristic (> 40 chars)
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

    return GenerationResponse(
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
