import { CheckCircle2, AlertTriangle, Copy } from "lucide-react";

interface ValidationSummaryProps {
  totalRows: number;
  validRows: number;
  invalidRows: number;
  duplicateRows: number;
}

export function ValidationSummary({
  totalRows,
  validRows,
  invalidRows,
  duplicateRows,
}: ValidationSummaryProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">Total Rows</p>
        <p className="text-2xl font-bold text-foreground mt-1">{totalRows}</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>Valid Rows</span>
        </div>
        <p className="text-2xl font-bold text-emerald-600 mt-1">{validRows}</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-1.5 text-xs font-medium text-amber-600">
          <AlertTriangle className="h-4 w-4" />
          <span>Invalid Rows</span>
        </div>
        <p className="text-2xl font-bold text-amber-600 mt-1">{invalidRows}</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Copy className="h-4 w-4" />
          <span>Duplicates</span>
        </div>
        <p className="text-2xl font-bold text-foreground mt-1">{duplicateRows}</p>
      </div>
    </div>
  );
}
