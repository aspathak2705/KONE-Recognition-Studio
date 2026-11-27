export type ElementType = "TEXT" | "IMAGE" | "SHAPE" | "TABLE" | "GROUP" | "UNKNOWN";

export type RoleCandidate = "STATIC" | "CONTAINER" | "REPLACEABLE_TEXT" | "REPLACEABLE_IMAGE" | "UNCONFIGURED";

export interface TextStyleInfo {
  font_name?: string;
  font_size_pt?: number;
  bold?: boolean;
  italic?: boolean;
  color_rgb?: string;
  alignment?: string;
}

export interface VisualElementConfig {
  element_id: string;
  original_shape_id?: number;
  shape_name: string;
  element_type: ElementType;
  left_in: number;
  top_in: number;
  width_in: number;
  height_in: number;
  fill_color_rgb?: string;
  line_color_rgb?: string;
  text_sample?: string;
  text_style?: TextStyleInfo;
  role: RoleCandidate;
  capabilities: string[];
  confidence_score: number;
  user_confirmed: boolean;
  notes?: string;
  target_field?: string;
}

export interface ContentCluster {
  cluster_id: string;
  bounding_box_in: number[];
  element_ids: string[];
  suggested_role: string;
  is_repeating_unit: boolean;
  field_mappings?: Record<string, string>;
}

export interface SlideLayoutConfig {
  slide_index: number;
  slide_width_in: number;
  slide_height_in: number;
  elements: VisualElementConfig[];
  content_clusters: ContentCluster[];
  is_suitable_for_content: boolean;
  layout_signature: string;
  layout_role?: "COVER" | "CONTENT" | "CLOSING";
}

export interface TemplateThemePalette {
  primary_color_rgb?: string;
  secondary_color_rgb?: string;
  accent_color_rgb?: string;
  background_color_rgb?: string;
  primary_font?: string;
  secondary_font?: string;
  detected_colors: string[];
  detected_fonts: string[];
}

export interface TemplateMimicConfig {
  template_id: string;
  filename: string;
  name: string;
  version: number;
  created_at: string;
  updated_at: string;
  slide_count: number;
  slide_width_in: number;
  slide_height_in: number;
  aspect_ratio: string;
  theme: TemplateThemePalette;
  slides: SlideLayoutConfig[];
  is_valid: boolean;
  validation_warnings: string[];
  preview_slide_urls: string[];
}
