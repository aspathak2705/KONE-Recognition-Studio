import { FolderKanban, Info } from "lucide-react";

export function RecognitionProjects() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Recognition Projects</h2>
          <p className="text-xs text-muted-foreground">
            Manage quarterly recognition batches and generated presentations.
          </p>
        </div>
      </div>

      {/* Scope banner */}
      <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/40 p-4 text-xs text-muted-foreground">
        <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-foreground">Phase 0 Scope Boundary</p>
          <p className="mt-0.5">
            Project management and file processing workflows are intentionally deferred to Phase 1.
            Excel input upload and PowerPoint generation endpoints will be attached here.
          </p>
        </div>
      </div>

      {/* Empty State */}
      <div className="rounded-lg border border-dashed border-border bg-card p-12 text-center">
        <div className="mx-auto max-w-sm space-y-3">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <FolderKanban className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-foreground">Project Management Ready</h3>
            <p className="text-xs text-muted-foreground">
              Once Phase 1 opens, created recognition projects will be listed here.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
