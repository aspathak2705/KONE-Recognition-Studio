import { useState, useEffect } from "react";
import { Plus, Award, UploadCloud, Users, Sparkles, History, Download, Eye, RefreshCw, AlertCircle, FileText } from "lucide-react";
import { PresentationHistoryItem, PresentationHistoryResponse } from "../types/presentation_history";

interface DashboardProps {
  onNavigateToCreate: () => void;
}

export function Dashboard({ onNavigateToCreate }: DashboardProps) {
  const [history, setHistory] = useState<PresentationHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [previewItem, setPreviewItem] = useState<PresentationHistoryItem | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/generations/history");
      if (!res.ok) {
        throw new Error(`Failed to load history (Status: ${res.status})`);
      }
      const data: PresentationHistoryResponse = await res.json();
      setHistory(data.items || []);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load presentation history.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Hero / Welcome Banner */}
      <div className="rounded-lg border border-border bg-card p-8 shadow-xs">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Intelligent Recognition Generator
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            KONE Recognition Studio
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Create employee recognition presentations using Excel recognition data and employee photographs. The system automatically matches photos, groups awards and generates editable PowerPoint presentations.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={onNavigateToCreate}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors cursor-pointer"
            >
              <Plus className="h-4 w-4" />
              Create Presentation
            </button>
          </div>
        </div>
      </div>

      {/* Previous Presentations Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-bold text-foreground">Previous Presentations</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-muted font-medium text-muted-foreground">
              {history.length}
            </span>
          </div>

          <button
            onClick={fetchHistory}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer disabled:opacity-50"
            title="Refresh presentation history"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
            Loading presentation history...
          </div>
        )}

        {/* Error State */}
        {!isLoading && errorMsg && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 flex items-start gap-3 text-red-800">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-semibold">Unable to load presentation history</p>
              <p className="text-xs text-red-700 mt-1">{errorMsg}</p>
            </div>
            <button
              onClick={fetchHistory}
              className="px-3 py-1 text-xs font-semibold rounded bg-red-100 hover:bg-red-200 text-red-900"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !errorMsg && history.length === 0 && (
          <div className="rounded-lg border border-dashed border-border p-10 text-center space-y-3 bg-card/50">
            <FileText className="h-8 w-8 mx-auto text-muted-foreground/60" />
            <h4 className="font-semibold text-sm text-foreground">No Presentations Generated Yet</h4>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              Get started by uploading an employee recognition Excel workbook and photograph directory.
            </p>
            <div className="pt-2">
              <button
                onClick={onNavigateToCreate}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
                Create First Presentation
              </button>
            </div>
          </div>
        )}

        {/* Presentations List */}
        {!isLoading && !errorMsg && history.length > 0 && (
          <div className="grid grid-cols-1 gap-4">
            {history.map((item) => (
              <div
                key={item.generation_id}
                className="rounded-lg border border-border bg-card p-5 shadow-xs hover:border-primary/40 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-foreground">
                      {item.presentation_name}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        item.can_download
                          ? "bg-emerald-500/10 text-emerald-700 border border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-700 border border-amber-500/20"
                      }`}
                    >
                      {item.delivery_status}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>Generated: {formatDate(item.created_at)}</span>
                    <span>•</span>
                    <span>{item.record_count} Employees</span>
                    <span>•</span>
                    <span>{item.award_categories_count} Award Categories</span>
                    <span>•</span>
                    <span>{item.slide_count} Slides</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  {item.rendered_slide_urls && item.rendered_slide_urls.length > 0 && (
                    <button
                      onClick={() => setPreviewItem(item)}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-border text-xs font-medium text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
                    >
                      <Eye className="h-3.5 w-3.5 text-primary" />
                      Preview
                    </button>
                  )}

                  {item.can_download ? (
                    <a
                      href={`http://127.0.0.1:8000${item.download_url}`}
                      download
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 shadow-xs transition-colors cursor-pointer"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Download PPTX
                    </a>
                  ) : (
                    <span className="text-xs text-muted-foreground italic px-2 py-1">
                      Artifact unavailable
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Preview Dialog */}
      {previewItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h4 className="font-bold text-base text-foreground">{previewItem.presentation_name}</h4>
                <p className="text-xs text-muted-foreground">
                  {previewItem.slide_count} slides • Generated {formatDate(previewItem.created_at)}
                </p>
              </div>
              <button
                onClick={() => setPreviewItem(null)}
                className="px-3 py-1 rounded text-xs font-semibold hover:bg-muted text-muted-foreground hover:text-foreground"
              >
                Close ✕
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {previewItem.rendered_slide_urls.map((url, idx) => (
                  <div key={url} className="border border-border rounded shadow-xs overflow-hidden bg-muted/20">
                    <img
                      src={`http://127.0.0.1:8000${url}`}
                      alt={`Slide ${idx + 1}`}
                      className="w-full h-auto object-cover border-b border-border"
                    />
                    <div className="p-2 text-center text-xs font-medium text-muted-foreground">
                      Slide {idx + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-4 border-t border-border flex justify-end gap-3 bg-muted/10">
              <button
                onClick={() => setPreviewItem(null)}
                className="px-4 py-2 rounded-md border text-xs font-medium text-foreground hover:bg-muted/50"
              >
                Done
              </button>
              {previewItem.can_download && (
                <a
                  href={`http://127.0.0.1:8000${previewItem.download_url}`}
                  download
                  className="px-4 py-2 rounded-md bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                >
                  Download PPTX
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Workflow Steps Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <div className="rounded-lg border border-border bg-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center text-primary">
            <UploadCloud className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-sm text-foreground">1. Provide Recognition Data & Photos</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Upload the HR recognition Excel workbook along with employee photographs (folder or ZIP archive).
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center text-primary">
            <Users className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-sm text-foreground">2. Photo Matching & Resolution</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            The intelligent matching engine associates photographs with employee records, with manual resolution for ambiguous names.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-md bg-primary/10 flex items-center justify-center text-primary">
            <Award className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-sm text-foreground">3. Dynamic Presentation Delivery</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Employees are grouped by award category, slides are paginated dynamically, and a verified editable PPTX is generated with slide previews.
          </p>
        </div>
      </div>
    </div>
  );
}
