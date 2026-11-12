export type PhotoMatchStatus =
  | "MATCHED"
  | "MISSING"
  | "AMBIGUOUS"
  | "INVALID_IMAGE"
  | "UNMATCHED_FILE"
  | "DUPLICATE_EMPLOYEE_NAME";

export interface PhotoFileMetadata {
  file_id: str;
  original_filename: string;
  normalized_stem: string;
  extension: string;
  file_size_bytes: number;
  width: number;
  height: number;
  format: string;
  relative_path: string;
  preview_url: string;
  is_valid: boolean;
  error_message?: string | null;
}

export interface EmployeePhotoMatch {
  employee_record_index: number;
  employee_name: string;
  designation?: string;
  branch?: string;
  award_name: string;
  normalized_name: string;
  match_status: PhotoMatchStatus;
  assigned_file?: PhotoFileMetadata | null;
  candidate_files: PhotoFileMetadata[];
  issue_message?: string | null;
  is_resolved: boolean;
  is_reused_override: boolean;
}

export interface PhotoMatchingSessionResponse {
  session_id: string;
  total_employees: number;
  matched_count: number;
  missing_count: number;
  ambiguous_count: number;
  duplicate_name_count: number;
  unmatched_files_count: number;
  invalid_images_count: number;
  is_dataset_ready: boolean;
  employee_matches: EmployeePhotoMatch[];
  unmatched_files: PhotoFileMetadata[];
  all_valid_photos: PhotoFileMetadata[];
}

export interface ResolveAssociationRequest {
  employee_record_index: number;
  file_id?: string | null;
  confirm_reuse?: boolean;
}

export interface DatasetFinalizeResponse {
  session_id: string;
  is_ready: boolean;
  total_employees: number;
  ready_employees: EmployeePhotoMatch[];
  manifest_saved_path?: string | null;
}
type str = string;
