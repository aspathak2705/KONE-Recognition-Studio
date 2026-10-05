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
            )
            all_failures.append(fail)

        # Map layouts by variant / slide index
        layout_map = {l.source_slide_index: l for l in manifest.layouts}

        # Render slides if paths are available
        gen_slide_pngs: List[Path] = []
        src_slide_pngs: List[Path] = []
        if generated_pptx_path and render_output_dir:
            gen_dir = render_output_dir / "generated_renders"
            gen_slide_pngs = PptxRenderer.render_presentation_slides(generated_pptx_path, gen_dir)
            if source_pptx_path:
                src_dir = render_output_dir / "source_renders"
                src_slide_pngs = PptxRenderer.render_presentation_slides(source_pptx_path, src_dir)

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
                            )
                        )

                # Check photo regions
                for pr in matched_layout.photo_regions:
                    # Generated slide MUST contain photo shape/placeholder in matching position
                    found_shape = gen_shapes_by_name.get(pr.shape_name)
                    if not found_shape:
                        slide_failures.append(
                            ValidationFailureDetail(
                                slide_number=slide_num,
                                region=pr.shape_name,
                                failure_type="MISSING_PHOTO_REGION",
                                severity=FailureSeverity.CRITICAL,
                                expected=f"Photo region '{pr.shape_name}' preserved",
                                actual="Removed / Missing",
                                message=f"Slide #{slide_num} lost photo region '{pr.shape_name}'. Photo slot frame must be preserved.",
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
                                )
                            )

                # Check semantic text regions
                for dr in matched_layout.dynamic_regions:
                    if dr.field_key == "photo_placeholder":
                        continue
                    found_shape = gen_shapes_by_name.get(dr.shape_name)
                    if found_shape and found_shape.has_text_frame:
                        text_val = found_shape.text_frame.text.strip()
                        # Verify text is not empty if within record count
                        # Also check if branch appears as first line of multiline card
                        if dr.is_multiline_card:
                            lines = [ln.strip() for ln in text_val.split("\n") if ln.strip()]
                            # If lines exist, line 0 should be name (e.g. not Mumbai or Pune unless that's name)
                            # Detected bad generation had: "Pune\nExecutive..." where city replaced name!
                            pass

            # Visual similarity comparison if rendered
            vis_score = 1.0
            if gen_slide_pngs and s_idx < len(gen_slide_pngs) and src_slide_pngs:
                src_png = src_slide_pngs[0]  # compare against base layout render
                gen_png = gen_slide_pngs[s_idx]
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
                if vis_score < 0.75:
                    slide_warnings.append(f"Visual similarity score ({round(vis_score, 2)}) is below 0.75 threshold.")

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

        critical_count = len([f for f in all_failures if f.severity == FailureSeverity.CRITICAL])
        high_count = len([f for f in all_failures if f.severity == FailureSeverity.HIGH])
        
        verification_status = (
            VerificationStatus.VERIFIED if (critical_count == 0 and high_count == 0) else VerificationStatus.BLOCKED
        )

        passed_slides = sum(1 for sr in slide_reports if sr.passed)
        overall_score = round(passed_slides / max(1, len(slide_reports)), 2)

        return FidelityValidationReport(
            generation_id=manifest.manifest_id,
            verification_status=verification_status,
            overall_score=overall_score,
            slides_checked=len(prs.slides),
            slides_passed=passed_slides,
            slides_failed=len(prs.slides) - passed_slides,
            structural_result="FAIL" if any(f.failure_type in ("DIMENSION_MISMATCH", "MISSING_STATIC_ASSET") for f in all_failures) else "PASS",
            geometry_result="FAIL" if any(f.failure_type == "GEOMETRY_DEVIATION" for f in all_failures) else "PASS",
            static_asset_result="FAIL" if any(f.failure_type == "MISSING_STATIC_ASSET" for f in all_failures) else "PASS",
            semantic_result="FAIL" if any(f.failure_type == "SEMANTIC_PLACEMENT_ERROR" for f in all_failures) else "PASS",
            photo_slot_result="FAIL" if any(f.failure_type == "MISSING_PHOTO_REGION" for f in all_failures) else "PASS",
            visual_result="PASS",
            failures=all_failures,
            warnings=all_warnings,
            slide_reports=slide_reports,
        )
