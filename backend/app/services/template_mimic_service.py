import io
import os
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.dml.color import RGBColor

from app.core.config import settings
from app.services.file_storage import atomic_write_json, read_json_safely
from app.schemas.template_mimic import (
    ElementType,
    RoleCandidate,
    ElementCapability,
    TextStyleInfo,
    VisualElementConfig,
    ContentCluster,
    SlideLayoutConfig,
    TemplateThemePalette,
    TemplateMimicConfig,
)

EMU_PER_INCH = 914400.0


def _emu_to_inch(emu: Optional[int]) -> float:
    if emu is None:
        return 0.0
    return round(float(emu) / EMU_PER_INCH, 3)


def _rgb_to_hex(rgb: Optional[RGBColor]) -> Optional[str]:
    if not rgb:
        return None
    try:
        return f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    except Exception:
        return None


class TemplateMimicService:
    @classmethod
    def get_template_storage_dir(cls, template_id: str) -> Path:
        p = settings.STORAGE_DIR / "templates" / template_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def analyze_and_register_template(cls, filename: str, content: bytes) -> TemplateMimicConfig:
        """
        Validates, analyzes, and serializes a generic PowerPoint template configuration.
        Does NOT hardcode any employee names, award categories, or domain assumptions.
        """
        if not content:
            raise ValueError("Template content is empty (0 bytes).")

        # Step 1: Open PPTX with python-pptx
        try:
            prs = Presentation(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Failed to open presentation: File is corrupted or not a valid PPTX. ({str(e)})")

        template_id = uuid.uuid4().hex
        template_dir = cls.get_template_storage_dir(template_id)
        raw_pptx_path = template_dir / f"master_{template_id}.pptx"

        # Save raw template binary
        with open(raw_pptx_path, "wb") as f:
            f.write(content)

        slide_width_in = _emu_to_inch(prs.slide_width)
        slide_height_in = _emu_to_inch(prs.slide_height)

        # Determine Aspect Ratio
        ratio_val = slide_width_in / slide_height_in if slide_height_in > 0 else 1.777
        if abs(ratio_val - 16 / 9) < 0.1:
            aspect_ratio = "16:9"
        elif abs(ratio_val - 4 / 3) < 0.1:
            aspect_ratio = "4:3"
        elif abs(ratio_val - 16 / 10) < 0.1:
            aspect_ratio = "16:10"
        else:
            aspect_ratio = f"{round(slide_width_in, 1)}:{round(slide_height_in, 1)}"

        # Analysis State
        all_colors: Counter = Counter()
        all_fonts: Counter = Counter()
        warnings: List[str] = []
        slides_config: List[SlideLayoutConfig] = []

        # Step 2: Analyze Each Slide
        for slide_idx, slide in enumerate(prs.slides):
            elements: List[VisualElementConfig] = []
            shape_idx = 0

            for shape in slide.shapes:
                elem = cls._analyze_shape(shape, slide_idx, shape_idx)
                if elem:
                    elements.append(elem)
                    shape_idx += 1
                    if elem.text_style and elem.text_style.color_rgb:
                        all_colors[elem.text_style.color_rgb] += 1
                    if elem.text_style and elem.text_style.font_name:
                        all_fonts[elem.text_style.font_name] += 1
                    if elem.fill_color_rgb:
                        all_colors[elem.fill_color_rgb] += 1

            # Detect content clusters (e.g. card regions) via geometric clustering
            clusters = cls._detect_spatial_clusters(elements, slide_width_in, slide_height_in)

            # Heuristics: refine candidate roles based on clustering and geometry
            cls._refine_candidate_roles(elements, clusters, slide_idx, len(prs.slides))

            slide_cfg = SlideLayoutConfig(
                slide_index=slide_idx,
                slide_width_in=slide_width_in,
                slide_height_in=slide_height_in,
                elements=elements,
                content_clusters=clusters,
                is_suitable_for_content=len(clusters) > 0 or any(e.role in (RoleCandidate.REPLACEABLE_TEXT, RoleCandidate.REPLACEABLE_IMAGE) for e in elements),
                layout_signature=f"s{slide_idx}_c{len(clusters)}_e{len(elements)}",
            )
            slides_config.append(slide_cfg)

        # Step 3: Extract Theme Palette
        detected_colors = [c[0] for c in all_colors.most_common(10)]
        detected_fonts = [f[0] for f in all_fonts.most_common(5)]

        theme = TemplateThemePalette(
            primary_color_rgb=detected_colors[0] if detected_colors else None,
            secondary_color_rgb=detected_colors[1] if len(detected_colors) > 1 else None,
            accent_color_rgb=detected_colors[2] if len(detected_colors) > 2 else None,
            primary_font=detected_fonts[0] if detected_fonts else "Segoe UI",
            secondary_font=detected_fonts[1] if len(detected_fonts) > 1 else None,
            detected_colors=detected_colors,
            detected_fonts=detected_fonts,
        )

        # Step 4: Render Previews via Isolated COM Renderer if Available
        preview_urls = []
        try:
            from app.services.pptx_renderer import PptxRenderer
            renders_dir = template_dir / "renders"
            renders_dir.mkdir(parents=True, exist_ok=True)
            rendered_paths = PptxRenderer.render_presentation_slides(raw_pptx_path, renders_dir, timeout_seconds=30)
            preview_urls = [f"/api/templates/mimic/{template_id}/renders/{p.name}" for p in rendered_paths]
        except Exception:
            # Fallback gracefully if COM worker is unavailable or in sandbox
            preview_urls = []

        now_iso = datetime.datetime.utcnow().isoformat()
        stem_name = Path(filename).stem.replace("_", " ").title()

        config = TemplateMimicConfig(
            template_id=template_id,
            filename=filename,
            name=stem_name,
            version=1,
            created_at=now_iso,
            updated_at=now_iso,
            slide_count=len(prs.slides),
            slide_width_in=slide_width_in,
            slide_height_in=slide_height_in,
            aspect_ratio=aspect_ratio,
            theme=theme,
            slides=slides_config,
            is_valid=True,
            validation_warnings=warnings,
            raw_storage_path=str(raw_pptx_path),
            preview_slide_urls=preview_urls,
        )

        # Step 5: Save config atomically
        config_path = template_dir / "config.json"
        atomic_write_json(config_path, config.model_dump())

        return config

    @classmethod
    def _analyze_shape(cls, shape, slide_idx: int, shape_idx: int) -> Optional[VisualElementConfig]:
        left = _emu_to_inch(getattr(shape, "left", 0))
        top = _emu_to_inch(getattr(shape, "top", 0))
        width = _emu_to_inch(getattr(shape, "width", 0))
        height = _emu_to_inch(getattr(shape, "height", 0))

        element_id = f"s{slide_idx}_e{shape_idx}_{shape.shape_id if hasattr(shape, 'shape_id') else uuid.uuid4().hex[:6]}"
        shape_name = shape.name or f"Shape_{shape_idx}"
        shape_type_enum = getattr(shape, "shape_type", None)

        element_type = ElementType.UNKNOWN
        capabilities = [ElementCapability.IMMUTABLE]
        text_sample = None
        text_style = None
        fill_hex = None
        line_hex = None

        # Inspect Shape Fill
        try:
            if hasattr(shape, "fill") and shape.fill and shape.fill.type == 1:  # Solid fill
                fill_hex = _rgb_to_hex(getattr(shape.fill.fore_color, "rgb", None))
        except Exception:
            pass

        # Inspect Shape Line
        try:
            if hasattr(shape, "line") and shape.line:
                line_hex = _rgb_to_hex(getattr(shape.line.color, "rgb", None))
        except Exception:
            pass

        # Check Picture
        if shape_type_enum == MSO_SHAPE_TYPE.PICTURE:
            element_type = ElementType.IMAGE
            capabilities = [ElementCapability.IMAGE_REPLACE, ElementCapability.STYLE_SOURCE]
            # Small heuristic: Is this picture large enough to be an avatar/photo frame or just a tiny icon?
            role = RoleCandidate.REPLACEABLE_IMAGE if (width >= 0.8 and height >= 0.8) else RoleCandidate.STATIC
            return VisualElementConfig(
                element_id=element_id,
                original_shape_id=getattr(shape, "shape_id", None),
                shape_name=shape_name,
                element_type=element_type,
                left_in=left,
                top_in=top,
                width_in=width,
                height_in=height,
                fill_color_rgb=fill_hex,
                line_color_rgb=line_hex,
                role=role,
                capabilities=capabilities,
                confidence_score=0.7 if role == RoleCandidate.REPLACEABLE_IMAGE else 0.4,
            )

        # Check Text Frame (only if shape has text or is a pure text box / placeholder)
        if hasattr(shape, "has_text_frame") and shape.has_text_frame and shape.text_frame:
            text_val = shape.text_frame.text.strip()
            # If shape is a geometry shape without text (e.g. background/card rectangle), treat as SHAPE container
            if text_val or shape_type_enum in (MSO_SHAPE_TYPE.TEXT_BOX, 14):
                element_type = ElementType.TEXT
                text_sample = text_val[:100] if text_val else None

                # Extract font/style of first paragraph/run
                font_name = None
                font_size_pt = None
                font_bold = None
                font_italic = None
                font_color_hex = None
                alignment = None

                for p in shape.text_frame.paragraphs:
                    if p.alignment:
                        alignment = str(p.alignment)
                    # Check paragraph-level font
                    if p.font:
                        font_name = p.font.name or font_name
                        if p.font.size:
                            font_size_pt = round(float(p.font.size.pt), 1)
                        font_bold = p.font.bold or font_bold
                        font_italic = p.font.italic or font_italic
                        try:
                            font_color_hex = _rgb_to_hex(getattr(p.font.color, "rgb", None)) or font_color_hex
                        except Exception:
                            pass
                    for r in p.runs:
                        if r.font:
                            font_name = r.font.name or font_name
                            if r.font.size:
                                font_size_pt = round(float(r.font.size.pt), 1)
                            font_bold = r.font.bold or font_bold
                            font_italic = r.font.italic or font_italic
                            try:
                                font_color_hex = _rgb_to_hex(getattr(r.font.color, "rgb", None)) or font_color_hex
                            except Exception:
                                pass
                        if font_name or font_size_pt:
                            break
                    if font_name or font_size_pt:
                        break

                text_style = TextStyleInfo(
                    font_name=font_name,
                    font_size_pt=font_size_pt,
                    bold=font_bold,
                    italic=font_italic,
                    color_rgb=font_color_hex,
                    alignment=alignment,
                )

                # Text role heuristic: Is it candidate replaceable text or static title/footer?
                if text_val:
                    role = RoleCandidate.REPLACEABLE_TEXT
                    capabilities = [ElementCapability.TEXT_EDIT, ElementCapability.STYLE_SOURCE]
                    confidence = 0.6
                else:
                    role = RoleCandidate.STATIC
                    confidence = 0.3

                return VisualElementConfig(
                    element_id=element_id,
                    original_shape_id=getattr(shape, "shape_id", None),
                    shape_name=shape_name,
                    element_type=element_type,
                    left_in=left,
                    top_in=top,
                    width_in=width,
                    height_in=height,
                    fill_color_rgb=fill_hex,
                    line_color_rgb=line_hex,
                    text_sample=text_sample,
                    text_style=text_style,
                    role=role,
                    capabilities=capabilities,
                    confidence_score=confidence,
                )

        # Check Shapes / Rectangles / Containers
        element_type = ElementType.SHAPE
        # If wide and tall container covering area
        is_container = width > 1.5 and height > 1.0
        role = RoleCandidate.CONTAINER if is_container else RoleCandidate.STATIC

        return VisualElementConfig(
            element_id=element_id,
            original_shape_id=getattr(shape, "shape_id", None),
            shape_name=shape_name,
            element_type=element_type,
            left_in=left,
            top_in=top,
            width_in=width,
            height_in=height,
            fill_color_rgb=fill_hex,
            line_color_rgb=line_hex,
            role=role,
            capabilities=[ElementCapability.STYLE_SOURCE],
            confidence_score=0.5,
        )

    @classmethod
    def _detect_spatial_clusters(
        cls, elements: List[VisualElementConfig], slide_w: float, slide_h: float
    ) -> List[ContentCluster]:
        """
        Groups visual elements into spatial clusters (e.g. cards) using 2D Euclidean distance.
        """
        # Find potential card containers or clusters of text + images
        clusters: List[ContentCluster] = []
        containers = [e for e in elements if e.role == RoleCandidate.CONTAINER]

        used_ids = set()
        for idx, c in enumerate(containers):
            enclosed_ids = []
            for e in elements:
                if e.element_id == c.element_id:
                    continue
                # Bounding box containment with slight tolerance
                if (
                    e.left_in >= c.left_in - 0.2
                    and e.top_in >= c.top_in - 0.2
                    and (e.left_in + e.width_in) <= (c.left_in + c.width_in + 0.2)
                    and (e.top_in + e.height_in) <= (c.top_in + c.height_in + 0.2)
                ):
                    enclosed_ids.append(e.element_id)
                    used_ids.add(e.element_id)

            if enclosed_ids:
                clusters.append(
                    ContentCluster(
                        cluster_id=f"cluster_{idx}",
                        bounding_box_in=[c.left_in, c.top_in, c.width_in, c.height_in],
                        element_ids=[c.element_id] + enclosed_ids,
                        suggested_role="RECORD_CARD",
                        is_repeating_unit=len(containers) > 1,
                    )
                )

        return clusters

    @classmethod
    def _refine_candidate_roles(
        cls,
        elements: List[VisualElementConfig],
        clusters: List[ContentCluster],
        slide_idx: int,
        total_slides: int,
    ):
        """
        Applies non-domain visual heuristics:
        - Top banner text (small height, top < 1.2 in, wide) -> STATIC Header
        - Bottom banner text (top > slide_height - 0.8 in) -> STATIC Footer
        - Elements inside repeating content clusters -> REPLACEABLE
        """
        cluster_elem_ids = set()
        for c in clusters:
            for eid in c.element_ids:
                cluster_elem_ids.add(eid)

        for e in elements:
            if e.element_id in cluster_elem_ids:
                if e.element_type == ElementType.TEXT:
                    e.role = RoleCandidate.REPLACEABLE_TEXT
                    e.confidence_score = 0.85
                elif e.element_type == ElementType.IMAGE:
                    e.role = RoleCandidate.REPLACEABLE_IMAGE
                    e.confidence_score = 0.85
            else:
                # Top header heuristic
                if e.top_in < 1.2 and e.width_in > 4.0 and e.element_type == ElementType.TEXT:
                    e.role = RoleCandidate.STATIC
                    e.confidence_score = 0.9
                # Bottom footer heuristic
                elif e.top_in > 6.5 and e.element_type == ElementType.TEXT:
                    e.role = RoleCandidate.STATIC
                    e.confidence_score = 0.9

    @classmethod
    def load_template_config(cls, template_id: str) -> Optional[TemplateMimicConfig]:
        template_dir = cls.get_template_storage_dir(template_id)
        config_path = template_dir / "config.json"
        data = read_json_safely(config_path)
        if not data:
            return None
        return TemplateMimicConfig(**data)

    @classmethod
    def list_template_configs(cls) -> List[TemplateMimicConfig]:
        base_dir = settings.STORAGE_DIR / "templates"
        if not base_dir.exists():
            return []
        configs = []
        for t_dir in base_dir.iterdir():
            if t_dir.is_dir():
                cfg_file = t_dir / "config.json"
                data = read_json_safely(cfg_file)
                if data:
                    try:
                        configs.append(TemplateMimicConfig(**data))
                    except Exception:
                        pass
        configs.sort(key=lambda x: x.created_at, reverse=True)
        return configs

    @classmethod
    def update_element_role(
        cls,
        template_id: str,
        slide_index: int,
        element_id: str,
        new_role: RoleCandidate,
        user_confirmed: bool = True,
        notes: Optional[str] = None,
    ) -> TemplateMimicConfig:
        config = cls.load_template_config(template_id)
        if not config:
            raise ValueError(f"Template with ID '{template_id}' not found.")

        if slide_index < 0 or slide_index >= len(config.slides):
            raise ValueError(f"Slide index {slide_index} out of range.")

        slide = config.slides[slide_index]
        elem = next((e for e in slide.elements if e.element_id == element_id), None)
        if not elem:
            raise ValueError(f"Element '{element_id}' not found in slide {slide_index}.")

        elem.role = new_role
        elem.user_confirmed = user_confirmed
        if notes:
            elem.notes = notes

        config.updated_at = datetime.datetime.utcnow().isoformat()

        # Save update atomically
        config_path = cls.get_template_storage_dir(template_id) / "config.json"
        atomic_write_json(config_path, config.dict())
        return config

    @classmethod
    def configure_slide_layout(
        cls,
        template_id: str,
        slide_index: int,
        layout_role: Optional[str] = None,
        field_mappings: Optional[Dict[str, str]] = None,
    ) -> TemplateMimicConfig:
        config = cls.load_template_config(template_id)
        if not config:
            raise ValueError(f"Template with ID '{template_id}' not found.")

        if slide_index < 0 or slide_index >= len(config.slides):
            raise ValueError(f"Slide index {slide_index} out of range.")

        slide = config.slides[slide_index]
        if layout_role:
            slide.layout_role = layout_role

        if field_mappings:
            for cluster in slide.content_clusters:
                cluster.field_mappings.update(field_mappings)
            for elem in slide.elements:
                if elem.element_id in field_mappings:
                    elem.target_field = field_mappings[elem.element_id]

        config.updated_at = datetime.datetime.utcnow().isoformat()
        config_path = cls.get_template_storage_dir(template_id) / "config.json"
        atomic_write_json(config_path, config.dict())
        return config
        atomic_write_json(config_path, config.model_dump())
        return config
