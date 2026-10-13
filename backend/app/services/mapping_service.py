from typing import Dict, List, Tuple, Optional
from app.schemas.template import TemplateInspectionResponse, SlideType
from app.schemas.mapping import (
    FieldMappingConfig,
    FieldMappingDetail,
    SlotMappingDetail,
    MappingStatus,
    GenerationReadiness,
    InspectionStatus,
    MappingValidationResponse,
    TemplateReadinessResponse,
    ErrorDetail,
    TemplateRequirements,
    SemanticFieldInfo,
)

CANONICAL_FIELDS = ["employee_name", "designation", "branch", "award_name"]


def extract_template_requirements(template_inspection: TemplateInspectionResponse) -> TemplateRequirements:
    """Dynamically derive required data fields and supported capacities from inspected slides."""
    if not template_inspection.valid or not template_inspection.slides:
        return TemplateRequirements()

    capacities = set()
    has_photo = False
    
    # Check repeating content slides
    for s in template_inspection.slides:
        if s.layout_model and s.layout_model.slide_type == SlideType.REPEATING_CONTENT:
            capacities.add(s.layout_model.capacity)
            for slot in s.layout_model.employee_slots:
                if slot.image_regions:
                    has_photo = True

    # Standard HR semantic fields detected from presentation cards
    # If template has repeating cards, each card provides employee_name, designation, and branch/location
    required_fields = [
        SemanticFieldInfo(
            field_key="employee_name",
            display_label="Employee Name",
            required=True,
            confidence=1.0,
        ),
        SemanticFieldInfo(
            field_key="designation",
            display_label="Designation / Role",
            required=True,
            confidence=1.0,
        ),
        SemanticFieldInfo(
            field_key="branch",
            display_label="Branch / Location",
            required=True,
            confidence=0.95,
        ),
    ]

    optional_fields = [
        SemanticFieldInfo(
            field_key="award_name",
            display_label="Award Title / Category",
            required=False,
            confidence=0.9,
        ),
    ]

    sorted_caps = sorted(capacities) if capacities else [1]

    return TemplateRequirements(
        required_fields=required_fields,
        optional_fields=optional_fields,
        supported_capacities=sorted_caps,
        has_photo_support=has_photo,
    )


ROLE_KEYWORDS = {
    "engineer", "specialist", "executive", "lead", "manager", "director", "consultant",
    "officer", "assistant", "technician", "supervisor", "installer", "operator", "analyst",
    "coordinator", "administrator", "advisor", "architect", "trainee", "intern", "vp", "president"
}

LOCATION_KEYWORDS = {
    "branch", "region", "office", "hub", "location", "area", "zone", "city",
    "bangalore", "bengaluru", "mumbai", "delhi", "chennai", "hyderabad", "pune", "kolkata",
    "ahmedabad", "gurgaon", "noida", "cochin", "kochi", "india", "north", "south", "east", "west"
}


