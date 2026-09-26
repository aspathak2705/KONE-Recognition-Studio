import { useEffect, useState } from "react";
import { FileSpreadsheet, Plus, CheckCircle2, ArrowRight } from "lucide-react";
import { TemplateMetadata } from "../types/recognition";
import { fetchRegisteredTemplates } from "../services/api";

interface DashboardProps {
  onNavigateToCreate: () => void;
  onNavigateToTemplates: () => void;
}

export function Dashboard({ onNavigateToCreate, onNavigateToTemplates }: DashboardProps) {
  const [templates, setTemplates] = useState<TemplateMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchRegisteredTemplates(false)
      .then((data) => setTemplates(data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Hero / Welcome Banner */}
      <div className="rounded-lg border border-border bg-card p-8 shadow-xs">
        <div className="max-w-3xl space-y-4">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            KONE Recognition Studio
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Create quarterly employee recognition presentations from recognition data and reusable KONE master templates.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={onNavigateToCreate}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors cursor-pointer"
            >
              <Plus className="h-4 w-4" />
              Create Presentation
            </button>

            <button
              onClick={onNavigateToTemplates}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-xs hover:bg-muted/50 transition-colors cursor-pointer"
            >
              <FileSpreadsheet className="h-4 w-4 text-primary" />
              Manage Templates
            </button>
          </div>
        </div>
      </div>

      {/* Templates Summary Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <FileSpreadsheet className="h-4.5 w-4.5 text-primary" />
            Registered Templates Library
          </h3>
          <button
            onClick={onNavigateToTemplates}
            className="text-xs text-primary font-medium hover:underline flex items-center gap-1 cursor-pointer"
          >
            View All Templates <ArrowRight className="h-3 w-3" />
          </button>
        </div>

        {isLoading ? (
          <div className="p-6 text-xs text-muted-foreground text-center">Loading templates...</div>
        ) : templates.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center space-y-3">
            <p className="text-sm font-medium text-foreground">No Registered Master Templates</p>
            <p className="text-xs text-muted-foreground">
              Register a PowerPoint master template once in the Template Library to reuse across all future presentations.
            </p>
            <button
              onClick={onNavigateToTemplates}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" /> Add Master Template
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.slice(0, 3).map((tpl) => (
              <div
                key={tpl.template_id}
                onClick={onNavigateToCreate}
                className="p-4 rounded-lg border border-border bg-card hover:bg-muted/30 transition-all cursor-pointer space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-foreground">{tpl.name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">Version {tpl.current_version}</p>
                  </div>
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600">
                    <CheckCircle2 className="h-3 w-3" /> Ready
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
