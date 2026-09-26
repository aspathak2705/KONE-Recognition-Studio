export interface RecognitionRecord {
  row_number: number;
  employee_name: string;
  designation: string;
  branch: string;
  award_name: string;
  is_valid: boolean;
  errors: string[];
}

export interface ValidationErrorItem {
  row: number;
  column: string;
  message: string;
}

export interface ExcelValidationResponse {
  valid: boolean;
  filename: string;
  file_id?: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  errors: ValidationErrorItem[];
  records: RecognitionRecord[];
  saved_path?: string;
}

export interface FieldSchemaInfo {
  field_name: string;
  canonical_header: string;
  accepted_aliases: string[];
  required: boolean;
  description: string;
}

export interface SchemaResponse {
  required_fields: FieldSchemaInfo[];
  accepted_formats: string[];
  rules: string[];
}

export interface TextShapeInfo {
  shape_name: string;
  shape_type: string;
  text: string;
  left_inches: number;
  top_inches: number;
  width_inches: number;
  height_inches: number;
  is_placeholder: boolean;
  placeholder_type?: string;
}

export interface SlideInfo {
  slide_number: number;
  shape_count: number;
  text_shapes: TextShapeInfo[];
  placeholders_count: number;
}

export interface TemplateInspectionResponse {
  valid: boolean;
  template_id: string;
  filename: string;
  slide_count: number;
  slide_width_inches: number;
  slide_height_inches: number;
  aspect_ratio: string;
  slides: SlideInfo[];
  warnings: string[];
  saved_path?: string;
}


export interface FieldMappingDetail {
  shape_name: string;
  shape_id?: string;
  placeholder_index?: number;
  required: boolean;
}

export interface FieldMappingConfig {
  employee_name?: FieldMappingDetail;
  designation?: FieldMappingDetail;
  branch?: FieldMappingDetail;
  award_name?: FieldMappingDetail;
}

export interface MappingValidationResponse {
  valid: boolean;
  mapping_status: "not_configured" | "partially_configured" | "valid" | "invalid";
  errors: string[];
  warnings: string[];
}

export interface TemplateReadinessResponse {
  template_id: string;
  filename: string;
  inspection_status: "success" | "failed";
  mapping_status: "not_configured" | "partially_configured" | "valid" | "invalid";
  generation_readiness: "requires_template" | "requires_mapping" | "blocked_by_validation" | "ready_for_generation";
  configured_mapping?: FieldMappingConfig;
  suggested_mapping?: FieldMappingConfig;
  warnings: string[];
  errors: string[];
}

export interface GenerationRequest {
  excel_file_id: string;
  template_file_id: string;
  template_version?: number;
  mapping_config?: FieldMappingConfig;
}

export interface GenerationResponse {
  generation_id: string;
  source_template_file_id: string;
  source_excel_file_id: string;
  generated_file_id: string;
  record_count: number;
  slide_count: number;
  status: string;
  warnings: string[];
  download_url: string;
}

export interface TemplateVersion {
  version_number: number;
  file_hash: string;
  filename: string;
  pptx_rel_path: string;
  inspection_status: "success" | "failed";
  mapping_status: "not_configured" | "partially_configured" | "valid" | "invalid";
  generation_readiness: "requires_template" | "requires_mapping" | "blocked_by_validation" | "ready_for_generation";
  mapping_config?: FieldMappingConfig;
  inspection_data?: TemplateInspectionResponse;
  created_at: string;
}

export interface TemplateMetadata {
  template_id: string;
  name: string;
  current_version: number;
  file_hash: string;
  inspection_status: "success" | "failed";
  mapping_status: "not_configured" | "partially_configured" | "valid" | "invalid";
  generation_readiness: "requires_template" | "requires_mapping" | "blocked_by_validation" | "ready_for_generation";
  aspect_ratio: string;
  versions: TemplateVersion[];
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface TemplateRegistrationResponse {
  template: TemplateMetadata;
  active_version: TemplateVersion;
  is_new_version: boolean;
  is_duplicate_hash: boolean;
  message: string;
}