def infer_card_line_mappings(sample_paragraphs: List[str]) -> Dict[int, str]:
    """
    Template-derived semantic line inference for multi-line employee cards.
    Infers which paragraph/line index maps to which employee field (employee_name, designation, branch, award_name)
    without assuming a fixed universal paragraph order.
    """
    if not sample_paragraphs:
        return {}

    cleaned_lines = [p.strip() for p in sample_paragraphs]
    n_lines = len(cleaned_lines)
    assigned: Dict[int, str] = {}
    unassigned_indices = set(range(n_lines))
    used_fields = set()

    # Pass 1: Explicit tokens / bracketed placeholders (e.g. "[Name]", "{Designation}", "<Branch>")
    for idx in list(unassigned_indices):
        text_lower = cleaned_lines[idx].lower().replace("[", "").replace("]", "").replace("{", "").replace("}", "").replace("<", "").replace(">", "").strip()
        for field in CANONICAL_FIELDS:
            field_clean = field.replace("_", "")
            if (field_clean in text_lower or text_lower in field_clean) and field not in used_fields:
                assigned[idx] = field
                used_fields.add(field)
                unassigned_indices.remove(idx)
                break

    # Pass 2: Lexical role & location matching
    for idx in list(unassigned_indices):
        text_lower = cleaned_lines[idx].lower()
        words = set(text_lower.replace(",", " ").replace("/", " ").replace("-", " ").split())
        
        # Check designation/role match
        if "designation" not in used_fields and (words & ROLE_KEYWORDS or any(kw in text_lower for kw in ["head of", "lead of", "chief"])):
            assigned[idx] = "designation"
            used_fields.add("designation")
            unassigned_indices.remove(idx)
            continue

        # Check location/branch match
        if "branch" not in used_fields and (words & LOCATION_KEYWORDS or any(kw in text_lower for kw in ["branch -", "location:"])):
            assigned[idx] = "branch"
            used_fields.add("branch")
            unassigned_indices.remove(idx)
            continue

        # Check award match
        if "award_name" not in used_fields and any(kw in text_lower for kw in ["award", "winner", "achievement", "recognition", "spotlight"]):
            assigned[idx] = "award_name"
            used_fields.add("award_name")
            unassigned_indices.remove(idx)
            continue

    # Pass 3: Template-structure-derived residual assignment
    # If employee_name is not yet assigned, the remaining line with title-cased/proper noun characteristics is employee_name
    if "employee_name" not in used_fields and unassigned_indices:
        # Prefer the first unassigned line, or line with 2-4 capitalized words
        best_name_idx = None
        for idx in sorted(unassigned_indices):
            line = cleaned_lines[idx]
            words = line.split()
            if 1 <= len(words) <= 5 and any(w.istitle() for w in words):
                best_name_idx = idx
                break
        if best_name_idx is None:
            best_name_idx = sorted(unassigned_indices)[0]

        assigned[best_name_idx] = "employee_name"
        used_fields.add("employee_name")
        unassigned_indices.remove(best_name_idx)

    # Remaining residual lines
    remaining_fields = [f for f in ["designation", "branch", "award_name"] if f not in used_fields]
    for idx in sorted(unassigned_indices):
        if remaining_fields:
            field = remaining_fields.pop(0)
            assigned[idx] = field
            used_fields.add(field)

    return assigned


