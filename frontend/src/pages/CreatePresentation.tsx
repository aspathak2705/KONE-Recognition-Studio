import React, { useState, useRef } from "react";
import {
  PhotoMatchingSessionResponse,
  PhotoMatchStatus,
} from "../types/photo_matching";
import { AwardGroup, DynamicGenerationResponse } from "../types/dynamic_presentation";

type WorkflowStep = "upload" | "review_photos" | "review_groups" | "preview";

export function CreatePresentation() {
  const [step, setStep] = useState<WorkflowStep>("upload");
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [photoFiles, setPhotoFiles] = useState<File[]>([]);
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [session, setSession] = useState<PhotoMatchingSessionResponse | null>(null);
  const [awardGroups, setAwardGroups] = useState<AwardGroup[]>([]);
  const [generationResult, setGenerationResult] = useState<DynamicGenerationResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
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

  const handleProcessUpload = async () => {
    if (!excelFile) {
      setErrorMsg("Please select the employee recognition Excel workbook.");
      return;
    }
    if (photoFiles.length === 0 && !zipFile) {
      setErrorMsg("Please select a photo directory or upload a ZIP archive of employee photographs.");
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
      setStep("review_photos");
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

  const handleFinalizeAndProceedToGroups = async () => {
    if (!session) return;
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/photos/${session.session_id}/finalize`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Cannot finalize dataset.");
      }

      // Group employees by award category locally for review
      const groupsMap: Record<string, { award_name: string; employees: any[] }> = {};
      session.employee_matches.forEach((emp) => {
        const award = (emp.award_name || "Uncategorized").trim();
        if (!groupsMap[award]) {
          groupsMap[award] = { award_name: award, employees: [] };
        }
        groupsMap[award].employees.push(emp);
      });

      const groupsArr: AwardGroup[] = Object.values(groupsMap).map((g) => ({
        award_name: g.award_name,
        normalized_award_name: g.award_name.toLowerCase(),
        employee_count: g.employees.length,
        employees: g.employees,
      }));

      setAwardGroups(groupsArr);
      setStep("review_groups");
    } catch (err: any) {
      setErrorMsg(`Finalization blocked: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGeneratePresentation = async () => {
    if (!session) return;
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/photos/${session.session_id}/generate-presentation`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate dynamic presentation.");
      }
      const data: DynamicGenerationResponse = await res.json();
      setGenerationResult(data);
      setStep("preview");
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsProcessing(false);
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
            Ambiguous
          </span>
        );
      case "DUPLICATE_EMPLOYEE_NAME":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
            Name Conflict
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
      {/* Header and Stepper */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            KONE Recognition Studio — Dynamic Presentation Generator
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Template-free, data-driven recognition presentations with automatic photograph matching.
          </p>
        </div>

        {/* Stepper indicator */}
        <div className="mt-4 md:mt-0 flex items-center space-x-2 text-xs font-medium">
          <span className={`px-2 py-1 rounded ${step === "upload" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
            1. Upload
          </span>
          <span>→</span>
          <span className={`px-2 py-1 rounded ${step === "review_photos" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
            2. Match Photos
          </span>
          <span>→</span>
          <span className={`px-2 py-1 rounded ${step === "review_groups" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
            3. Award Groups
          </span>
          <span>→</span>
          <span className={`px-2 py-1 rounded ${step === "preview" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
            4. Preview & Download
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {errorMsg}
        </div>
      )}

      {/* STEP 1: UPLOAD */}
      {step === "upload" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="border border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
            <h3 className="text-base font-semibold text-gray-800 mb-2">
              1. Employee Recognition Excel (.xlsx)
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Columns: Employee Name, Award Name (Required). Designation, Branch (Optional).
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
                ✓ {excelFile.name} ({(excelFile.size / 1024).toFixed(1)} KB)
              </div>
            )}
          </div>

          <div className="border border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
            <h3 className="text-base font-semibold text-gray-800 mb-2">
              2. Employee Photographs (Folder or ZIP)
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Select an entire directory of photos named "Employee Name.jpg/png" or a ZIP folder.
            </p>
            <div className="flex justify-center gap-3">
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
                ✓ Selected {photoFiles.length} photo(s) from directory
              </div>
            )}
            {zipFile && (
              <div className="mt-3 text-xs text-green-700 font-medium">
                ✓ Selected ZIP: {zipFile.name} ({(zipFile.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
            )}
          </div>

          <div className="col-span-full pt-4 border-t flex justify-end">
            <button
              onClick={handleProcessUpload}
              disabled={isProcessing || !excelFile || (photoFiles.length === 0 && !zipFile)}
              className="px-6 py-2.5 bg-blue-600 text-white rounded font-semibold text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {isProcessing ? "Processing & Matching Photos..." : "Match Photos & Review →"}
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: REVIEW PHOTOS */}
      {step === "review_photos" && session && (
        <div className="space-y-6">
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

            <div className="flex gap-3">
              <button
                onClick={() => setStep("upload")}
                className="px-4 py-2 border rounded text-sm text-gray-700 hover:bg-gray-50"
              >
                ← Back to Upload
              </button>
              <button
                onClick={handleFinalizeAndProceedToGroups}
                disabled={!session.is_dataset_ready || isProcessing}
                className="px-5 py-2 bg-blue-600 text-white rounded font-medium text-sm hover:bg-blue-700 disabled:opacity-40"
              >
                {isProcessing
                  ? "Finalizing..."
                  : session.is_dataset_ready
                  ? "Proceed to Award Groups →"
                  : `Blocked (${attentionMatches.length} issues remaining)`}
              </button>
            </div>
          </div>

          {activeTab === "unmatched" ? (
            <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200 p-6">
              <h4 className="text-sm font-semibold text-gray-800 mb-4">
                Uploaded Photographs Not Associated With Any Employee
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4">
                {session.unmatched_files.map((file) => (
                  <div key={file.file_id} className="border rounded p-2 text-center bg-gray-50 flex flex-col items-center">
                    <img
                      src={file.preview_url}
                      alt={file.original_filename}
                      className="w-20 h-20 object-cover rounded mb-2 border"
                    />
                    <div className="text-xs font-medium text-gray-800 truncate w-full" title={file.original_filename}>
                      {file.original_filename}
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
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50 text-left text-xs font-semibold text-gray-600 uppercase">
                  <tr>
                    <th className="px-4 py-3">Photo</th>
                    <th className="px-4 py-3">Employee Details</th>
                    <th className="px-4 py-3">Award Category</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Associated Photo</th>
                    <th className="px-4 py-3 text-right">Actions / Resolve</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {displayedMatches.map((match) => (
                    <tr key={match.employee_record_index} className={match.is_resolved ? "hover:bg-gray-50" : "bg-red-50/40"}>
                      <td className="px-4 py-3">
                        {match.assigned_file ? (
                          <img
                            src={match.assigned_file.preview_url}
                            alt={match.employee_name}
                            className="w-12 h-12 object-cover rounded border border-gray-300"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded bg-gray-100 border border-dashed text-xs flex items-center justify-center text-gray-400">
                            No Photo
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900">{match.employee_name}</div>
                        <div className="text-xs text-gray-500">
                          {match.designation || "—"} {match.branch ? `• ${match.branch}` : ""}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-700">{match.award_name}</td>
                      <td className="px-4 py-3">
                        {statusBadge(match.match_status, match.is_reused_override)}
                        {match.issue_message && (
                          <div className="text-xs text-red-600 mt-1 max-w-xs">{match.issue_message}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">
                        {match.assigned_file ? match.assigned_file.original_filename : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <select
                          className="text-xs border rounded p-1 bg-white"
                          value={match.assigned_file ? match.assigned_file.file_id : ""}
                          onChange={(e) =>
                            handleResolve(match.employee_record_index, e.target.value ? e.target.value : null)
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
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* STEP 3: REVIEW AWARD GROUPS */}
      {step === "review_groups" && session && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Award Category Grouping Summary</h3>
            <p className="text-sm text-gray-500 mb-4">
              All {session.total_employees} employees have been grouped into {awardGroups.length} award categories.
              Dynamic presentation engine will automatically paginate categories and optimize card density.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {awardGroups.map((g) => (
                <div key={g.normalized_award_name} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold text-gray-800 text-sm">{g.award_name}</span>
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
                      {g.employee_count} {g.employee_count === 1 ? "Employee" : "Employees"}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 line-clamp-2">
                    {g.employees.map((e) => e.employee_name).join(", ")}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setStep("review_photos")}
              className="px-4 py-2 border rounded text-sm text-gray-700 hover:bg-gray-50"
            >
              ← Back to Photo Review
            </button>
            <button
              onClick={handleGeneratePresentation}
              disabled={isProcessing}
              className="px-6 py-2.5 bg-green-600 text-white rounded font-semibold text-sm hover:bg-green-700 disabled:opacity-50"
            >
              {isProcessing ? "Generating Presentation..." : "Generate Editable PowerPoint Presentation →"}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: PREVIEW & DOWNLOAD */}
      {step === "preview" && generationResult && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-lg shadow border border-gray-200 flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  ✓ Verified Ready for Download
                </span>
                <span className="text-xs text-gray-500 font-mono">
                  ID: {generationResult.generation_id.slice(0, 8)}...
                </span>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mt-2">
                Recognition Presentation Ready
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {generationResult.slide_count} slides generated across {generationResult.award_categories_count} award categories for {generationResult.total_employees} recognized employees.
              </p>
            </div>

            <div className="mt-4 md:mt-0 flex gap-3">
              <button
                onClick={() => setStep("review_groups")}
                className="px-4 py-2 border rounded text-sm text-gray-700 hover:bg-gray-50"
              >
                Review Groups
              </button>
              <a
                href={generationResult.download_url}
                download
                className="px-6 py-2.5 bg-blue-600 text-white rounded font-semibold text-sm hover:bg-blue-700 inline-flex items-center gap-2"
              >
                <span>Download Editable PPTX</span>
              </a>
            </div>
          </div>

          {/* Rendered Slide Previews */}
          {generationResult.rendered_slide_urls.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
              <h3 className="text-base font-bold text-gray-900 mb-4">Generated Slide Previews</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {generationResult.rendered_slide_urls.map((url, sIdx) => (
                  <div key={url} className="border rounded shadow-sm overflow-hidden bg-gray-50">
                    <img src={url} alt={`Slide ${sIdx + 1}`} className="w-full h-auto object-cover border-b" />
                    <div className="p-2 text-xs font-semibold text-gray-600 text-center">
                      Slide {sIdx + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
