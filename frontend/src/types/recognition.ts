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
