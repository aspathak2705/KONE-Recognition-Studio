import { EmployeePhotoMatch } from "./photo_matching";

export interface AwardGroup {
  award_name: string;
  normalized_award_name: string;
  employee_count: number;
  employees: EmployeePhotoMatch[];
}

export interface SlideGeometryFinding {
  slide_index: number;
  severity: "PASS" | "WARNING" | "ERROR";
  issue_type: string;
  message: string;
}

export interface DynamicGenerationResponse {
  generation_id: string;
  session_id: string;
  slide_count: number;
  total_employees: number;
  award_categories_count: number;
  award_groups: AwardGroup[];
  download_url: string;
  pptx_path: string;
  is_valid: boolean;
  validation_findings: SlideGeometryFinding[];
  rendered_slide_urls: string[];
  delivery_status: string;
  can_download: boolean;
  created_at: string;
}
