import { useEffect, useState } from "react";
import { FileUpload } from "../components/FileUpload";
import { ValidationSummary } from "../components/ValidationSummary";
import { RecognitionTable } from "../components/RecognitionTable";
import { ExcelValidationResponse, SchemaResponse } from "../types/recognition";
import { fetchExcelSchema, uploadAndValidateExcel } from "../services/api";
import { FileSpreadsheet, AlertCircle, CheckCircle2 } from "lucide-react";

export function ExcelImport() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [validationResult, setValidationResult] = useState<ExcelValidationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchExcelSchema()
      .then((data) => setSchema(data))
      .catch((err) => setErrorMsg(err.message));
  }, []);

  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const res = await uploadAndValidateExcel(file);
      setValidationResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to parse and validate Excel file.");
      setValidationResult(null);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Excel Data Import</h2>
          <p className="text-xs text-muted-foreground">
            Upload employee recognition details in `.xlsx` format for automated validation.
          </p>
        </div>
      </div>

      {/* Upload Control */}
      <div className="space-y-4">
        <FileUpload
          accept=".xlsx"
          acceptLabel="Microsoft Excel Workbooks (.xlsx) up to 20MB"
          onFileSelect={handleFileSelect}
          isLoading={isProcessing}
        />

        {errorMsg && (
          <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Validation Results */}
      {validationResult && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-foreground">Validation Results</h3>
            {validationResult.valid ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600">
                <CheckCircle2 className="h-4 w-4" /> Ready for Generation
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600">
                <AlertCircle className="h-4 w-4" /> Requires Correction
              </span>
            )}
          </div>

          <ValidationSummary
            totalRows={validationResult.total_rows}
            validRows={validationResult.valid_rows}
            invalidRows={validationResult.invalid_rows}
            duplicateRows={validationResult.duplicate_rows}
          />

          <RecognitionTable records={validationResult.records} />
        </div>
      )}

      {/* Schema Reference Guide */}
      {schema && (
        <div className="rounded-lg border border-border bg-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <FileSpreadsheet className="h-4 w-4 text-primary" />
            <span>Expected Excel Specification</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {schema.required_fields.map((f) => (
              <div key={f.field_name} className="p-3 rounded-md bg-muted/40 border border-border space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-primary">{f.canonical_header}</span>
                  <span className="text-[10px] uppercase font-semibold text-emerald-600 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                    Required
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{f.description}</p>
                <p className="text-[11px] text-muted-foreground/80">
                  Aliases: <code className="text-foreground">{f.accepted_aliases.join(", ")}</code>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
