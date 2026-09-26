from typing import Dict, List, Tuple
from app.schemas.template import TemplateInspectionResponse
from app.schemas.mapping import (
    FieldMappingConfig,
    FieldMappingDetail,
    MappingStatus,
    GenerationReadiness,
    InspectionStatus,
    MappingValidationResponse,
    TemplateReadinessResponse,
    ErrorDetail,
)

CANONICAL_FIELDS = ["employee_name", "designation", "branch", "award_name"]


def auto_suggest_mapping(template_inspection: TemplateInspectionResponse) -> FieldMappingConfig:
    mapping_dict: Dict[str, FieldMappingDetail] = {}

    if not template_inspection.slides:
        return FieldMappingConfig()

    slide = template_inspection.slides[0]
    
    for field in CANONICAL_FIELDS:
        matched_detail = None

        # Search text shapes for exact or fuzzy shape name or text match
        for s in slide.text_shapes:
            name_clean = s.shape_name.lower().replace("_", "").replace(" ", "")
            field_clean = field.lower().replace("_", "").replace(" ", "")

            text_clean = s.text.lower().replace("_", "").replace(" ", "")

            if field_clean in name_clean or field_clean in text_clean:
                matched_detail = FieldMappingDetail(
                    shape_name=s.shape_name,
                    required=True,
                )
                break

        # Fallback to placeholders
        if not matched_detail:
            for idx, s in enumerate(slide.text_shapes):
                if s.is_placeholder:
                    ph_type = (s.placeholder_type or "").lower()
                    if field == "employee_name" and ("title" in ph_type or "header" in ph_type or idx == 0):
                        matched_detail = FieldMappingDetail(
                            shape_name=s.shape_name,
                            placeholder_index=idx,
                            required=True,
                        )
                        break
                    elif field == "designation" and ("body" in ph_type or idx == 1):
                        matched_detail = FieldMappingDetail(
                            shape_name=s.shape_name,
                            placeholder_index=idx,
                            required=True,
                        )
                        break

        if matched_detail:
            mapping_dict[field] = matched_detail

    return FieldMappingConfig(**mapping_dict)


def validate_mapping_config(
    mapping: FieldMappingConfig, template_inspection: TemplateInspectionResponse
) -> MappingValidationResponse:
    errors: List[str] = []
    structured_errors: List[ErrorDetail] = []
    warnings: List[str] = []

    if not template_inspection.valid or not template_inspection.slides:
        err_msg = "Template inspection data is invalid or contains no slides."
        return MappingValidationResponse(
            valid=False,
            mapping_status=MappingStatus.INVALID,
            errors=[err_msg],
            structured_errors=[ErrorDetail(code="INVALID_TEMPLATE_INSPECTION", message=err_msg)],
            warnings=[],
        )

    slide_idx = mapping.template_slide_index if mapping else 0
    if slide_idx < 0 or slide_idx >= len(template_inspection.slides):
        err_msg = f"Configured template_slide_index {slide_idx} is out of bounds (slide count: {len(template_inspection.slides)})."
        return MappingValidationResponse(
            valid=False,
            mapping_status=MappingStatus.INVALID,
            errors=[err_msg],
            structured_errors=[ErrorDetail(code="INVALID_SLIDE_INDEX", message=err_msg)],
            warnings=[],
        )

    slide = template_inspection.slides[slide_idx]
    available_shape_names = {s.shape_name for s in slide.text_shapes}

    used_shapes: Dict[str, str] = {}
    configured_fields_count = 0

    mapping_fields = [
        ("employee_name", mapping.employee_name),
        ("designation", mapping.designation),
        ("branch", mapping.branch),
        ("award_name", mapping.award_name),
    ]

    for field_name, detail in mapping_fields:
        if detail and detail.shape_name:
            configured_fields_count += 1
            
            if detail.shape_name not in available_shape_names:
                err_msg = f"Mapped shape '{detail.shape_name}' for field '{field_name}' does not exist on slide #{slide_idx + 1}."
                errors.append(err_msg)
                structured_errors.append(
                    ErrorDetail(
                        code="MISSING_MAPPED_SHAPE",
                        field=field_name,
                        message=err_msg,
                        details={"shape_name": detail.shape_name, "slide_index": slide_idx},
                    )
                )

            if detail.shape_name in used_shapes:
                err_msg = f"AMBIGUOUS_SHAPE_MAPPING: Shape '{detail.shape_name}' is assigned to multiple fields ('{used_shapes[detail.shape_name]}' and '{field_name}')."
                errors.append(err_msg)
                structured_errors.append(
                    ErrorDetail(
                        code="AMBIGUOUS_SHAPE_MAPPING",
                        field=field_name,
                        message=err_msg,
                        details={
                            "shape_name": detail.shape_name,
                            "conflicting_field": used_shapes[detail.shape_name],
                        },
                    )
                )
            else:
                used_shapes[detail.shape_name] = field_name
        else:
            warnings.append(f"Required field '{field_name}' is not currently mapped.")

    if errors:
        status = MappingStatus.INVALID
    elif configured_fields_count == len(CANONICAL_FIELDS):
        status = MappingStatus.VALID
    elif configured_fields_count > 0:
        status = MappingStatus.PARTIALLY_CONFIGURED
    else:
        status = MappingStatus.NOT_CONFIGURED

    return MappingValidationResponse(
        valid=len(errors) == 0 and configured_fields_count > 0,
        mapping_status=status,
        errors=errors,
        structured_errors=structured_errors,
        warnings=warnings,
    )


def calculate_template_readiness(
    template_inspection: TemplateInspectionResponse,
    configured_mapping: FieldMappingConfig = None,
) -> TemplateReadinessResponse:
    suggested = auto_suggest_mapping(template_inspection)
    mapping_to_use = configured_mapping or suggested

    val_res = validate_mapping_config(mapping_to_use, template_inspection)

    all_warnings = list(template_inspection.warnings) + val_res.warnings
    all_errors = list(val_res.errors)
    all_structured_errors = list(val_res.structured_errors)

    if not template_inspection.valid:
        readiness = GenerationReadiness.REQUIRES_TEMPLATE
        insp_status = InspectionStatus.FAILED
    elif val_res.mapping_status == MappingStatus.INVALID:
        readiness = GenerationReadiness.BLOCKED_BY_VALIDATION
        insp_status = InspectionStatus.SUCCESS
    elif val_res.mapping_status != MappingStatus.VALID:
        readiness = GenerationReadiness.REQUIRES_MAPPING
        insp_status = InspectionStatus.SUCCESS
    else:
        readiness = GenerationReadiness.READY_FOR_GENERATION
        insp_status = InspectionStatus.SUCCESS

    return TemplateReadinessResponse(
        template_id=template_inspection.template_id,
        filename=template_inspection.filename,
        inspection_status=insp_status,
        mapping_status=val_res.mapping_status,
        generation_readiness=readiness,
        configured_mapping=configured_mapping,
        suggested_mapping=suggested,
        warnings=all_warnings,
        errors=all_errors,
        structured_errors=all_structured_errors,
    )
