import {
  ExcelValidationResponse,
  SchemaResponse,
  TemplateInspectionResponse,
} from "../types/recognition";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchExcelSchema(): Promise<SchemaResponse> {
  const res = await fetch(`${API_BASE_URL}/api/recognitions/schema`);
  if (!res.ok) {
    throw new Error("Failed to fetch Excel schema specification.");
  }
  return res.json();
}

export async function uploadAndValidateExcel(file: File): Promise<ExcelValidationResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/recognitions/validate-excel`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Excel validation failed with status ${res.status}`);
  }

  return res.json();
}

export async function uploadAndInspectTemplate(file: File): Promise<TemplateInspectionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/templates/inspect`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Template inspection failed with status ${res.status}`);
  }

  return res.json();
}
