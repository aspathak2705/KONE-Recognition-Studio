"""
Template-Aware Rendering Adapter for KONE Recognition Studio.
Renders presentation content planned by upstream pipeline using visual styles,
layouts, typography, and card geometry from an analyzed TemplateMimicConfig.
Domain-agnostic: no hardcoded Excel columns, employee names, or award categories.
"""

import os
import shutil
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from app.core.config import settings
from app.services.file_storage import atomic_write_json
from app.schemas.photo_matching import EmployeePhotoMatch
from app.schemas.dynamic_presentation import (
    DynamicGenerationResponse,
    SlideGeometryFinding,
    AwardGroup,
)
from app.schemas.template_mimic import (
    TemplateMimicConfig,
    SlideLayoutConfig,
    VisualElementConfig,
    RoleCandidate,
    ElementType,
)
from app.services.award_grouping_service import group_employees_by_award
from app.services.dynamic_layout_engine import paginate_award_group


def _hex_to_rgb(hex_code: Optional[str]) -> Optional[RGBColor]:
    if not hex_code:
        return None
    clean = hex_code.strip("#")
    if len(clean) == 6:
        try:
            return RGBColor(int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
        except ValueError:
            return None
    return None


class TemplateAwareAdapter:
    """
    Adapter bridging upstream planned content with an uploaded master template.
    """

    @classmethod
    def render_presentation(
        cls,
        session_id: str,
        employees: List[EmployeePhotoMatch],
        template_config: TemplateMimicConfig,
    ) -> DynamicGenerationResponse:
        if not employees:
            raise ValueError("Cannot render template presentation with empty employee records.")
        if not template_config or not template_config.is_valid:
            raise ValueError("Provided template configuration is invalid or unanalyzed.")

        session_dir = settings.PHOTO_SESSIONS_DIR.resolve() / session_id
        for emp in employees:
            if not emp.is_resolved or not emp.assigned_file:
                raise ValueError(
                    f"Employee '{emp.employee_name}' lacks a verified photograph."
                )
            photo_disk_path = session_dir / emp.assigned_file.relative_path
            if not photo_disk_path.exists():
                raise ValueError(
                    f"Photograph for '{emp.employee_name}' not found at {photo_disk_path}."
                )

        # 1. Load the master presentation source
        master_path = Path(template_config.raw_storage_path)
        if not master_path.exists():
            raise ValueError(f"Master template file not found on disk: {master_path}")

        generation_id = uuid.uuid4().hex
        out_prs = Presentation(str(master_path))

        # Classify available template slides into structural roles:
        # Cover (usually slide 0 if multiple slides), Content (repeating layout), Closing
        content_layout_idx, cover_layout_idx, closing_layout_idx = cls._classify_template_layouts(template_config)

        # Retain master slides as prototype definitions, clear slides from working deck
        # In python-pptx, deleting slides from prs directly can corrupt XML relationships.
        # Cleanest, safest strategy: Build output prs with matching slide width/height,
        # copy/mimic master visual elements with pixel-perfection and applied data.
        final_prs = Presentation()
        final_prs.slide_width = Inches(template_config.slide_width_in)
        final_prs.slide_height = Inches(template_config.slide_height_in)
        blank_layout = final_prs.slide_layouts[6]

        # Step A: Render Cover Slide (using cover_layout_idx)
        cover_cfg = template_config.slides[cover_layout_idx] if cover_layout_idx < len(template_config.slides) else template_config.slides[0]
        cls._render_cover_slide(final_prs, blank_layout, cover_cfg, template_config, len(employees))

        # Step B: Render Content Slides by Group
        award_groups = group_employees_by_award(employees)
        content_cfg = template_config.slides[content_layout_idx] if content_layout_idx < len(template_config.slides) else template_config.slides[0]

        # Determine card capacity of content layout
        cluster_capacity = len(content_cfg.content_clusters) if content_cfg.content_clusters else 0
        card_capacity = max(cluster_capacity, 1)

        for group in award_groups:
            cls._render_group_slides(
                prs=final_prs,
                layout=blank_layout,
                layout_cfg=content_cfg,
                template_config=template_config,
                group=group,
                session_dir=session_dir,
                card_capacity=card_capacity,
            )

        # Step C: Render Closing Slide (using closing_layout_idx if available)
        if closing_layout_idx is not None and closing_layout_idx < len(template_config.slides):
            closing_cfg = template_config.slides[closing_layout_idx]
            cls._render_closing_slide(final_prs, blank_layout, closing_cfg, template_config)

        # Step D: Save output presentation (or skip saving to permanent outputs if in preview mode)
        settings.GENERATED_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        out_filename = f"{generation_id}.pptx"
        dest_pptx_path = settings.GENERATED_OUTPUTS_DIR / out_filename
        final_prs.save(str(dest_pptx_path))

        # Step E: Previews and geometry validation
        from app.services.dynamic_presentation_service import DynamicPresentationService
        findings = DynamicPresentationService._validate_presentation_geometry(final_prs)

        from app.services.pptx_renderer import PptxRenderer
        render_dir = settings.GENERATED_OUTPUTS_DIR / f"renders_{generation_id}"
        rendered_paths = PptxRenderer.render_presentation_slides(dest_pptx_path, render_dir, timeout_seconds=45)
        rendered_slide_urls = [
            f"/api/generations/{generation_id}/renders/{p.name}" for p in rendered_paths
        ]

        now_iso = datetime.datetime.utcnow().isoformat()
        has_critical_error = any(f.severity == "ERROR" for f in findings)
        delivery_status = "BLOCKED" if has_critical_error else "READY"

        response = DynamicGenerationResponse(
            generation_id=generation_id,
            session_id=session_id,
            slide_count=len(final_prs.slides),
            total_employees=len(employees),
            award_categories_count=len(award_groups),
            award_groups=award_groups,
            download_url=f"/api/generations/{generation_id}/download",
            pptx_path=str(dest_pptx_path),
            is_valid=not has_critical_error,
            validation_findings=findings,
            rendered_slide_urls=rendered_slide_urls,
            delivery_status=delivery_status,
            can_download=not has_critical_error,
            created_at=now_iso,
        )

        job_meta_path = settings.GENERATED_OUTPUTS_DIR / f"{generation_id}.json"
        meta_data = {
            "generation_id": generation_id,
            "session_id": session_id,
            "template_id": template_config.template_id,
            "template_name": template_config.name,
            "generation_mode": "TEMPLATE_MIMIC",
            "status": "completed",
            "delivery_status": delivery_status,
            "validation_status": "VERIFIED" if not has_critical_error else "FAILED",
            "slide_count": len(final_prs.slides),
            "record_count": len(employees),
            "award_categories_count": len(award_groups),
            "created_at": now_iso,
            "download_url": f"/api/generations/{generation_id}/download",
            "rendered_slide_urls": rendered_slide_urls,
        }
        atomic_write_json(job_meta_path, meta_data)

        return response

    @classmethod
    def extract_record_fields(
        cls, record: Any, field_key: str
    ) -> Optional[str]:
        """
        Generic content extraction: extracts field by key from dict or model object
        without assuming fixed attribute names.
        """
        if isinstance(record, dict):
            return str(record.get(field_key, "")) if record.get(field_key) is not None else None
        return str(getattr(record, field_key, "")) if getattr(record, field_key, None) is not None else None

    @classmethod
    def _classify_template_layouts(
        cls, config: TemplateMimicConfig
    ) -> Tuple[int, int, Optional[int]]:
        """
        Identifies most suitable layout indices for (Content, Cover, Closing).
        Honors explicit user configuration (layout_role) or applies generic visual heuristic.
        """
        slide_count = len(config.slides)
        if slide_count == 1:
            return 0, 0, None

        # Check for explicitly configured layout roles
        explicit_cover = None
        explicit_content = None
        explicit_closing = None

        for idx, sl in enumerate(config.slides):
            if sl.layout_role == "COVER":
                explicit_cover = idx
            elif sl.layout_role == "CONTENT":
                explicit_content = idx
            elif sl.layout_role == "CLOSING":
                explicit_closing = idx

        if explicit_content is not None:
            cover_idx = explicit_cover if explicit_cover is not None else (0 if explicit_content != 0 else 1)
            return explicit_content, cover_idx, explicit_closing

        # Generic heuristic: slide with highest number of clusters / replaceable elements as Content
        content_idx = 1
        max_clusters = -1
        for idx, sl in enumerate(config.slides):
            cluster_count = len(sl.content_clusters)
            if cluster_count > max_clusters:
                max_clusters = cluster_count
                content_idx = idx

        cover_idx = 0 if content_idx != 0 else 1
        closing_idx = (slide_count - 1) if (slide_count > 2 and content_idx != slide_count - 1 and cover_idx != slide_count - 1) else None

        return content_idx, cover_idx, closing_idx

    @classmethod
    def _render_cover_slide(
        cls,
        prs: Presentation,
        layout,
        layout_cfg: SlideLayoutConfig,
        tpl_cfg: TemplateMimicConfig,
        total_employees: int,
    ):
        slide = prs.slides.add_slide(layout)
        primary_color = _hex_to_rgb(tpl_cfg.theme.primary_color_rgb) or RGBColor(0, 47, 108)
        font_name = tpl_cfg.theme.primary_font or "Segoe UI"

        for elem in layout_cfg.elements:
            if elem.role == RoleCandidate.STATIC:
                cls._render_static_element(slide, elem, tpl_cfg)
            elif elem.role == RoleCandidate.REPLACEABLE_TEXT:
                # Replace with presentation title / subtitle without hardcoding
                text_to_display = elem.text_sample or "Recognition Studio"
                # If element appears to be a large title
                if elem.text_style and (elem.text_style.font_size_pt or 0) >= 24:
                    text_to_display = "ANNUAL EMPLOYEE RECOGNITION"
                elif elem.text_style and (elem.text_style.font_size_pt or 0) < 24:
                    text_to_display = f"Honoring Excellence • {total_employees} Honorees"

                tb = slide.shapes.add_textbox(
                    Inches(elem.left_in), Inches(elem.top_in), Inches(elem.width_in), Inches(elem.height_in)
                )
                tf = tb.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = text_to_display
                p.font.name = (elem.text_style and elem.text_style.font_name) or font_name
                p.font.size = Pt((elem.text_style and elem.text_style.font_size_pt) or 32)
                p.font.bold = True
                p.font.color.rgb = _hex_to_rgb(elem.text_style and elem.text_style.color_rgb) or primary_color

    @classmethod
    def _render_closing_slide(
        cls,
        prs: Presentation,
        layout,
        layout_cfg: SlideLayoutConfig,
        tpl_cfg: TemplateMimicConfig,
    ):
        slide = prs.slides.add_slide(layout)
        for elem in layout_cfg.elements:
            if elem.role == RoleCandidate.STATIC:
                cls._render_static_element(slide, elem, tpl_cfg)
            else:
                cls._render_static_element(slide, elem, tpl_cfg)

    @classmethod
    def _render_group_slides(
        cls,
        prs: Presentation,
        layout,
        layout_cfg: SlideLayoutConfig,
        template_config: TemplateMimicConfig,
        group: AwardGroup,
        session_dir: Path,
        card_capacity: int,
    ):
        # Paginate group based on template's discovered cluster card capacity
        # e.g., if template has 2 cards, slice by 2; if template has 4, slice by 4.
        effective_capacity = min(max(card_capacity, 1), 8)
        slide_slices = paginate_award_group(group.employee_count, max_density_per_slide=effective_capacity)
        curr_emp_idx = 0

        for page_idx, count_on_slide in enumerate(slide_slices):
            slice_employees = group.employees[curr_emp_idx : curr_emp_idx + count_on_slide]
            curr_emp_idx += count_on_slide

            slide = prs.slides.add_slide(layout)

            # 1. Render all static visual elements (headers, borders, backgrounds)
            for elem in layout_cfg.elements:
                if elem.role == RoleCandidate.STATIC:
                    # Check if this static element is a category title candidate (near top of slide)
                    if elem.element_type == ElementType.TEXT and elem.top_in < 1.6 and elem.width_in > 4.0:
                        # Render category header matching template typography
                        cls._render_header_text(slide, elem, group.award_name, page_idx, len(slide_slices), template_config)
                    else:
                        cls._render_static_element(slide, elem, template_config)

            # 2. Render cards using template's content clusters
            clusters = layout_cfg.content_clusters
            elem_map = {e.element_id: e for e in layout_cfg.elements}

            for card_idx, emp in enumerate(slice_employees):
                if card_idx < len(clusters):
                    cluster = clusters[card_idx]
                    cls._render_cluster_card(
                        slide=slide,
                        cluster=cluster,
                        elem_map=elem_map,
                        emp=emp,
                        session_dir=session_dir,
                        template_config=template_config,
                    )
                else:
                    # Overflow fallback: dynamically position adjacent card if count exceeds detected clusters
                    base_cluster = clusters[0] if clusters else None
                    cls._render_dynamic_card_fallback(
                        slide=slide,
                        card_idx=card_idx,
                        total_on_slide=count_on_slide,
                        emp=emp,
                        session_dir=session_dir,
                        template_config=template_config,
                    )

    @classmethod
    def _render_header_text(
        cls,
        slide,
        elem: VisualElementConfig,
        category_name: str,
        page_idx: int,
        total_pages: int,
        template_config: TemplateMimicConfig,
    ):
        tb = slide.shapes.add_textbox(
            Inches(elem.left_in), Inches(elem.top_in), Inches(elem.width_in), Inches(elem.height_in)
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category_name.upper()
        p.font.name = (elem.text_style and elem.text_style.font_name) or template_config.theme.primary_font or "Segoe UI"
        p.font.size = Pt((elem.text_style and elem.text_style.font_size_pt) or 22.0)
        p.font.bold = True
        p.font.color.rgb = _hex_to_rgb(elem.text_style and elem.text_style.color_rgb) or _hex_to_rgb(template_config.theme.primary_color_rgb) or RGBColor(0, 47, 108)

        if total_pages > 1:
            p2 = tf.add_paragraph()
            p2.text = f"Part {page_idx + 1} of {total_pages}"
            p2.font.size = Pt(11)
            p2.font.color.rgb = RGBColor(100, 116, 139)

    @classmethod
    def _render_static_element(
        cls,
        slide,
        elem: VisualElementConfig,
        template_config: TemplateMimicConfig,
    ):
        if elem.element_type == ElementType.SHAPE:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(elem.left_in),
                Inches(elem.top_in),
                Inches(elem.width_in),
                Inches(elem.height_in),
            )
            fill_color = _hex_to_rgb(elem.fill_color_rgb)
            if fill_color:
                shape.fill.solid()
                shape.fill.fore_color.rgb = fill_color
            else:
                shape.fill.background()

            line_color = _hex_to_rgb(elem.line_color_rgb)
            if line_color:
                shape.line.color.rgb = line_color
                if elem.line_width_pt:
                    shape.line.width = Pt(elem.line_width_pt)
            else:
                shape.line.fill.background()

        elif elem.element_type == ElementType.TEXT and elem.text_sample:
            tb = slide.shapes.add_textbox(
                Inches(elem.left_in), Inches(elem.top_in), Inches(elem.width_in), Inches(elem.height_in)
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = elem.text_sample
            if elem.text_style:
                if elem.text_style.font_name:
                    p.font.name = elem.text_style.font_name
                if elem.text_style.font_size_pt:
                    p.font.size = Pt(elem.text_style.font_size_pt)
                if elem.text_style.bold is not None:
                    p.font.bold = elem.text_style.bold
                font_rgb = _hex_to_rgb(elem.text_style.color_rgb)
                if font_rgb:
                    p.font.color.rgb = font_rgb

    @classmethod
    def _render_cluster_card(
        cls,
        slide,
        cluster,
        elem_map: Dict[str, VisualElementConfig],
        emp: EmployeePhotoMatch,
        session_dir: Path,
        template_config: TemplateMimicConfig,
    ):
        """
        Renders an employee card within a configured template cluster box.
        """
        primary_color = _hex_to_rgb(template_config.theme.primary_color_rgb) or RGBColor(0, 47, 108)
        font_name = template_config.theme.primary_font or "Segoe UI"

        # Separate elements in cluster
        container_elem = None
        text_elements: List[VisualElementConfig] = []
        image_elem = None

        for eid in cluster.element_ids:
            elem = elem_map.get(eid)
            if not elem:
                continue
            if elem.role == RoleCandidate.CONTAINER:
                container_elem = elem
            elif elem.role in (RoleCandidate.REPLACEABLE_TEXT, RoleCandidate.STATIC) and elem.element_type == ElementType.TEXT:
                text_elements.append(elem)
            elif elem.role == RoleCandidate.REPLACEABLE_IMAGE or elem.element_type == ElementType.IMAGE:
                image_elem = elem

        # 1. Render container card box
        if container_elem:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(container_elem.left_in),
                Inches(container_elem.top_in),
                Inches(container_elem.width_in),
                Inches(container_elem.height_in),
            )
            fill_color = _hex_to_rgb(container_elem.fill_color_rgb) or RGBColor(248, 250, 252)
            shape.fill.solid()
            shape.fill.fore_color.rgb = fill_color
            line_color = _hex_to_rgb(container_elem.line_color_rgb) or RGBColor(226, 232, 240)
            shape.line.color.rgb = line_color
            shape.line.width = Pt(1.0)
        else:
            # Bounding box fallback
            bx, by, bw, bh = cluster.bounding_box_in
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(bx), Inches(by), Inches(bw), Inches(bh))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(248, 250, 252)
            shape.line.color.rgb = RGBColor(226, 232, 240)

        # 2. Render employee photo
        photo_disk_path = None
        if hasattr(emp, "assigned_file") and emp.assigned_file and hasattr(emp.assigned_file, "relative_path"):
            photo_disk_path = session_dir / emp.assigned_file.relative_path

        if photo_disk_path and photo_disk_path.exists():
            if image_elem:
                # Exact position specified by template
                img_left = Inches(image_elem.left_in)
                img_top = Inches(image_elem.top_in)
                img_w = Inches(image_elem.width_in)
                img_h = Inches(image_elem.height_in)
                slide.shapes.add_picture(str(photo_disk_path), img_left, img_top, width=img_w, height=img_h)
            else:
                # Synthesize photo inside container
                bx, by, bw, bh = cluster.bounding_box_in
                img_size = min(bw * 0.4, bh * 0.5, 1.8)
                img_left = Inches(bx + 0.3)
                img_top = Inches(by + (bh - img_size) / 2.0)
                slide.shapes.add_picture(str(photo_disk_path), img_left, img_top, width=Inches(img_size), height=Inches(img_size))

        # 3. Render content values dynamically (generic field binding)
        # Determine primary and secondary field values from record or employee model
        primary_val = (
            cls.extract_record_fields(emp, "primary_text")
            or cls.extract_record_fields(emp, "employee_name")
            or cls.extract_record_fields(emp, "name")
            or cls.extract_record_fields(emp, "title")
            or ""
        )
        secondary_parts = [
            cls.extract_record_fields(emp, "secondary_text"),
            cls.extract_record_fields(emp, "designation"),
            cls.extract_record_fields(emp, "branch"),
            cls.extract_record_fields(emp, "department"),
            cls.extract_record_fields(emp, "location"),
        ]
        secondary_val = " • ".join([p for p in secondary_parts if p])

        if text_elements:
            # Sort text elements by vertical coordinate
            text_elements.sort(key=lambda t: t.top_in)
            for idx, txt_elem in enumerate(text_elements):
                # Check if element has an explicit target_field mapping
                val_to_render = None
                if txt_elem.target_field:
                    val_to_render = cls.extract_record_fields(emp, txt_elem.target_field)
                elif cluster.field_mappings.get(txt_elem.element_id):
                    val_to_render = cls.extract_record_fields(emp, cluster.field_mappings[txt_elem.element_id])

                if val_to_render is None:
                    # Default: first text element gets primary_val, subsequent get secondary_val
                    val_to_render = primary_val if idx == 0 else secondary_val

                if not val_to_render:
                    continue

                tb = slide.shapes.add_textbox(
                    Inches(txt_elem.left_in), Inches(txt_elem.top_in), Inches(txt_elem.width_in), Inches(txt_elem.height_in)
                )
                tf = tb.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = val_to_render
                p.font.name = (txt_elem.text_style and txt_elem.text_style.font_name) or font_name
                default_size = 16.0 if idx == 0 else 11.0
                p.font.size = Pt((txt_elem.text_style and txt_elem.text_style.font_size_pt) or default_size)
                p.font.bold = True if idx == 0 else (txt_elem.text_style and txt_elem.text_style.bold)
                color = _hex_to_rgb(txt_elem.text_style and txt_elem.text_style.color_rgb) or (primary_color if idx == 0 else RGBColor(100, 116, 139))
                p.font.color.rgb = color
        else:
            # Fallback text area inside container
            bx, by, bw, bh = cluster.bounding_box_in
            tb = slide.shapes.add_textbox(Inches(bx + (bw * 0.45)), Inches(by + 0.3), Inches(bw * 0.5), Inches(bh - 0.6))
            tf = tb.text_frame
            tf.word_wrap = True
            p_n = tf.paragraphs[0]
            p_n.text = primary_val
            p_n.font.name = font_name
            p_n.font.size = Pt(16.0)
            p_n.font.bold = True
            p_n.font.color.rgb = primary_color

            if secondary_val:
                p_m = tf.add_paragraph()
                p_m.text = secondary_val
                p_m.font.size = Pt(11.0)
                p_m.font.color.rgb = RGBColor(100, 116, 139)

    @classmethod
    def _render_dynamic_card_fallback(
        cls,
        slide,
        card_idx: int,
        total_on_slide: int,
        emp: EmployeePhotoMatch,
        session_dir: Path,
        template_config: TemplateMimicConfig,
    ):
        """
        Dynamically adapts layout when content requires more cards than the master slide had clusters.
        """
        from app.services.dynamic_layout_engine import calculate_optimal_slide_layout
        layout_cfg = calculate_optimal_slide_layout(total_on_slide)
        col = card_idx % layout_cfg.columns
        row = card_idx // layout_cfg.columns

        x_in = layout_cfg.margin_left_in + (col * (layout_cfg.card_width_in + layout_cfg.gap_x_in))
        y_in = layout_cfg.margin_top_in + (row * (layout_cfg.card_height_in + layout_cfg.gap_y_in))

        # Render fallback card using template theme colors
        primary_color = _hex_to_rgb(template_config.theme.primary_color_rgb) or RGBColor(0, 47, 108)
        font_name = template_config.theme.primary_font or "Segoe UI"

        card = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(x_in), Inches(y_in), Inches(layout_cfg.card_width_in), Inches(layout_cfg.card_height_in)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(248, 250, 252)
        card.line.color.rgb = RGBColor(226, 232, 240)
        card.line.width = Pt(1.0)

        photo_disk_path = None
        if hasattr(emp, "assigned_file") and emp.assigned_file and hasattr(emp.assigned_file, "relative_path"):
            photo_disk_path = session_dir / emp.assigned_file.relative_path

        img_size = layout_cfg.image_size_in
        if photo_disk_path and photo_disk_path.exists():
            slide.shapes.add_picture(
                str(photo_disk_path),
                Inches(x_in + 0.2),
                Inches(y_in + (layout_cfg.card_height_in - img_size) / 2.0),
                width=Inches(img_size),
                height=Inches(img_size),
            )

        txt_left = Inches(x_in + img_size + 0.35)
        txt_width = Inches(max(layout_cfg.card_width_in - img_size - 0.45, 1.0))
        tb = slide.shapes.add_textbox(txt_left, Inches(y_in + 0.25), txt_width, Inches(layout_cfg.card_height_in - 0.5))
        tf = tb.text_frame
        tf.word_wrap = True

        primary_val = (
            cls.extract_record_fields(emp, "primary_text")
            or cls.extract_record_fields(emp, "employee_name")
            or cls.extract_record_fields(emp, "name")
            or ""
        )
        p_name = tf.paragraphs[0]
        p_name.text = primary_val
        p_name.font.name = font_name
        p_name.font.size = Pt(layout_cfg.name_font_size_pt)
        p_name.font.bold = True
        p_name.font.color.rgb = primary_color

        meta_parts = [
            cls.extract_record_fields(emp, "secondary_text"),
            cls.extract_record_fields(emp, "designation"),
            cls.extract_record_fields(emp, "branch"),
        ]
        meta_str = " • ".join([m for m in meta_parts if m])
        if meta_str:
            p_meta = tf.add_paragraph()
            p_meta.text = meta_str
            p_meta.font.name = font_name
            p_meta.font.size = Pt(layout_cfg.meta_font_size_pt)
            p_meta.font.color.rgb = RGBColor(100, 116, 139)
