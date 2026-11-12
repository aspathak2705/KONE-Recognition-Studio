import React, { useState, useRef } from "react";
import {
  PhotoMatchingSessionResponse,
  EmployeePhotoMatch,
  PhotoMatchStatus,
  PhotoFileMetadata,
} from "../types/photo_matching";

export function CreatePresentation() {
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [photoFiles, setPhotoFiles] = useState<File[]>([]);
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [session, setSession] = useState<PhotoMatchingSessionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isFinalized, setIsFinalized] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "attention" | "unmatched">("all");

  const dirInputRef = useRef<HTMLInputElement>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);

  const handleDirectorySelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArr = Array.from(e.target.files).filter((f) =>
        /\.(jpe?g|png|webp)$/i.test(f.name)
      );
      setPhotoFiles(filesArr);
      setZipFile(null);
    }
  };

  const handleZipSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setZipFile(e.target.files[0]);
      setPhotoFiles([]);
    }
  };

  const handleProcess = async () => {
    if (!excelFile) {
      setErrorMsg("Please upload the employee recognition Excel workbook.");
      return;
    }
    if (photoFiles.length === 0 && !zipFile) {
      setErrorMsg("Please select a photographs folder or upload a ZIP archive of photographs.");
      return;
    }

    setIsProcessing(true);
    setErrorMsg(null);

    const formData = new FormData();
    formData.append("excel_file", excelFile);
    if (zipFile) {
      formData.append("photo_zip", zipFile);
    } else {
      photoFiles.forEach((f) => formData.append("photo_files", f));
    }

    try {
      const res = await fetch("/api/photos/process-dataset", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to process dataset.");
      }
      const data: PhotoMatchingSessionResponse = await res.json();
      setSession(data);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResolve = async (
    employeeIndex: number,
    fileId: string | null,
    confirmReuse: boolean = false
  ) => {
    if (!session) return;
    try {
      const res = await fetch(`/api/photos/${session.session_id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employee_record_index: employeeIndex,
          file_id: fileId,
          confirm_reuse: confirmReuse,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        if (err.detail && err.detail.includes("CONFIRMATION_REQUIRED")) {
          const userConfirmed = window.confirm(
            `${err.detail}\n\nDo you want to confirm explicit reuse of this photograph for multiple employees?`
          );
          if (userConfirmed) {
            await handleResolve(employeeIndex, fileId, true);
          }
          return;
        }
        throw new Error(err.detail || "Failed to resolve association.");
      }

      const updated: PhotoMatchingSessionResponse = await res.json();
      setSession(updated);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleFinalize = async () => {
    if (!session) return;
    try {
      const res = await fetch(`/api/photos/${session.session_id}/finalize`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Cannot finalize dataset.");
      }
      setIsFinalized(true);
      alert("Dataset verified and ready for Phase 2 presentation generation!");
    } catch (err: any) {
      alert(`Finalization blocked: ${err.message}`);
    }
  };

  const statusBadge = (status: PhotoMatchStatus, isReused: boolean) => {
    switch (status) {
      case "MATCHED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
            Matched {isReused ? "(Reused)" : ""}
          </span>
        );
      case "MISSING":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
            Missing
          </span>
        );
      case "AMBIGUOUS":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
            Ambiguous (Multiple Files)
          </span>
        );
      case "DUPLICATE_EMPLOYEE_NAME":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
            Duplicate Name Conflict
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
            {status}
          </span>
        );
    }
  };

  const attentionMatches = session
    ? session.employee_matches.filter((m) => m.match_status !== "MATCHED" || !m.assigned_file)
    : [];

  const displayedMatches = session
    ? activeTab === "attention"
      ? attentionMatches
      : session.employee_matches
    : [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Employee Recognition Studio — Input & Photo Matching
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload employee recognition records and photo folder to intelligently match photographs.
        </p>
      </div>

      {errorMsg && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {errorMsg}
        </div>
      )}

      {!session ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-lg shadow border border-gray-200">
          {/* Step 1: Excel Upload */}
          <div className="border border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
            <h3 className="text-base font-semibold text-gray-800 mb-2">
              1. Employee Recognition Excel
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Required headers: Employee Name, Award Name. Optional: Designation, Branch.
            </p>
            <input
              type="file"
              ref={excelInputRef}
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => e.target.files && setExcelFile(e.target.files[0])}
            />
            <button
              type="button"
              onClick={() => excelInputRef.current?.click()}
              className="px-4 py-2 bg-blue-600 text-white rounded font-medium text-sm hover:bg-blue-700"
            >
              Select Excel File
            </button>
            {excelFile && (
              <div className="mt-3 text-xs text-green-700 font-medium">
                Selected: {excelFile.name} ({(excelFile.size / 1024).toFixed(1)} KB)
              </div>
            )}
          </div>

          {/* Step 2: Photo Folder Upload */}
          <div className="border border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
            <h3 className="text-base font-semibold text-gray-800 mb-2">
              2. Employee Photographs Folder
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Select an entire directory of photos named "Employee Name.jpg/png" or a ZIP archive.
            </p>
            <div className="flex justify-center gap-3">
              {/* Directory input */}
              <input
                type="file"
                ref={dirInputRef}
                multiple
                // @ts-ignore
                webkitdirectory=""
                // @ts-ignore
                directory=""
                className="hidden"
                onChange={handleDirectorySelect}
              />
              <button
                type="button"
                onClick={() => dirInputRef.current?.click()}
                className="px-4 py-2 bg-gray-800 text-white rounded font-medium text-sm hover:bg-gray-900"
              >
                Select Photo Folder
              </button>

              {/* ZIP fallback */}
              <input
                type="file"
                ref={zipInputRef}
                accept=".zip"
                className="hidden"
                onChange={handleZipSelect}
              />
              <button
                type="button"
                onClick={() => zipInputRef.current?.click()}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded font-medium text-sm hover:bg-gray-300"
              >
                Upload ZIP Archive
              </button>
            </div>
            {photoFiles.length > 0 && (
              <div className="mt-3 text-xs text-green-700 font-medium">
                Selected {photoFiles.length} photo(s) from folder
              </div>
            )}
            {zipFile && (
              <div className="mt-3 text-xs text-green-700 font-medium">
                Selected ZIP: {zipFile.name} ({(zipFile.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
            )}
          </div>

          <div className="col-span-full pt-4 border-t flex justify-end">
            <button
              onClick={handleProcess}
              disabled={isProcessing || !excelFile || (photoFiles.length === 0 && !zipFile)}
              className="px-6 py-2.5 bg-blue-600 text-white rounded font-semibold text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {isProcessing ? "Processing & Matching Photos..." : "Match Photos & Review"}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 bg-white p-4 rounded-lg shadow border border-gray-200 text-center">
            <div className="p-2">
              <div className="text-xl font-bold text-gray-800">{session.total_employees}</div>
              <div className="text-xs text-gray-500 uppercase">Total Employees</div>
            </div>
            <div className="p-2">
              <div className="text-xl font-bold text-green-600">{session.matched_count}</div>
              <div className="text-xs text-gray-500 uppercase">Matched</div>
            </div>
            <div className="p-2">
              <div className="text-xl font-bold text-red-600">{session.missing_count}</div>
              <div className="text-xs text-gray-500 uppercase">Missing</div>
            </div>
            <div className="p-2">
              <div className="text-xl font-bold text-yellow-600">{session.ambiguous_count}</div>
              <div className="text-xs text-gray-500 uppercase">Ambiguous</div>
            </div>
            <div className="p-2">
              <div className="text-xl font-bold text-orange-600">{session.duplicate_name_count}</div>
              <div className="text-xs text-gray-500 uppercase">Name Conflicts</div>
            </div>
            <div className="p-2">
              <div className="text-xl font-bold text-gray-600">{session.unmatched_files_count}</div>
              <div className="text-xs text-gray-500 uppercase">Unmatched Photos</div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex justify-between items-center border-b border-gray-200">
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab("all")}
                className={`py-2 px-3 text-sm font-medium border-b-2 ${
                  activeTab === "all"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                All Employees ({session.employee_matches.length})
              </button>
              <button
                onClick={() => setActiveTab("attention")}
                className={`py-2 px-3 text-sm font-medium border-b-2 ${
                  activeTab === "attention"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Needs Attention ({attentionMatches.length})
              </button>
              <button
                onClick={() => setActiveTab("unmatched")}
                className={`py-2 px-3 text-sm font-medium border-b-2 ${
                  activeTab === "unmatched"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Unmatched Files ({session.unmatched_files.length})
              </button>
            </div>

            <div>
              <button
                onClick={handleFinalize}
                disabled={!session.is_dataset_ready || isFinalized}
                className="px-5 py-2 bg-green-600 text-white rounded font-medium text-sm hover:bg-green-700 disabled:opacity-40"
              >
                {isFinalized
                  ? "✓ Dataset Finalized"
                  : session.is_dataset_ready
                  ? "Finalize Dataset for Presentation"
                  : `Blocked (${attentionMatches.length} issues remaining)`}
              </button>
            </div>
          </div>

          {/* Table / Review List */}
          {activeTab === "unmatched" ? (
            <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
              <div className="p-4 bg-gray-50 border-b text-xs font-semibold text-gray-600 uppercase">
                Uploaded Photographs Not Associated With Any Employee
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4 p-4">
                {session.unmatched_files.map((file) => (
                  <div
                    key={file.file_id}
                    className="border rounded p-2 text-center bg-gray-50 flex flex-col items-center"
                  >
                    <img
                      src={file.preview_url}
                      alt={file.original_filename}
                      className="w-20 h-20 object-cover rounded mb-2 border"
                    />
                    <div className="text-xs font-medium text-gray-800 truncate w-full" title={file.original_filename}>
                      {file.original_filename}
                    </div>
                    <div className="text-xs text-gray-500">
                      {file.width}×{file.height} | {(file.file_size_bytes / 1024).toFixed(0)} KB
                    </div>
                  </div>
                ))}
                {session.unmatched_files.length === 0 && (
                  <div className="col-span-full py-8 text-center text-sm text-gray-500">
                    No unmatched photograph files.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 text-left text-xs font-semibold text-gray-600 uppercase">
                  <tr>
                    <th className="px-4 py-3">Photo</th>
                    <th className="px-4 py-3">Employee Details</th>
                    <th className="px-4 py-3">Award Category</th>
                    <th className="px-4 py-3">Matching Status</th>
                    <th className="px-4 py-3">Photo Filename</th>
                    <th className="px-4 py-3 text-right">Actions / Resolve</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 text-sm">
                  {displayedMatches.map((match) => (
                    <tr
                      key={match.employee_record_index}
                      className={match.is_resolved ? "hover:bg-gray-50" : "bg-red-50/40 hover:bg-red-50"}
                    >
                      {/* Photo Thumbnail */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        {match.assigned_file ? (
                          <img
                            src={match.assigned_file.preview_url}
                            alt={match.employee_name}
                            className="w-12 h-12 object-cover rounded border border-gray-300"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded bg-gray-100 border border-dashed border-gray-300 flex items-center justify-center text-xs text-gray-400">
                            No Photo
                          </div>
                        )}
                      </td>

                      {/* Employee Info */}
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900">{match.employee_name}</div>
                        <div className="text-xs text-gray-500">
                          {match.designation || "—"} {match.branch ? `• ${match.branch}` : ""}
                        </div>
                      </td>

                      {/* Award */}
                      <td className="px-4 py-3 text-gray-700">{match.award_name}</td>

                      {/* Status */}
                      <td className="px-4 py-3">
                        <div>{statusBadge(match.match_status, match.is_reused_override)}</div>
                        {match.issue_message && (
                          <div className="text-xs text-red-600 mt-1 max-w-xs">{match.issue_message}</div>
                        )}
                      </td>

                      {/* Associated Filename */}
                      <td className="px-4 py-3 text-xs font-mono text-gray-600">
                        {match.assigned_file ? match.assigned_file.original_filename : "—"}
                      </td>

                      {/* Actions dropdown */}
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <select
                          className="text-xs border rounded p-1 bg-white"
                          value={match.assigned_file ? match.assigned_file.file_id : ""}
                          onChange={(e) =>
                            handleResolve(
                              match.employee_record_index,
                              e.target.value ? e.target.value : null
                            )
                          }
                        >
                          <option value="">-- Assign Photo --</option>
                          {session.all_valid_photos.map((p) => (
                            <option key={p.file_id} value={p.file_id}>
                              {p.original_filename}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                  {displayedMatches.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-sm text-gray-500">
                        No employees found for this view.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
