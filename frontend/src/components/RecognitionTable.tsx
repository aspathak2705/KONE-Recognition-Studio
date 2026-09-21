import { RecognitionRecord } from "../types/recognition";
import { CheckCircle2, AlertCircle } from "lucide-react";

interface RecognitionTableProps {
  records: RecognitionRecord[];
}

export function RecognitionTable({ records }: RecognitionTableProps) {
  if (records.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <h3 className="font-semibold text-sm text-foreground">Extracted Recognition Records</h3>
        <span className="text-xs text-muted-foreground">{records.length} records parsed</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-foreground">
          <thead className="bg-muted/50 border-b border-border text-muted-foreground font-medium uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Row</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Employee Name</th>
              <th className="px-4 py-3">Designation</th>
              <th className="px-4 py-3">Branch</th>
              <th className="px-4 py-3">Award Name</th>
              <th className="px-4 py-3">Validation Errors</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {records.map((rec) => (
              <tr
                key={rec.row_number}
                className={rec.is_valid ? "hover:bg-muted/20" : "bg-amber-500/5 hover:bg-amber-500/10"}
              >
                <td className="px-4 py-3 font-mono text-muted-foreground">{rec.row_number}</td>
                <td className="px-4 py-3">
                  {rec.is_valid ? (
                    <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Valid
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-amber-600 font-medium">
                      <AlertCircle className="h-3.5 w-3.5" /> Invalid
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 font-medium">{rec.employee_name || "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{rec.designation || "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{rec.branch || "—"}</td>
                <td className="px-4 py-3 font-medium text-primary">{rec.award_name || "—"}</td>
                <td className="px-4 py-3">
                  {rec.errors.length > 0 ? (
                    <div className="space-y-0.5">
                      {rec.errors.map((err, i) => (
                        <p key={i} className="text-amber-600 text-[11px]">
                          • {err}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted-foreground/60">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
