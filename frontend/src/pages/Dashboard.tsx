import { Plus, Award, UploadCloud, Users, Sparkles } from "lucide-react";

interface DashboardProps {
  onNavigateToCreate: () => void;
}

export function Dashboard({ onNavigateToCreate }: DashboardProps) {
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

      {/* Workflow Steps Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