def auto_suggest_mapping(template_inspection: TemplateInspectionResponse) -> FieldMappingConfig:
    """
    Automatically generate mapping configuration for the template.
    If the template contains repeating multi-card content slides, maps all employee slots
    on the first content slide. Otherwise falls back to single-card canonical field matching.
    """
    if not template_inspection.slides:
        return FieldMappingConfig()

    # Find the primary content slide (first REPEATING_CONTENT slide, or slide 0)
    target_slide_idx = 0
    target_slide = template_inspection.slides[0]

    for idx, s in enumerate(template_inspection.slides):
        if s.layout_model and s.layout_model.slide_type == SlideType.REPEATING_CONTENT and len(s.layout_model.employee_slots) > 1:
            target_slide_idx = idx
            target_slide = s
            break

    # If the target slide has employee slots, construct SlotMappingDetail for every slot
    if target_slide.layout_model and target_slide.layout_model.employee_slots:
        slots: List[SlotMappingDetail] = []
        for slot in target_slide.layout_model.employee_slots:
            txt_shape = slot.text_shapes[0] if slot.text_shapes else None
            img_shape = slot.image_regions[0] if slot.image_regions else None

            line_map: Optional[Dict[int, str]] = None
            if txt_shape:
                sample_paras = [ln.strip() for ln in txt_shape.text.split("\n") if ln.strip()]
                if len(sample_paras) >= 2:
                    line_map = infer_card_line_mappings(sample_paras)

            slot_detail = SlotMappingDetail(
                slot_index=slot.slot_index,
                employee_name=FieldMappingDetail(shape_name=txt_shape.shape_name, shape_id=txt_shape.shape_id, required=True, line_mappings=line_map) if txt_shape else None,
                designation=FieldMappingDetail(shape_name=txt_shape.shape_name, shape_id=txt_shape.shape_id, required=False, line_mappings=line_map) if txt_shape else None,
                branch=FieldMappingDetail(shape_name=txt_shape.shape_name, shape_id=txt_shape.shape_id, required=False, line_mappings=line_map) if txt_shape else None,
                award_name=None,
                photo_placeholder=FieldMappingDetail(shape_name=img_shape.shape_name, shape_id=img_shape.shape_id, required=False) if img_shape else None,
                line_mappings=line_map,
            )
            slots.append(slot_detail)

        return FieldMappingConfig(
            template_slide_index=target_slide_idx,
            slots=slots,
        )

    # Fallback to single-card matching on slide 0
    mapping_dict: Dict[str, FieldMappingDetail] = {}
    slide = template_inspection.slides[0]

    for field in CANONICAL_FIELDS:
        matched_detail = None
        for s in slide.text_shapes:
            name_clean = s.shape_name.lower().replace("_", "").replace(" ", "")
            field_clean = field.lower().replace("_", "").replace(" ", "")
            text_clean = s.text.lower().replace("_", "").replace(" ", "")

            if field_clean in name_clean or field_clean in text_clean:
                sample_paras = [ln.strip() for ln in s.text.split("\n") if ln.strip()]
                l_map = infer_card_line_mappings(sample_paras) if len(sample_paras) >= 2 else None
                matched_detail = FieldMappingDetail(
                    shape_name=s.shape_name,
                    shape_id=s.shape_id,
                    required=True,
                    line_mappings=l_map,
                )
                break

        if not matched_detail:
            for idx, s in enumerate(slide.text_shapes):
                if s.is_placeholder:
                    ph_type = (s.placeholder_type or "").lower()
                    if field == "employee_name" and ("title" in ph_type or "header" in ph_type or idx == 0):
                        matched_detail = FieldMappingDetail(
                            shape_name=s.shape_name,
                            shape_id=s.shape_id,
                            placeholder_index=idx,
                            required=True,
                        )
                        break
                    elif field == "designation" and ("body" in ph_type or idx == 1):
                        matched_detail = FieldMappingDetail(
                            shape_name=s.shape_name,
                            shape_id=s.shape_id,
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
    available_image_names = {i.shape_name for i in slide.image_shapes}
    all_available_shapes = available_shape_names.union(available_image_names)

    used_shapes: Dict[str, str] = {}
    configured_fields_count = 0

    if mapping.slots:
        # Multi-card slot validation mode
        for slot in mapping.slots:
            slot_fields = [
                ("employee_name", slot.employee_name),
                ("designation", slot.designation),
                ("branch", slot.branch),
                ("award_name", slot.award_name),
                ("photo_placeholder", slot.photo_placeholder),
            ]
            for field_name, detail in slot_fields:
                if detail and detail.shape_name:
                    configured_fields_count += 1
                    if detail.shape_name not in all_available_shapes:
                        err_msg = f"Slot #{slot.slot_index+1} mapped shape '{detail.shape_name}' for field '{field_name}' does not exist on slide #{slide_idx + 1}."
                        errors.append(err_msg)
                        structured_errors.append(
                            ErrorDetail(
                                code="MISSING_MAPPED_SHAPE",
                                field=field_name,
                                message=err_msg,
                                details={"shape_name": detail.shape_name, "slide_index": slide_idx, "slot_index": slot.slot_index},
                            )
                        )
                    # Register mapped shape
                    used_shapes[detail.shape_name] = f"slot_{slot.slot_index}"

            # Check if multi-line text shape in slot has line_mappings
            if slot.employee_name and slot.employee_name.shape_name:
                sh = next((s for s in slide.text_shapes if s.shape_name == slot.employee_name.shape_name), None)
                if sh:
                    paras = [ln.strip() for ln in sh.text.split("\n") if ln.strip()]
                    if len(paras) >= 2:
                        eff_lm = slot.line_mappings or (slot.employee_name.line_mappings if slot.employee_name else None)
                        if not eff_lm:
                            inferred = infer_card_line_mappings(paras)
                            if inferred:
                                slot.line_mappings = inferred
                                slot.employee_name.line_mappings = inferred
                            else:
                                err_msg = f"Slot #{slot.slot_index+1} multi-line shape '{slot.employee_name.shape_name}' lacks template-derived line mappings."
                                errors.append(err_msg)
                                structured_errors.append(
                                    ErrorDetail(
                                        code="AMBIGUOUS_LINE_MAPPING",
                                        field="line_mappings",
                                        message=err_msg,
                                        details={"slot_index": slot.slot_index, "shape_name": slot.employee_name.shape_name},
                                    )
                                )
    else:
        # Legacy single-card mapping validation mode
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
                    # Allow same shape if line_mappings is present and distinct
                    if not (detail.line_mappings or (mapping.employee_name and mapping.employee_name.line_mappings)):
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
    elif configured_fields_count > 0:
        status = MappingStatus.VALID
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

    requirements = extract_template_requirements(template_inspection)

    return TemplateReadinessResponse(
        template_id=template_inspection.template_id,
        filename=template_inspection.filename,
        inspection_status=insp_status,
        mapping_status=val_res.mapping_status,
        generation_readiness=readiness,
        requirements=requirements,
        configured_mapping=configured_mapping,
        suggested_mapping=suggested,
        warnings=all_warnings,
        errors=all_errors,
        structured_errors=all_structured_errors,
    )

