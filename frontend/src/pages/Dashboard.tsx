import { useEffect, useState } from "react";
import { FileUp, Award, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

interface DashboardProps {
  onNavigateToProjects: () => void;
}

export function Dashboard({ onNavigateToProjects }: DashboardProps) {
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
            Internal Enterprise Tool
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            KONE Recognition Automation
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Create quarterly employee recognition presentations from structured employee data.
            Automate high-impact poster generation using KONE-approved newspaper-style layouts.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={onNavigateToProjects}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors cursor-pointer"
            >
              <FileUp className="h-4 w-4" />
              View Recognition Projects
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

      {/* Empty State / Workflow Introduction */}
      <div className="rounded-lg border border-dashed border-border bg-card/50 p-10 text-center">
        <div className="mx-auto max-w-md space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Award className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground">No Active Recognition Projects</h3>
            <p className="text-xs text-muted-foreground leading-normal">
              Excel parsing and presentation generation workflows will be enabled in Phase 1 following template analysis.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
