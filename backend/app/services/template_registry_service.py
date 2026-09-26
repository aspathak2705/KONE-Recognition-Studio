import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from fastapi import UploadFile, HTTPException

from app.core.config import settings
from app.schemas.template import TemplateInspectionResponse
from app.schemas.mapping import (
    FieldMappingConfig,
    InspectionStatus,
    MappingStatus,
    GenerationReadiness,
)
from app.schemas.template_registry import (
    TemplateMetadata,
    TemplateVersion,
    TemplateRegistrationResponse,
)
from app.services.template_inspector import inspect_powerpoint_template
from app.services.mapping_service import (
    validate_mapping_config,
    calculate_template_readiness,
    auto_suggest_mapping,
)
from app.api.generation import HEX_ID_PATTERN


def calculate_pptx_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of binary PPTX content."""
    return hashlib.sha256(content).hexdigest()


class TemplateRegistryService:
    def __init__(self, registry_dir: Optional[Path] = None):
        self.registry_dir = registry_dir or (settings.STORAGE_DIR / "templates")
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def _get_template_dir(self, template_id: str) -> Path:
        if not HEX_ID_PATTERN.match(template_id):
            raise HTTPException(status_code=400, detail="Invalid template identifier format: Expected 32-character hex ID.")
        path = (self.registry_dir / template_id).resolve()
        if not str(path).startswith(str(self.registry_dir.resolve())):
            raise HTTPException(status_code=400, detail="Access denied: invalid template path.")
        return path

    def list_templates(self, include_archived: bool = False) -> List[TemplateMetadata]:
        templates: List[TemplateMetadata] = []
        if not self.registry_dir.exists():
            return templates

        for folder in self.registry_dir.iterdir():
            if folder.is_dir() and HEX_ID_PATTERN.match(folder.name):
                meta_file = folder / "template.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            meta = TemplateMetadata(**data)
                            if include_archived or not meta.is_archived:
                                templates.append(meta)
                    except Exception:
                        continue

        # Sort by updated_at descending
        templates.sort(key=lambda t: t.updated_at, reverse=True)
        return templates

    def get_template(self, template_id: str) -> Optional[TemplateMetadata]:
        tpl_dir = self._get_template_dir(template_id)
        meta_file = tpl_dir / "template.json"
        if not meta_file.exists():
            return None
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return TemplateMetadata(**data)

    def save_template_metadata(self, meta: TemplateMetadata) -> None:
        tpl_dir = self._get_template_dir(meta.template_id)
        tpl_dir.mkdir(parents=True, exist_ok=True)
        meta.updated_at = datetime.utcnow().isoformat()
        meta_file = tpl_dir / "template.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta.dict(), f, indent=2)

    def find_by_hash(self, file_hash: str) -> Optional[Tuple[TemplateMetadata, TemplateVersion]]:
        """Search all registered templates for a version matching the given SHA-256 file hash."""
        for meta in self.list_templates(include_archived=True):
            for version in meta.versions:
                if version.file_hash.lower() == file_hash.lower():
                    return meta, version
        return None

    def register_or_update_template(
        self,
        name: str,
        content: bytes,
        filename: str,
        existing_template_id: Optional[str] = None,
    ) -> TemplateRegistrationResponse:
        file_hash = calculate_pptx_hash(content)

        # 1. Check if exact hash already exists in registry
        existing_match = self.find_by_hash(file_hash)
        if existing_match:
            meta, version = existing_match
            return TemplateRegistrationResponse(
                template=meta,
                active_version=version,
                is_new_version=False,
                is_duplicate_hash=True,
                message=f"Identical template binary detected. Reusing '{meta.name}' version {version.version_number}.",
            )

        now_str = datetime.utcnow().isoformat()

        # 2. If existing_template_id provided, add new version to existing template
        if existing_template_id:
            meta = self.get_template(existing_template_id)
            if not meta:
                raise HTTPException(status_code=404, detail=f"Template ID '{existing_template_id}' not found.")
            
            template_id = meta.template_id
            tpl_dir = self._get_template_dir(template_id)
            new_v_number = meta.current_version + 1

            # Perform inspection ONCE for new binary
            inspection = inspect_powerpoint_template(content, filename)
            inspection.template_id = template_id

            # Auto-suggest mapping for new version
            suggested = auto_suggest_mapping(inspection)
            readiness = calculate_template_readiness(inspection, suggested)

            # Save master PPTX binary for version
            version_pptx_filename = f"master_v{new_v_number}.pptx"
            with open(tpl_dir / version_pptx_filename, "wb") as f:
                f.write(content)

            # Save inspection metadata & mapping
            with open(tpl_dir / f"inspection_v{new_v_number}.json", "w", encoding="utf-8") as f:
                json.dump(inspection.dict(), f, indent=2)

            with open(tpl_dir / f"mapping_v{new_v_number}.json", "w", encoding="utf-8") as f:
                json.dump(suggested.dict(), f, indent=2)

            new_version = TemplateVersion(
                version_number=new_v_number,
                file_hash=file_hash,
                filename=filename,
                pptx_rel_path=version_pptx_filename,
                inspection_status=InspectionStatus.SUCCESS if inspection.valid else InspectionStatus.FAILED,
                mapping_status=readiness.mapping_status,
                generation_readiness=readiness.generation_readiness,
                mapping_config=suggested,
                inspection_data=inspection,
                created_at=now_str,
            )

            meta.versions.append(new_version)
            meta.current_version = new_v_number
            meta.aspect_ratio = inspection.aspect_ratio
            meta.updated_at = now_str
            meta.generation_readiness = readiness.generation_readiness
            meta.mapping_status = readiness.mapping_status

            self.save_template_metadata(meta)

            return TemplateRegistrationResponse(
                template=meta,
                active_version=new_version,
                is_new_version=True,
                is_duplicate_hash=False,
                message=f"Created Version {new_v_number} for template '{meta.name}'.",
            )

        # 3. Create brand new Template
        template_id = uuid.uuid4().hex
        tpl_dir = self._get_template_dir(template_id)
        tpl_dir.mkdir(parents=True, exist_ok=True)

        inspection = inspect_powerpoint_template(content, filename)
        inspection.template_id = template_id

        suggested = auto_suggest_mapping(inspection)
        readiness = calculate_template_readiness(inspection, suggested)

        version_pptx_filename = "master_v1.pptx"
        with open(tpl_dir / version_pptx_filename, "wb") as f:
            f.write(content)

        with open(tpl_dir / "inspection_v1.json", "w", encoding="utf-8") as f:
            json.dump(inspection.dict(), f, indent=2)

        with open(tpl_dir / "mapping_v1.json", "w", encoding="utf-8") as f:
            json.dump(suggested.dict(), f, indent=2)

        v1 = TemplateVersion(
            version_number=1,
            file_hash=file_hash,
            filename=filename,
            pptx_rel_path=version_pptx_filename,
            inspection_status=InspectionStatus.SUCCESS if inspection.valid else InspectionStatus.FAILED,
            mapping_status=readiness.mapping_status,
            generation_readiness=readiness.generation_readiness,
            mapping_config=suggested,
            inspection_data=inspection,
            created_at=now_str,
        )

        meta = TemplateMetadata(
            template_id=template_id,
            name=name,
            current_version=1,
            file_hash=file_hash,
            inspection_status=InspectionStatus.SUCCESS if inspection.valid else InspectionStatus.FAILED,
            mapping_status=readiness.mapping_status,
            generation_readiness=readiness.generation_readiness,
            aspect_ratio=inspection.aspect_ratio,
            versions=[v1],
            is_archived=False,
            created_at=now_str,
            updated_at=now_str,
        )

        self.save_template_metadata(meta)

        return TemplateRegistrationResponse(
            template=meta,
            active_version=v1,
            is_new_version=True,
            is_duplicate_hash=False,
            message=f"Template '{name}' (v1) registered successfully.",
        )

    def update_template_mapping(
        self,
        template_id: str,
        mapping: FieldMappingConfig,
        version_number: Optional[int] = None,
    ) -> TemplateMetadata:
        meta = self.get_template(template_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")

        target_v_num = version_number or meta.current_version
        version_obj = next((v for v in meta.versions if v.version_number == target_v_num), None)
        if not version_obj:
            raise HTTPException(status_code=404, detail=f"Version {target_v_num} not found for template '{template_id}'.")

        tpl_dir = self._get_template_dir(template_id)
        
        # Load inspection data if needed
        inspection = version_obj.inspection_data
        if not inspection:
            insp_file = tpl_dir / f"inspection_v{target_v_num}.json"
            if insp_file.exists():
                with open(insp_file, "r", encoding="utf-8") as f:
                    inspection = TemplateInspectionResponse(**json.load(f))
            else:
                # Re-inspect if missing (failsafe)
                pptx_path = tpl_dir / version_obj.pptx_rel_path
                with open(pptx_path, "rb") as f:
                    inspection = inspect_powerpoint_template(f.read(), version_obj.filename)

        val_res = validate_mapping_config(mapping, inspection)
        readiness = calculate_template_readiness(inspection, mapping)

        version_obj.mapping_config = mapping
        version_obj.mapping_status = readiness.mapping_status
        version_obj.generation_readiness = readiness.generation_readiness

        # Save mapping to file
        with open(tpl_dir / f"mapping_v{target_v_num}.json", "w", encoding="utf-8") as f:
            json.dump(mapping.dict(), f, indent=2)

        if target_v_num == meta.current_version:
            meta.mapping_status = readiness.mapping_status
            meta.generation_readiness = readiness.generation_readiness

        self.save_template_metadata(meta)
        return meta

    def archive_template(self, template_id: str) -> TemplateMetadata:
        meta = self.get_template(template_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")

        meta.is_archived = True
        self.save_template_metadata(meta)
        return meta

    def get_template_version_pptx(self, template_id: str, version_number: Optional[int] = None) -> Tuple[bytes, TemplateVersion]:
        meta = self.get_template(template_id)
        if not meta:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")

        target_v_num = version_number or meta.current_version
        version_obj = next((v for v in meta.versions if v.version_number == target_v_num), None)
        if not version_obj:
            raise HTTPException(status_code=404, detail=f"Version {target_v_num} not found for template '{template_id}'.")

        tpl_dir = self._get_template_dir(template_id)
        pptx_path = (tpl_dir / version_obj.pptx_rel_path).resolve()
        
        if not str(pptx_path).startswith(str(self.registry_dir.resolve())):
            raise HTTPException(status_code=400, detail="Access denied: invalid PPTX path.")
        
        if not pptx_path.exists():
            raise HTTPException(status_code=404, detail=f"Master PPTX file for version {target_v_num} missing.")

        with open(pptx_path, "rb") as f:
            content = f.read()

        return content, version_obj


template_registry = TemplateRegistryService()
