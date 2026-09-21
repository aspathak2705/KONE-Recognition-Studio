import { useEffect, useState } from "react";
import { FileUp, Award, CheckCircle2, AlertCircle, RefreshCw, FileSpreadsheet } from "lucide-react";

interface DashboardProps {
  onNavigateToImport: () => void;
  onNavigateToTemplates: () => void;
}

export function Dashboard({ onNavigateToImport, onNavigateToTemplates }: DashboardProps) {
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "error">("checking");
  const [backendService, setBackendService] = useState<string>("");

  const checkBackendHealth = async () => {
    setBackendStatus("checking");
    try {
      const res = await fetch("http://127.0.0.1:8000/health");
      if (res.ok) {
        const data = await res.json();
        setBackendStatus("connected");
        setBackendService(data.service);
      } else {
        setBackendStatus("error");
      }
    } catch {
      setBackendStatus("error");
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-xs">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-muted text-xs font-medium text-muted-foreground">
            <Award className="h-3.5 w-3.5 text-primary" />
            Internal Enterprise Tool — Phase 1 Active
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            KONE Recognition Studio
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Create quarterly employee recognition presentations from structured employee data.
            Upload Excel recognition sheets and inspect master newspaper-style PowerPoint templates.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={onNavigateToImport}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors cursor-pointer"
            >
              <FileUp className="h-4 w-4" />
              Upload & Validate Excel Data
            </button>

            <button
              onClick={onNavigateToTemplates}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground shadow-xs hover:bg-muted/50 transition-colors cursor-pointer"
            >
              <FileSpreadsheet className="h-4 w-4 text-primary" />
              Inspect PowerPoint Template
            </button>

            {/* Backend connection badge */}
            <div className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs font-medium">
              {backendStatus === "checking" && (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  <span>Checking Backend API...</span>
                </>
              )}
              {backendStatus === "connected" && (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span className="text-foreground">Backend Online ({backendService})</span>
                </>
              )}
              {backendStatus === "error" && (
                <>
                  <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
                  <span className="text-muted-foreground">Backend Offline (Run uvicorn)</span>
                  <button
                    onClick={checkBackendHealth}
                    className="ml-1 underline text-primary cursor-pointer hover:text-primary/80"
                  >
                    Retry
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Phase 1 Capability Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          onClick={onNavigateToImport}
          className="group rounded-lg border border-border bg-card p-6 shadow-xs hover:border-primary/50 transition-all cursor-pointer space-y-3"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
            <FileUp className="h-5 w-5" />
          </div>
          <h3 className="font-semibold text-base text-foreground">1. Excel Parsing & Validation</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Upload `.xlsx` files with employee recognition records (`employee_name`, `designation`, `branch`, `award_name`). Review row-level validation alerts and duplicate detection.
          </p>
        </div>

        <div
          onClick={onNavigateToTemplates}
          className="group rounded-lg border border-border bg-card p-6 shadow-xs hover:border-primary/50 transition-all cursor-pointer space-y-3"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
            <FileSpreadsheet className="h-5 w-5" />
          </div>
          <h3 className="font-semibold text-base text-foreground">2. Template Inspector</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Upload KONE master newspaper PowerPoint templates (`.pptx`). Analyze slide counts, dimensions, text frames, and shape layout metadata without modifying the original template.
          </p>
        </div>
      </div>
    </div>
  );
}
