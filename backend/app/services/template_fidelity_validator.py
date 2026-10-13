import io
from pathlib import Path
from typing import List, Optional, Dict, Any
from pptx import Presentation

from app.schemas.fidelity import (
    TemplateFidelityManifest,
    FidelityValidationReport,
    SlideValidationResult,
    ValidationFailureDetail,
    FailureSeverity,
    VerificationStatus,
    SlideLayoutManifest,
    QualityClassification,
    DeliveryStatus,
    DeliveryDecision,
)
from app.services.pptx_renderer import PptxRenderer

EMU_PER_INCH = 914400.0


class TemplateFidelityValidator:
    """Generic fidelity validation service comparing generated presentations against source manifests."""

    @staticmethod
    def validate_presentation(
        generated_pptx_bytes: bytes,
        manifest: TemplateFidelityManifest,
        expected_records_count: int,
        generated_pptx_path: Optional[Path] = None,
        source_pptx_path: Optional[Path] = None,
        render_output_dir: Optional[Path] = None,
    ) -> FidelityValidationReport:
        prs = Presentation(io.BytesIO(generated_pptx_bytes))
        gen_w_in = prs.slide_width / EMU_PER_INCH
        gen_h_in = prs.slide_height / EMU_PER_INCH

        slide_reports: List[SlideValidationResult] = []
        all_failures: List[ValidationFailureDetail] = []
        all_warnings: List[str] = []

        # 1. Dimension & Aspect Ratio Check
        dim_tol = 0.05  # 0.05 inches tolerance
        if abs(gen_w_in - manifest.slide_width_inches) > dim_tol or abs(gen_h_in - manifest.slide_height_inches) > dim_tol:
            fail = ValidationFailureDetail(
                slide_number=0,
                region="presentation_dimensions",
                failure_type="DIMENSION_MISMATCH",
                severity=FailureSeverity.CRITICAL,
                expected=f"{manifest.slide_width_inches}x{manifest.slide_height_inches} in",
                actual=f"{round(gen_w_in, 3)}x{round(gen_h_in, 3)} in",
                message=f"Presentation dimensions {round(gen_w_in, 2)}x{round(gen_h_in, 2)} differ from master template {manifest.slide_width_inches}x{manifest.slide_height_inches}.",
                is_repairable=False,
                is_conclusive=True,
            )
            all_failures.append(fail)

        # Map layouts by variant / slide index
        layout_map = {l.source_slide_index: l for l in manifest.layouts}

        # Render slides if paths are available and renderer is functional
        gen_slide_pngs: List[Path] = []
        src_slide_pngs: List[Path] = []
        visual_verification_executed = False
        renderer_diagnostic_msg: Optional[str] = None

        if generated_pptx_path and render_output_dir:
            try:
                gen_dir = render_output_dir / "generated_renders"
                gen_slide_pngs = PptxRenderer.render_presentation_slides(generated_pptx_path, gen_dir)
                if source_pptx_path:
                    src_dir = render_output_dir / "source_renders"
                    src_slide_pngs = PptxRenderer.render_presentation_slides(source_pptx_path, src_dir)
                
                # Visual verification executed if generated slides rendered successfully
                if gen_slide_pngs and len(gen_slide_pngs) == len(prs.slides):
                    visual_verification_executed = True
                elif not gen_slide_pngs:
                    renderer_diagnostic_msg = "PowerPoint rendering produced 0 slide images."
            except Exception as e:
                renderer_diagnostic_msg = f"Renderer execution encountered: {str(e)}"

        # 2. Per-slide validation
        for s_idx, slide in enumerate(prs.slides):
            slide_num = s_idx + 1
            slide_failures: List[ValidationFailureDetail] = []
            slide_warnings: List[str] = []

            # Determine matched source layout (default to content layout)
            matched_layout: Optional[SlideLayoutManifest] = None
            if len(manifest.layouts) == 1:
                matched_layout = manifest.layouts[0]
            else:
                # Find matching layout from repeating content
                content_layouts = [l for l in manifest.layouts if l.slide_type == "REPEATING_CONTENT"]
                matched_layout = content_layouts[0] if content_layouts else manifest.layouts[0]

            layout_var_id = matched_layout.layout_variant_id if matched_layout else "unknown"

            # Check static shapes
            gen_shapes_by_name = {s.name: s for s in slide.shapes}

            if matched_layout:
                for st in matched_layout.static_regions:
                    if st.shape_name not in gen_shapes_by_name:
                        # Missing static asset
                        slide_failures.append(
                            ValidationFailureDetail(
                                slide_number=slide_num,
                                region=st.shape_name,
                                failure_type="MISSING_STATIC_ASSET",
                                severity=FailureSeverity.CRITICAL if st.is_image else FailureSeverity.HIGH,
                                expected=f"Static shape '{st.shape_name}' present",
                                actual="Missing from generated slide",
                                message=f"Slide #{slide_num} is missing required static asset '{st.shape_name}'.",
                                is_repairable=True,
                                is_conclusive=True,
                            )
                        )

                # Check photo regions: distinguish genuine loss from candidate photo frames
                for pr in matched_layout.photo_regions:
                    found_shape = gen_shapes_by_name.get(pr.shape_name)

                    if not found_shape:
                        # Secondary lookup: check if any picture or shape exists at matching bounding box
                        candidate_at_bbox = None
                        for s in slide.shapes:
                            s_l = s.left / EMU_PER_INCH
                            s_t = s.top / EMU_PER_INCH
                            s_w = s.width / EMU_PER_INCH
                            s_h = s.height / EMU_PER_INCH
                            if abs(s_l - pr.bbox.left_inches) <= 0.25 and abs(s_t - pr.bbox.top_inches) <= 0.25:
                                candidate_at_bbox = s
                                break

                        if candidate_at_bbox:
                            # Frame exists at exact position under renamed or converted shape ID -> NON-CRITICAL WARNING
                            slide_warnings.append(
                                f"Photo region '{pr.shape_name}' preserved at expected coordinates under shape '{candidate_at_bbox.name}'."
                            )
                        else:
                            # Photo region genuinely removed / missing -> CRITICAL / REPAIRABLE defect
                            slide_failures.append(
                                ValidationFailureDetail(
                                    slide_number=slide_num,
                                    region=pr.shape_name,
                                    failure_type="MISSING_PHOTO_REGION",
                                    severity=FailureSeverity.CRITICAL,
                                    expected=f"Photo region '{pr.shape_name}' preserved",
                                    actual="Removed / Missing",
                                    message=f"Slide #{slide_num} lost photo region '{pr.shape_name}'. Photo slot frame must be preserved.",
                                    is_repairable=True,
                                    is_conclusive=True,
                                )
                            )
                    else:
                        # Verify geometry bounds
                        g_l = found_shape.left / EMU_PER_INCH
                        g_t = found_shape.top / EMU_PER_INCH
                        g_w = found_shape.width / EMU_PER_INCH
                        g_h = found_shape.height / EMU_PER_INCH
                        if abs(g_l - pr.bbox.left_inches) > 0.2 or abs(g_t - pr.bbox.top_inches) > 0.2:
                            slide_failures.append(
                                ValidationFailureDetail(
                                    slide_number=slide_num,
                                    region=pr.shape_name,
                                    failure_type="GEOMETRY_DEVIATION",
                                    severity=FailureSeverity.HIGH,
                                    expected=f"Pos ({pr.bbox.left_inches}, {pr.bbox.top_inches})",
                                    actual=f"Pos ({round(g_l, 2)}, {round(g_t, 2)})",
                                    message=f"Photo region '{pr.shape_name}' displaced beyond tolerance.",
                                    is_repairable=True,
                                    is_conclusive=True,
                                )
                            )

                # Check boundary overflow: shapes extending substantially beyond slide canvas
                for s in slide.shapes:
                    s_r = (s.left + s.width) / EMU_PER_INCH
                    s_b = (s.top + s.height) / EMU_PER_INCH
                    if s_r > (gen_w_in + 0.5) or s_b > (gen_h_in + 0.5):
                        slide_warnings.append(
                            f"Slide #{slide_num} shape '{s.name}' extends beyond slide boundaries ({round(s_r, 1)}in x {round(s_b, 1)}in vs {round(gen_w_in, 1)}in x {round(gen_h_in, 1)}in)."
                        )

            # Visual inspection of rendered slide image if available
            vis_score = 1.0
            if visual_verification_executed and s_idx < len(gen_slide_pngs):
                gen_png = gen_slide_pngs[s_idx]
                slide_insp = PptxRenderer.inspect_rendered_slide(gen_png)
                if not slide_insp["is_readable"]:
                    slide_failures.append(
                        ValidationFailureDetail(
                            slide_number=slide_num,
                            region="rendered_slide",
                            failure_type="RENDERED_SLIDE_UNREADABLE",
                            severity=FailureSeverity.CRITICAL,
                            expected="Rendered slide is valid readable image",
                            actual="Unreadable or corrupt rendered image",
                            message=f"Slide #{slide_num} rendered output could not be read as valid image.",
                            is_repairable=False,
                            is_conclusive=True,
                        )
                    )
                elif slide_insp["is_blank"] and len(slide.shapes) > 0:
                    # Genuinely blank rendered slide when shapes were supposed to render
                    slide_failures.append(
                        ValidationFailureDetail(
                            slide_number=slide_num,
                            region="rendered_slide",
                            failure_type="BLANK_RENDERED_SLIDE",
                            severity=FailureSeverity.CRITICAL,
                            expected="Rendered slide contains visible content",
                            actual="Slide rendered completely blank/empty",
                            message=f"Slide #{slide_num} rendered as blank canvas despite containing shapes.",
                            is_repairable=False,
                            is_conclusive=True,
                        )
                    )

                # Visual similarity comparison against base layout render if source render exists
                if src_slide_pngs:
                    src_png = src_slide_pngs[0]
                    mask_boxes = [
                        [dr.bbox.left_inches, dr.bbox.top_inches, dr.bbox.width_inches, dr.bbox.height_inches]
                        for dr in (matched_layout.dynamic_regions if matched_layout else [])
                    ]
                    vis_score = PptxRenderer.compute_visual_similarity(
                        src_png,
                        gen_png,
                        dynamic_mask_boxes=mask_boxes,
                        slide_width_inches=manifest.slide_width_inches,
                        slide_height_inches=manifest.slide_height_inches,
                    )
                    if vis_score < 0.70:
                        slide_warnings.append(f"Visual similarity score ({round(vis_score, 2)}) is below 0.70 threshold.")

            slide_passed = len([f for f in slide_failures if f.severity in (FailureSeverity.CRITICAL, FailureSeverity.HIGH)]) == 0
            slide_report = SlideValidationResult(
                slide_number=slide_num,
                source_layout_variant_id=layout_var_id,
                passed=slide_passed,
                structural_score=1.0 if not slide_failures else 0.5,
                geometry_score=0.0 if any(f.failure_type == "GEOMETRY_DEVIATION" for f in slide_failures) else 1.0,
                static_asset_score=0.0 if any(f.failure_type == "MISSING_STATIC_ASSET" for f in slide_failures) else 1.0,
                semantic_score=0.0 if any(f.failure_type == "SEMANTIC_PLACEMENT_ERROR" for f in slide_failures) else 1.0,
                photo_slot_score=0.0 if any(f.failure_type == "MISSING_PHOTO_REGION" for f in slide_failures) else 1.0,
                visual_score=round(vis_score, 3),
                failures=slide_failures,
                warnings=slide_warnings,
            )
            slide_reports.append(slide_report)
            all_failures.extend(slide_failures)
            all_warnings.extend(slide_warnings)

        # Deduplicate identical failure messages for same region/failure_type
        seen_keys = set()
        deduped_failures: List[ValidationFailureDetail] = []
        for f in all_failures:
            f_key = (f.failure_type, f.region, f.severity)
            if f_key not in seen_keys:
                seen_keys.add(f_key)
                deduped_failures.append(f)

        critical_count = len([f for f in deduped_failures if f.severity == FailureSeverity.CRITICAL])
        high_count = len([f for f in deduped_failures if f.severity == FailureSeverity.HIGH])
        repairable_count = len([f for f in deduped_failures if f.is_repairable and f.severity in (FailureSeverity.CRITICAL, FailureSeverity.HIGH)])

        # Quality Classification
        # If all critical/high failures are marked is_repairable, classify as REPAIRABLE -> triggers bounded repair pipeline
        has_unrepairable = any(not f.is_repairable for f in deduped_failures if f.severity in (FailureSeverity.CRITICAL, FailureSeverity.HIGH))
        has_defects = (critical_count + high_count) > 0

        if has_defects:
            if not has_unrepairable and repairable_count > 0:
                quality_class = QualityClassification.REPAIRABLE
                delivery_st = DeliveryStatus.REPAIR_PENDING
                ver_status = VerificationStatus.BLOCKED
            else:
                quality_class = QualityClassification.CRITICAL
                delivery_st = DeliveryStatus.BLOCKED
                ver_status = VerificationStatus.BLOCKED
        elif len(all_warnings) > 0:
            quality_class = QualityClassification.WARNING
            delivery_st = DeliveryStatus.READY_WITH_WARNING
            ver_status = VerificationStatus.VERIFIED
        else:
            quality_class = QualityClassification.PASS
            delivery_st = DeliveryStatus.READY
            ver_status = VerificationStatus.VERIFIED

        passed_slides = sum(1 for sr in slide_reports if sr.passed)
        overall_score = round(passed_slides / max(1, len(slide_reports)), 2)

        # Visual verification result status: do NOT falsely claim PASS if not executed
        if visual_verification_executed:
            visual_res = "WARN" if any("Visual similarity score" in w for w in all_warnings) else "PASS"
        else:
            visual_res = "UNAVAILABLE"
            reason_diag = f" ({renderer_diagnostic_msg})" if renderer_diagnostic_msg else ""
            all_warnings.append(f"Visual rendering comparison was unavailable in this environment{reason_diag}.")

        # Build delivery decision
        from datetime import datetime
        deliv_dec = DeliveryDecision(
            delivery_status=delivery_st,
            can_download=(delivery_st in (DeliveryStatus.READY, DeliveryStatus.READY_WITH_WARNING)),
            reason=f"Quality: {quality_class.value}",
            hr_message="Presentation is ready." if delivery_st == DeliveryStatus.READY else (
                "Presentation is ready with minor warnings." if delivery_st == DeliveryStatus.READY_WITH_WARNING else (
                    "We found an issue that needs to be resolved before this presentation can be downloaded." if delivery_st == DeliveryStatus.REPAIR_PENDING else
                    "We couldn't safely prepare this presentation."
                )
            ),
            quality_classification=quality_class,
            decision_timestamp=datetime.utcnow().isoformat(),
        )

        return FidelityValidationReport(
            generation_id=manifest.manifest_id,
            verification_status=ver_status,
            quality_classification=quality_class,
            delivery_status=delivery_st,
            delivery_decision=deliv_dec,
            overall_score=overall_score,
            slides_checked=len(prs.slides),
            slides_passed=passed_slides,
            slides_failed=len(prs.slides) - passed_slides,
            structural_result="FAIL" if any(f.failure_type in ("DIMENSION_MISMATCH", "MISSING_STATIC_ASSET") for f in deduped_failures) else "PASS",
            geometry_result="FAIL" if any(f.failure_type == "GEOMETRY_DEVIATION" for f in deduped_failures) else "PASS",
            static_asset_result="FAIL" if any(f.failure_type == "MISSING_STATIC_ASSET" for f in deduped_failures) else "PASS",
            semantic_result="FAIL" if any(f.failure_type == "SEMANTIC_PLACEMENT_ERROR" for f in deduped_failures) else "PASS",
            photo_slot_result="FAIL" if any(f.failure_type == "MISSING_PHOTO_REGION" for f in deduped_failures) else "PASS",
            visual_result=visual_res,
            visual_verification_executed=visual_verification_executed,
            failures=deduped_failures,
            warnings=all_warnings,
            slide_reports=slide_reports,
        )
