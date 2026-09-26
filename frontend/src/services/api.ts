import {
  ExcelValidationResponse,
  SchemaResponse,
  TemplateInspectionResponse,
  TemplateReadinessResponse,
  FieldMappingConfig,
  MappingValidationResponse,
  GenerationRequest,
  GenerationResponse,
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

export async function fetchTemplateReadiness(fileId: string): Promise<TemplateReadinessResponse> {
  const res = await fetch(`${API_BASE_URL}/api/templates/${fileId}/readiness`);
  if (!res.ok) {
    throw new Error("Failed to fetch template readiness status.");
  }
  return res.json();
}

export async function validateMapping(
  fileId: string,
  mappingConfig: FieldMappingConfig
): Promise<MappingValidationResponse> {
  const res = await fetch(`${API_BASE_URL}/api/templates/mapping/validate?file_id=${fileId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mappingConfig),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || "Mapping validation failed.");
  }
  return res.json();
}

export async function generatePresentation(req: GenerationRequest): Promise<GenerationResponse> {
  const res = await fetch(`${API_BASE_URL}/api/recognitions/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || "Presentation generation failed.");
  }
  return res.json();
}

export function getDownloadUrl(generationId: string): string {
  return `${API_BASE_URL}/api/generations/${generationId}/download`;
}

