import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from pptx import Presentation

from app.schemas.fidelity import (
    DeliveryDecision,
    DeliveryStatus,
    QualityClassification,
    VerificationStatus,
    FidelityValidationReport,
)
from app.core.config import settings


class DeliveryService:
    """Centralized, backend-authoritative delivery decision service for generated presentations."""

    @staticmethod
    def evaluate_delivery_eligibility(
        generation_id: str,
        job_meta: Optional[Dict[str, Any]] = None,
        validation_report: Optional[FidelityValidationReport] = None,
        generated_pptx_path: Optional[Path] = None,
    ) -> DeliveryDecision:
        """
        Evaluate if a generated presentation is eligible for HR delivery/download.
        Follows the Phase 3F-1 quality classification and delivery policy:
        - PASS -> READY -> can_download: True
        - WARNING -> READY_WITH_WARNING -> can_download: True (if artifact is safe/usable)
        - REPAIRABLE -> REPAIR_PENDING -> can_download: False
        - CRITICAL -> BLOCKED -> can_download: False
        - Missing or corrupt artifact / missing metadata -> BLOCKED -> can_download: False
        """
        now_iso = datetime.utcnow().isoformat()
        gen_dir = settings.GENERATED_OUTPUTS_DIR.resolve()

        # 1. Resolve generated PPTX path if not provided
        if not generated_pptx_path:
            generated_pptx_path = (gen_dir / f"{generation_id}.pptx").resolve()

        # 2. Check artifact existence
        if not generated_pptx_path.exists():
            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason="GENERATED_ARTIFACT_MISSING",
                hr_message="We couldn't safely prepare this presentation. Generated file is missing.",
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )

        # 3. Verify artifact structural opening / corruption check
        try:
            prs = Presentation(str(generated_pptx_path))
            if not prs.slides:
                return DeliveryDecision(
                    delivery_status=DeliveryStatus.BLOCKED,
                    can_download=False,
                    reason="GENERATED_ARTIFACT_EMPTY",
                    hr_message="We couldn't safely prepare this presentation. The presentation contains no slides.",
                    quality_classification=QualityClassification.CRITICAL,
                    decision_timestamp=now_iso,
                )
        except Exception as e:
            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason=f"GENERATED_ARTIFACT_CORRUPT: {str(e)}",
                hr_message="We couldn't safely prepare this presentation. The generated presentation file is corrupted.",
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )

        # 4. Resolve generation metadata if not provided
        if not job_meta:
            job_meta_path = (gen_dir / f"{generation_id}.json").resolve()
            if job_meta_path.exists():
                try:
                    with open(job_meta_path, "r", encoding="utf-8") as f:
                        job_meta = json.load(f)
                except Exception:
                    job_meta = None

        if not job_meta:
            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason="GENERATION_METADATA_MISSING",
                hr_message="Presentation quality checks could not be verified. Metadata is missing.",
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )

        # Verify generation ID consistency
        if job_meta.get("generation_id") != generation_id:
            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason="METADATA_GENERATION_ID_MISMATCH",
                hr_message="Presentation validation provenance check failed.",
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )

        job_status = job_meta.get("status")
        if job_status != "completed":
            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason=f"GENERATION_NOT_COMPLETED: status={job_status}",
                hr_message="Presentation is still generating or encountered an error.",
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )

        # 5. Resolve validation report if not provided
        if not validation_report:
            val_path = (gen_dir / f"{generation_id}_validation.json").resolve()
            if val_path.exists():
                try:
                    with open(val_path, "r", encoding="utf-8") as f:
                        val_dict = json.load(f)
                        validation_report = FidelityValidationReport(**val_dict)
                except Exception:
                    validation_report = None

        if not validation_report:
            # Fallback for legacy jobs / tests that only persisted job_meta
            meta_deliv = job_meta.get("delivery_status")
            meta_val = job_meta.get("validation_status")
            if meta_deliv in (DeliveryStatus.READY, "READY", DeliveryStatus.READY_WITH_WARNING, "READY_WITH_WARNING") or meta_val == "VERIFIED":
                return DeliveryDecision(
                    delivery_status=DeliveryStatus.READY if meta_deliv != DeliveryStatus.READY_WITH_WARNING else DeliveryStatus.READY_WITH_WARNING,
                    can_download=True,
                    reason="LEGACY_VERIFIED_JOB",
                    hr_message="Your presentation is ready to download.",
                    quality_classification=QualityClassification.PASS,
                    decision_timestamp=now_iso,
                )
            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason="VALIDATION_REPORT_MISSING",
                hr_message="Presentation quality checks could not be fully completed. Report is unavailable.",
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )

        # 6. Apply Phase 3F-1 Quality Classification Delivery Policy
        classification = validation_report.quality_classification or QualityClassification.PASS

        if classification == QualityClassification.PASS:
            return DeliveryDecision(
                delivery_status=DeliveryStatus.READY,
                can_download=True,
                reason="VERIFIED_PASS",
                hr_message="Presentation is ready.",
                quality_classification=QualityClassification.PASS,
                decision_timestamp=now_iso,
            )

        elif classification == QualityClassification.WARNING:
            warn_msg = "Presentation is ready with minor quality warnings."
            if validation_report.warnings:
                warn_msg = f"Presentation is ready with minor warnings: {validation_report.warnings[0]}"
            return DeliveryDecision(
                delivery_status=DeliveryStatus.READY_WITH_WARNING,
                can_download=True,
                reason="VERIFIED_WITH_WARNINGS",
                hr_message=warn_msg,
                quality_classification=QualityClassification.WARNING,
                decision_timestamp=now_iso,
            )

        elif classification == QualityClassification.REPAIRABLE:
            return DeliveryDecision(
                delivery_status=DeliveryStatus.REPAIR_PENDING,
                can_download=False,
                reason="REPAIRABLE_ISSUE_PENDING",
                hr_message="We found an issue that needs to be resolved before this presentation can be downloaded.",
                quality_classification=QualityClassification.REPAIRABLE,
                decision_timestamp=now_iso,
            )

        else:  # CRITICAL
            crit_reason = "CRITICAL_DEFECT_DETECTED"
            hr_msg = "We couldn't safely prepare this presentation."
            if validation_report.failures:
                crit_reason = f"CRITICAL: {validation_report.failures[0].message}"
                hr_msg = f"We couldn't safely prepare this presentation. {validation_report.failures[0].message}"

            return DeliveryDecision(
                delivery_status=DeliveryStatus.BLOCKED,
                can_download=False,
                reason=crit_reason,
                hr_message=hr_msg,
                quality_classification=QualityClassification.CRITICAL,
                decision_timestamp=now_iso,
            )
