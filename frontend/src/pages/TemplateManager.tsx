import { useState } from "react";
import { FileUpload } from "../components/FileUpload";
import { TemplateInspectionResponse } from "../types/recognition";
import { uploadAndInspectTemplate } from "../services/api";
import { Presentation, CheckCircle2, AlertTriangle } from "lucide-react";

export function TemplateManager() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [inspectionResult, setInspectionResult] = useState<TemplateInspectionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const res = await uploadAndInspectTemplate(file);
      setInspectionResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to inspect PowerPoint template.");
      setInspectionResult(null);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Template Inspector</h2>
          <p className="text-xs text-muted-foreground">
            Upload KONE master newspaper PowerPoint template (`.pptx`) for dynamic shape structure inspection.
          </p>
        </div>
      </div>

      {/* Upload Control */}
      <div className="space-y-4">
        <FileUpload
          accept=".pptx"
          acceptLabel="PowerPoint Presentations (.pptx) up to 20MB"
          onFileSelect={handleFileSelect}
          isLoading={isProcessing}
        />

        {errorMsg && (
          <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Inspection Results */}
      {inspectionResult && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-foreground">Template Inspection Metadata</h3>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary">
              <CheckCircle2 className="h-4 w-4" /> Inspected & Preserved
            </span>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs font-medium text-muted-foreground">Filename</p>
              <p className="text-sm font-bold text-foreground mt-1 truncate">{inspectionResult.filename}</p>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs font-medium text-muted-foreground">Slide Count</p>
              <p className="text-2xl font-bold text-primary mt-1">{inspectionResult.slide_count}</p>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs font-medium text-muted-foreground">Dimensions</p>
              <p className="text-sm font-bold text-foreground mt-1">
                {inspectionResult.slide_width_inches}" × {inspectionResult.slide_height_inches}"
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs font-medium text-muted-foreground">Aspect Ratio</p>
              <p className="text-2xl font-bold text-foreground mt-1">{inspectionResult.aspect_ratio}</p>
            </div>
          </div>

          {/* Warnings list */}
          {inspectionResult.warnings.length > 0 && (
            <div className="rounded-md border border-amber-500/20 bg-amber-500/10 p-4 space-y-1">
              <p className="text-xs font-semibold text-amber-600">Inspection Warnings</p>
              {inspectionResult.warnings.map((w, i) => (
                <p key={i} className="text-xs text-amber-700 dark:text-amber-400">• {w}</p>
              ))}
            </div>
          )}

          {/* Slide Shape Breakdown */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-foreground">Slide Structure Breakdown</h4>
            <div className="space-y-4">
              {inspectionResult.slides.map((slide) => (
                <div key={slide.slide_number} className="rounded-lg border border-border bg-card p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <div className="flex items-center gap-2">
                      <Presentation className="h-4 w-4 text-primary" />
                      <span className="font-semibold text-sm">Slide #{slide.slide_number}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {slide.shape_count} total shapes ({slide.placeholders_count} placeholders)
                    </span>
                  </div>

                  {slide.text_shapes.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-foreground">
                        <thead className="bg-muted/40 border-b border-border text-muted-foreground">
                          <tr>
                            <th className="px-3 py-2">Shape Name</th>
                            <th className="px-3 py-2">Type</th>
                            <th className="px-3 py-2">Position (L, T)</th>
                            <th className="px-3 py-2">Size (W, H)</th>
                            <th className="px-3 py-2">Sample Text Content</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {slide.text_shapes.map((s, idx) => (
                            <tr key={idx} className="hover:bg-muted/20">
                              <td className="px-3 py-2 font-medium font-mono text-primary">{s.shape_name}</td>
                              <td className="px-3 py-2 text-muted-foreground">{s.shape_type}</td>
                              <td className="px-3 py-2 font-mono text-muted-foreground">
                                {s.left_inches}in, {s.top_inches}in
                              </td>
                              <td className="px-3 py-2 font-mono text-muted-foreground">
                                {s.width_inches}in × {s.height_inches}in
                              </td>
                              <td className="px-3 py-2 text-foreground font-sans truncate max-w-xs">
                                {s.text || <span className="text-muted-foreground/40 italic">(empty frame)</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">No readable text shapes found on this slide.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
