import { useState } from "react";
import { FileUpload } from "../components/FileUpload";
import {
  ExcelValidationResponse,
  TemplateInspectionResponse,
  TemplateReadinessResponse,
  FieldMappingConfig,
  GenerationResponse,
} from "../types/recognition";
import {
  uploadAndValidateExcel,
  uploadAndInspectTemplate,
  fetchTemplateReadiness,
  generatePresentation,
} from "../services/api";
import {
  CheckCircle2,
  AlertTriangle,
  Download,
  Settings2,
  Presentation,
  RefreshCw,
} from "lucide-react";

export function GeneratePresentation() {
  const [excelResult, setExcelResult] = useState<ExcelValidationResponse | null>(null);
  const [templateResult, setTemplateResult] = useState<TemplateInspectionResponse | null>(null);
  const [readiness, setReadiness] = useState<TemplateReadinessResponse | null>(null);

  const [isUploadingExcel, setIsUploadingExcel] = useState(false);
  const [isUploadingTemplate, setIsUploadingTemplate] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const [mapping, setMapping] = useState<FieldMappingConfig>({});
  const [genResponse, setGenResponse] = useState<GenerationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleExcelSelect = async (file: File) => {
    setIsUploadingExcel(true);
    setErrorMsg(null);
    try {
      const res = await uploadAndValidateExcel(file);
      setExcelResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to upload Excel file.");
      setExcelResult(null);
    } finally {
      setIsUploadingExcel(false);
    }
  };

  const handleTemplateSelect = async (file: File) => {
    setIsUploadingTemplate(true);
    setErrorMsg(null);
    try {
      const res = await uploadAndInspectTemplate(file);
      setTemplateResult(res);
      if (res.template_id) {
        const readRes = await fetchTemplateReadiness(res.template_id);
        setReadiness(readRes);
        if (readRes.suggested_mapping) {
          setMapping(readRes.suggested_mapping);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to upload Template file.");
      setTemplateResult(null);
      setReadiness(null);
    } finally {
      setIsUploadingTemplate(false);
    }
  };

  const handleGenerate = async () => {
    if (!excelResult?.file_id || !templateResult?.template_id) {
      setErrorMsg("Please upload both a valid Excel file and a PowerPoint template first.");
      return;
    }

    setIsGenerating(true);
    setErrorMsg(null);
    try {
      const res = await generatePresentation({
        excel_file_id: excelResult.file_id,
        template_file_id: templateResult.template_id,
        mapping_config: mapping,
      });
      setGenResponse(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Presentation generation failed.");
      setGenResponse(null);
    } finally {
      setIsGenerating(false);
    }
  };

  const availableShapes =
    templateResult?.slides && templateResult.slides[0]
      ? templateResult.slides[0].text_shapes.map((s) => s.shape_name)
      : [];

  return (
    <div className="space-y-8">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Generate PowerPoint Presentation</h2>
          <p className="text-xs text-muted-foreground">
            Map Excel employee recognition fields to PowerPoint template text shapes and generate editable PPTX slides.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Inputs Step Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Step 1: Excel Input */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 text-primary font-bold text-xs">
                1
              </div>
              <h3 className="font-semibold text-sm text-foreground">Source Excel Recognition Data</h3>
            </div>
            {excelResult && (
              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                excelResult.valid ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600"
              }`}>
                {excelResult.valid_rows} Valid Rows
              </span>
            )}
          </div>

          <FileUpload
            accept=".xlsx"
            acceptLabel="Select Excel workbook (.xlsx)"
            onFileSelect={handleExcelSelect}
            isLoading={isUploadingExcel}
          />

          {excelResult && (
            <div className="p-3 rounded-md bg-muted/40 text-xs space-y-1">
              <p className="font-medium text-foreground truncate">{excelResult.filename}</p>
              <p className="text-muted-foreground">{excelResult.records.length} employee records extracted.</p>
            </div>
          )}
        </div>

        {/* Step 2: Template Input */}
        <div className="rounded-lg border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 text-primary font-bold text-xs">
                2
              </div>
              <h3 className="font-semibold text-sm text-foreground">Master PowerPoint Template</h3>
            </div>
            {readiness && (
              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                readiness.generation_readiness === "ready_for_generation"
                  ? "bg-emerald-500/10 text-emerald-600"
                  : "bg-amber-500/10 text-amber-600"
              }`}>
                {readiness.generation_readiness.replace(/_/g, " ")}
              </span>
            )}
          </div>

          <FileUpload
            accept=".pptx"
            acceptLabel="Select PowerPoint template (.pptx)"
            onFileSelect={handleTemplateSelect}
            isLoading={isUploadingTemplate}
          />

          {templateResult && (
            <div className="p-3 rounded-md bg-muted/40 text-xs space-y-1">
              <p className="font-medium text-foreground truncate">{templateResult.filename}</p>
              <p className="text-muted-foreground">
                {templateResult.slide_count} slides ({templateResult.aspect_ratio})
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Step 3: Field Mapping Configuration */}
      {templateResult && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-primary" />
              <h3 className="font-semibold text-sm text-foreground">Field Shape Mapping Configuration</h3>
            </div>
            <span className="text-xs text-muted-foreground">
              Select target text shape name on slide #1 for each recognition field
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { field: "employee_name", label: "Employee Name" },
              { field: "designation", label: "Designation" },
              { field: "branch", label: "Branch Location" },
              { field: "award_name", label: "Award / Recognition Category" },
            ].map(({ field, label }) => {
              const currentVal = (mapping as any)[field]?.shape_name || "";

              return (
                <div key={field} className="p-3 rounded-md border border-border bg-muted/30 space-y-2">
                  <label className="block text-xs font-semibold text-foreground">{label}</label>
                  <select
                    value={currentVal}
                    onChange={(e) =>
                      setMapping((prev) => ({
                        ...prev,
                        [field]: { shape_name: e.target.value, required: true },
                      }))
                    }
                    className="w-full rounded-md border border-border bg-card px-3 py-1.5 text-xs text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
                  >
                    <option value="">-- Select Target Shape --</option>
                    {availableShapes.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>

          {/* Readiness Warnings */}
          {readiness && readiness.warnings.length > 0 && (
            <div className="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-xs space-y-1">
              <p className="font-semibold text-amber-600">Inspection & Mapping Warnings</p>
              {readiness.warnings.map((w, idx) => (
                <p key={idx} className="text-amber-700 dark:text-amber-400">• {w}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action Button */}
      <div className="flex justify-end pt-2">
        <button
          onClick={handleGenerate}
          disabled={!excelResult?.valid || !templateResult?.valid || isGenerating}
          className={`inline-flex items-center justify-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors ${
            !excelResult?.valid || !templateResult?.valid || isGenerating
              ? "opacity-50 cursor-not-allowed"
              : "cursor-pointer"
          }`}
        >
          {isGenerating ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Generating Presentation...
            </>
          ) : (
            <>
              <Presentation className="h-4 w-4" />
              Generate PowerPoint Presentation
            </>
          )}
        </button>
      </div>

      {/* Generation Success & Download */}
      {genResponse && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold text-sm">
              <CheckCircle2 className="h-5 w-5" />
              <span>Presentation Generation Completed!</span>
            </div>
            <span className="text-xs text-muted-foreground font-mono">ID: {genResponse.generation_id}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 rounded-md bg-card border border-border">
              <p className="text-muted-foreground">Processed Records</p>
              <p className="text-lg font-bold text-foreground mt-0.5">{genResponse.record_count}</p>
            </div>
            <div className="p-3 rounded-md bg-card border border-border">
              <p className="text-muted-foreground">Generated Slides</p>
              <p className="text-lg font-bold text-primary mt-0.5">{genResponse.slide_count}</p>
            </div>
            <div className="p-3 rounded-md bg-card border border-border">
              <p className="text-muted-foreground">Status</p>
              <p className="text-lg font-bold text-emerald-600 mt-0.5 uppercase">{genResponse.status}</p>
            </div>
          </div>

          {genResponse.warnings.length > 0 && (
            <div className="p-3 rounded-md bg-card border border-amber-500/30 text-xs text-amber-700 dark:text-amber-400 space-y-1">
              <p className="font-semibold">Text Fitting & Overflow Warnings:</p>
              {genResponse.warnings.map((w, idx) => (
                <p key={idx}>• {w}</p>
              ))}
            </div>
          )}

          <div className="pt-2 flex justify-end">
            <a
              href={`http://127.0.0.1:8000${genResponse.download_url}`}
              download
              className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-5 py-2 text-sm font-semibold text-white shadow-xs hover:bg-emerald-700 transition-colors"
            >
              <Download className="h-4 w-4" />
              Download Generated Presentation (.pptx)
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
