import { useState, useEffect } from "react";
import { FileUpload } from "../components/FileUpload";
import {
  ExcelValidationResponse,
  TemplateMetadata,
  GenerationResponse,
} from "../types/recognition";
import {
  uploadAndValidateExcel,
  fetchRegisteredTemplates,
  generatePresentation,
  getDownloadUrl,
} from "../services/api";
import {
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Download,
  Award,
  RefreshCw,
  ArrowRight,
  Plus,
  Sparkles,
  Image as ImageIcon,
} from "lucide-react";

interface CreatePresentationProps {
  onNavigateToTemplates?: () => void;
}

export function CreatePresentation({ onNavigateToTemplates }: CreatePresentationProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Step 1: Excel Data
  const [excelResult, setExcelResult] = useState<ExcelValidationResponse | null>(null);
  const [isUploadingExcel, setIsUploadingExcel] = useState(false);

  // Step 2: Registered Template Selection
  const [templates, setTemplates] = useState<TemplateMetadata[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateMetadata | null>(null);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);

  // Step 3 & 4: Generation
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResponse, setGenResponse] = useState<GenerationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const data = await fetchRegisteredTemplates(false);
      setTemplates(data);
      if (data.length > 0 && !selectedTemplate) {
        const ready = data.find((t) => t.generation_readiness === "ready_for_generation") || data[0];
        setSelectedTemplate(ready);
      }
    } catch {
      // Ignore initial load error
    } finally {
      setIsLoadingTemplates(false);
    }
  };

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

  const handleGenerate = async () => {
    if (!excelResult?.file_id || !selectedTemplate) {
      setErrorMsg("Please provide recognition Excel data and select a master template.");
      return;
    }

    setIsGenerating(true);
    setErrorMsg(null);
    try {
      const res = await generatePresentation({
        excel_file_id: excelResult.file_id,
        template_file_id: selectedTemplate.template_id,
        template_version: selectedTemplate.current_version,
      });
      setGenResponse(res);
      setStep(4);
    } catch (err: any) {
      setErrorMsg(err.message || "Presentation generation failed.");
      setGenResponse(null);
    } finally {
      setIsGenerating(false);
    }
  };

  const activeVersion = selectedTemplate?.versions.find(
    (v) => v.version_number === selectedTemplate.current_version
  );
  const capacities = selectedTemplate?.supported_capacities || activeVersion?.supported_capacities || [1];
  const maxCap = Math.max(...capacities);
  const numEmployees = excelResult?.valid_rows || 0;
  const estSlides = numEmployees > 0 ? Math.ceil(numEmployees / maxCap) : 1;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Wizard Progress Bar */}
      <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
        <div className="grid grid-cols-4 gap-2 text-center text-xs font-semibold">
          {[
            { s: 1, label: "1. Recognition Data" },
            { s: 2, label: "2. Master Template" },
            { s: 3, label: "3. Review & Confirm" },
            { s: 4, label: "4. Presentation Output" },
          ].map((item) => {
            const isActive = step === item.s;
            const isDone = step > item.s;
            return (
              <div
                key={item.s}
                className={`py-2 px-3 rounded-md transition-all ${
                  isActive
                    ? "bg-primary text-primary-foreground font-bold shadow-xs"
                    : isDone
                    ? "bg-primary/10 text-primary"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {item.label}
              </div>
            );
          })}
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-4 text-xs text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* STEP 1: Excel Data Upload */}
      {step === 1 && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-6 shadow-xs">
          <div className="border-b border-border pb-4">
            <h3 className="text-lg font-bold text-foreground">Step 1 — Recognition Data Upload</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Upload recognition Excel data sheet (`.xlsx`). Columns are automatically detected.
            </p>
          </div>

          <FileUpload
            accept=".xlsx"
            acceptLabel="Excel files (.xlsx) up to 20MB"
            onFileSelect={handleExcelSelect}
            isLoading={isUploadingExcel}
          />

          {excelResult && (
            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between p-4 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-600">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 shrink-0" />
                  <div>
                    <p className="font-bold text-sm">{excelResult.filename} Validated</p>
                    <p className="text-xs">
                      {excelResult.valid_rows} recognition records ready for presentation generation.
                    </p>
                  </div>
                </div>
              </div>

              {/* Detected Excel Columns */}
              {excelResult.detected_columns && excelResult.detected_columns.length > 0 && (
                <div className="p-3 rounded-md border border-border bg-muted/20 space-y-1.5">
                  <p className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-primary" /> Detected Data Columns:
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {excelResult.detected_columns.map((col) => (
                      <span
                        key={col}
                        className="px-2 py-0.5 rounded text-[11px] bg-background border border-border font-mono text-foreground"
                      >
                        {col}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setStep(2)}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 cursor-pointer"
                >
                  Continue to Template Selection <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 2: Template Selection */}
      {step === 2 && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-6 shadow-xs">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h3 className="text-lg font-bold text-foreground">Step 2 — Select Master Template</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Select an official KONE master presentation template. Layouts adapt automatically to record counts.
              </p>
            </div>
            {onNavigateToTemplates && (
              <button
                onClick={onNavigateToTemplates}
                className="inline-flex items-center gap-1.5 text-xs text-primary font-medium hover:underline cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" /> Manage Template Library
              </button>
            )}
          </div>

          {isLoadingTemplates ? (
            <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Loading registered templates...
            </div>
          ) : templates.length === 0 ? (
            <div className="p-8 border border-dashed border-border rounded-lg text-center space-y-3">
              <FileSpreadsheet className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium text-foreground">No Registered Templates Found</p>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                No PowerPoint master templates are currently registered in the library. Please add a template first.
              </p>
              {onNavigateToTemplates && (
                <button
                  onClick={onNavigateToTemplates}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer"
                >
                  <Plus className="h-3.5 w-3.5" /> Add Template to Library
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {templates.map((tpl) => {
                const isSelected = selectedTemplate?.template_id === tpl.template_id;
                const isReady = tpl.generation_readiness === "ready_for_generation";
                const caps = tpl.supported_capacities || [1];

                return (
                  <div
                    key={tpl.template_id}
                    onClick={() => isReady && setSelectedTemplate(tpl)}
                    className={`p-4 rounded-lg border text-left cursor-pointer transition-all ${
                      isSelected
                        ? "border-primary bg-primary/5 ring-1 ring-primary shadow-xs"
                        : !isReady
                        ? "border-border bg-muted/30 opacity-60 cursor-not-allowed"
                        : "border-border bg-card hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-bold text-sm text-foreground">{tpl.name}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          v{tpl.current_version} • Aspect Ratio {tpl.aspect_ratio}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-1">
                          Capacities: {caps.join(", ")} per slide
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                          isReady ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600"
                        }`}
                      >
                        {isReady ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                        {isReady ? "Ready" : "Under Review"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center justify-between pt-4 border-t border-border">
            <button
              onClick={() => setStep(1)}
              className="rounded-md border border-border bg-card px-4 py-2 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
            >
              Back
            </button>

            <button
              onClick={() => setStep(3)}
              disabled={!selectedTemplate || selectedTemplate.generation_readiness !== "ready_for_generation"}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 disabled:opacity-50 cursor-pointer"
            >
              Review Presentation <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Dynamic Review & Confirm */}
      {step === 3 && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-6 shadow-xs">
          <div className="border-b border-border pb-4">
            <h3 className="text-lg font-bold text-foreground">Step 3 — Review & Confirm Presentation</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Confirm your recognition dataset and master template before generating the PowerPoint file.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Excel Data Summary */}
            <div className="p-4 rounded-lg border border-border bg-muted/20 space-y-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recognition Dataset</p>
              <div>
                <p className="text-sm font-bold text-foreground truncate">{excelResult?.filename}</p>
                <p className="text-xs text-emerald-600 font-medium mt-0.5 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  {excelResult?.valid_rows} Employees Validated
                </p>
              </div>

              <div className="text-xs border-t border-border/50 pt-2 space-y-1">
                <span className="text-muted-foreground font-medium">Mapped Recognition Fields:</span>
                <div className="space-y-0.5 text-[11px] font-mono text-foreground">
                  <div>Employee Name ← Name / Employee Name</div>
                  <div>Designation ← Role / Job Title</div>
                  <div>Branch ← Location / Branch</div>
                </div>
              </div>
            </div>

            {/* Template Summary */}
            <div className="p-4 rounded-lg border border-border bg-muted/20 space-y-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">PowerPoint Master</p>
              <div>
                <p className="text-sm font-bold text-foreground">{selectedTemplate?.name}</p>
                <p className="text-xs text-muted-foreground">Version {selectedTemplate?.current_version} ({selectedTemplate?.aspect_ratio})</p>
              </div>

              <div className="text-xs border-t border-border/50 pt-2 space-y-1">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Supported Slide Capacities:</span>
                  <span className="font-semibold text-foreground">{capacities.join(", ")}</span>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Estimated Slide Count:</span>
                  <span className="font-bold text-primary">~{estSlides} Content Slide(s)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Photo Note */}
          <div className="flex items-center gap-2.5 p-3 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-600 text-xs">
            <ImageIcon className="h-4 w-4 shrink-0" />
            <span>
              <strong>Sample portraits cleared:</strong> Generated presentation leaves photo regions empty and ready for manual HR portrait insertion.
            </span>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-border">
            <button
              onClick={() => setStep(2)}
              className="rounded-md border border-border bg-card px-4 py-2 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
            >
              Back
            </button>

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 disabled:opacity-50 cursor-pointer"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" /> Generating Presentation...
                </>
              ) : (
                <>
                  <Award className="h-4 w-4" /> Generate Presentation
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Complete & Download */}
      {step === 4 && genResponse && (
        <div className="rounded-lg border border-border bg-card p-8 text-center space-y-6 shadow-xs">
          <div className="h-14 w-14 rounded-full bg-emerald-500/10 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="h-8 w-8" />
          </div>

          <div>
            <h3 className="text-xl font-bold text-foreground">Presentation Generated Successfully</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Generated PowerPoint presentation containing {genResponse.slide_count} slides for {genResponse.record_count} recognition records.
            </p>
          </div>

          <div className="pt-2 flex justify-center gap-4">
            <a
              href={getDownloadUrl(genResponse.generation_id)}
              download
              className="inline-flex items-center gap-2 rounded-md bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-colors cursor-pointer"
            >
              <Download className="h-4 w-4" /> Download Presentation (.pptx)
            </a>

            <button
              onClick={() => {
                setStep(1);
                setExcelResult(null);
                setGenResponse(null);
              }}
              className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-4 py-3 text-sm font-medium text-foreground hover:bg-muted transition-colors cursor-pointer"
            >
              Create Another Presentation
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
