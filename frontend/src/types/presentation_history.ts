export interface PresentationHistoryItem {
  generation_id: string;
  presentation_name: string;
  created_at: string;
  record_count: number;
  award_categories_count: number;
  slide_count: number;
  status: string;
  delivery_status: string;
  can_download: boolean;
  download_url: string;
  rendered_slide_urls: string[];
}

export interface PresentationHistoryResponse {
  total_count: number;
  items: PresentationHistoryItem[];
}
