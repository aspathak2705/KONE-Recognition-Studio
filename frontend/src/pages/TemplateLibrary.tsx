import { useState, useEffect } from "react";
import { FileUpload } from "../components/FileUpload";
import {
  TemplateMetadata,
  TemplateRegistrationResponse,
  FieldMappingConfig,
} from "../types/recognition";
import {
  fetchRegisteredTemplates,
  registerTemplate,
  updateTemplateMapping,
  archiveTemplate,
} from "../services/api";
import {
  FileSpreadsheet,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Archive,
  RefreshCw,
  Layers,
  Settings2,
} from "lucide-react";

export function TemplateLibrary() {
  const [templates, setTemplates] = useState<TemplateMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modal / Add state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [regResult, setRegResult] = useState<TemplateRegistrationResponse | null>(null);

  // Selected template for inspection / mapping
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateMetadata | null>(null);
  const [editingMapping, setEditingMapping] = useState<FieldMappingConfig>({});
  const [isSavingMapping, setIsSavingMapping] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const loadTemplates = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchRegisteredTemplates(false);
      setTemplates(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load template library.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleRegister = async () => {
    if (!newTemplateName.trim() || !selectedFile) {
      setErrorMsg("Please provide both a template name and a PowerPoint (.pptx) file.");
      return;
    }
    setIsRegistering(true);
    setErrorMsg(null);
    try {
      const res = await registerTemplate(newTemplateName.trim(), selectedFile);
      setRegResult(res);
      await loadTemplates();
      setSelectedTemplate(res.template);
      if (res.active_version.mapping_config) {
        setEditingMapping(res.active_version.mapping_config);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to register new template.");
    } finally {
      setIsRegistering(false);
    }
  };

  const handleSaveMapping = async () => {
    if (!selectedTemplate) return;
    setIsSavingMapping(true);
    setSaveSuccessMsg(null);
    setErrorMsg(null);
    try {
      const updated = await updateTemplateMapping(selectedTemplate.template_id, editingMapping);
      setSelectedTemplate(updated);
      setSaveSuccessMsg("Mapping configuration saved successfully.");
      await loadTemplates();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save field mapping.");
    } finally {
      setIsSavingMapping(false);
    }
  };

  const handleArchive = async (tplId: string) => {
    if (!confirm("Are you sure you want to archive this template?")) return;
    try {
      await archiveTemplate(tplId);
      if (selectedTemplate?.template_id === tplId) {
        setSelectedTemplate(null);
      }
      await loadTemplates();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to archive template.");
    }
  };

  const availableShapes =
    selectedTemplate?.versions[0]?.inspection_data?.slides[0]?.text_shapes.map((s) => s.shape_name) || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Template Library</h2>
          <p className="text-xs text-muted-foreground">
            Register and manage reusable KONE PowerPoint master templates and shape mappings.
          </p>
        </div>
        <button
          onClick={() => {
            setShowAddModal(true);
            setRegResult(null);
            setNewTemplateName("");
            setSelectedFile(null);
            setErrorMsg(null);
          }}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          Add New Template
        </button>
      </div>

      {errorMsg && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Grid: Template List + Template Details/Mapping */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Templates List */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <FileSpreadsheet className="h-4 w-4 text-primary" />
            Registered Templates ({templates.length})
          </h3>

          {isLoading ? (
            <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Loading templates...
            </div>
          ) : templates.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border p-6 text-center space-y-2">
              <FileSpreadsheet className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm font-medium text-foreground">No Templates Registered</p>
              <p className="text-xs text-muted-foreground">
                Click "+ Add New Template" to upload a master PowerPoint template once.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((tpl) => {
                const isSelected = selectedTemplate?.template_id === tpl.template_id;
                const isReady = tpl.generation_readiness === "ready_for_generation";

                return (
                  <div
                    key={tpl.template_id}
                    onClick={() => {
                      setSelectedTemplate(tpl);
                      const currentV = tpl.versions.find((v) => v.version_number === tpl.current_version);
                      setEditingMapping(currentV?.mapping_config || {});
                      setSaveSuccessMsg(null);
                    }}
                    className={`p-4 rounded-lg border text-left cursor-pointer transition-all ${
                      isSelected
                        ? "border-primary bg-primary/5 shadow-xs"
                        : "border-border bg-card hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-bold text-sm text-foreground">{tpl.name}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Version {tpl.current_version} • {tpl.aspect_ratio}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                          isReady ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600"
                        }`}
                      >
                        {isReady ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                        {isReady ? "Ready" : "Mapping Needed"}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/50 pt-2">
                      <span>Updated {new Date(tpl.updated_at).toLocaleDateString()}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleArchive(tpl.template_id);
                        }}
                        className="text-muted-foreground hover:text-destructive flex items-center gap-1"
                      >
                        <Archive className="h-3 w-3" /> Archive
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Template Configuration Panel */}
        <div className="lg:col-span-2 space-y-6">
          {selectedTemplate ? (
            <div className="rounded-lg border border-border bg-card p-6 space-y-6">
              <div className="flex items-start justify-between border-b border-border pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-foreground">{selectedTemplate.name}</h3>
                    <span className="text-xs px-2 py-0.5 rounded bg-muted font-mono">
                      v{selectedTemplate.current_version}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Template ID: <span className="font-mono">{selectedTemplate.template_id}</span>
                  </p>
                </div>
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                    selectedTemplate.generation_readiness === "ready_for_generation"
                      ? "bg-emerald-500/10 text-emerald-600"
                      : "bg-amber-500/10 text-amber-600"
                  }`}
                >
                  {selectedTemplate.generation_readiness === "ready_for_generation" ? (
                    <>
                      <CheckCircle2 className="h-4 w-4" /> Ready for Presentation Generation
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-4 w-4" /> Mapping Incomplete
                    </>
                  )}
                </span>
              </div>

              {saveSuccessMsg && (
                <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 p-3 text-xs text-emerald-600 font-medium">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>{saveSuccessMsg}</span>
                </div>
              )}

              {/* Version History & Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Aspect Ratio</p>
                  <p className="text-sm font-bold text-foreground mt-0.5">{selectedTemplate.aspect_ratio}</p>
                </div>
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Versions</p>
                  <p className="text-sm font-bold text-primary mt-0.5">{selectedTemplate.versions.length}</p>
                </div>
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">File Hash</p>
                  <p className="text-xs font-mono text-foreground mt-0.5 truncate">
                    {selectedTemplate.file_hash.substring(0, 12)}...
                  </p>
                </div>
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Readiness State</p>
                  <p className="text-xs font-bold capitalize text-foreground mt-0.5">
                    {selectedTemplate.generation_readiness.replace(/_/g, " ")}
                  </p>
                </div>
              </div>

              {/* Shape Mapping Configuration */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Settings2 className="h-4 w-4 text-primary" />
                    Field Shape Mapping Configuration
                  </h4>
                  <button
                    onClick={handleSaveMapping}
                    disabled={isSavingMapping}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer"
                  >
                    {isSavingMapping ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                    Save Mapping
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { key: "employee_name", label: "Employee Name Shape" },
                    { key: "designation", label: "Designation Shape" },
                    { key: "branch", label: "Branch / Location Shape" },
                    { key: "award_name", label: "Award Name Shape" },
                  ].map((field) => {
                    const currentVal = (editingMapping as any)[field.key]?.shape_name || "";
                    return (
                      <div key={field.key} className="space-y-1.5 p-3 rounded-md border border-border bg-background">
                        <label className="text-xs font-medium text-foreground">{field.label}</label>
                        {availableShapes.length > 0 ? (
                          <select
                            value={currentVal}
                            onChange={(e) => {
                              const val = e.target.value;
                              setEditingMapping((prev) => ({
                                ...prev,
                                [field.key]: val ? { shape_name: val, required: true } : undefined,
                              }));
                            }}
                            className="w-full text-xs rounded-md border border-border bg-background p-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          >
                            <option value="">-- Select Shape --</option>
                            {availableShapes.map((s) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="text"
                            value={currentVal}
                            onChange={(e) => {
                              const val = e.target.value;
                              setEditingMapping((prev) => ({
                                ...prev,
                                [field.key]: val ? { shape_name: val, required: true } : undefined,
                              }));
                            }}
                            placeholder="Enter shape name (e.g. EmployeeName)"
                            className="w-full text-xs rounded-md border border-border bg-background p-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
              <Layers className="h-10 w-10 mx-auto text-muted-foreground/60 mb-2" />
              <p className="text-sm font-medium text-foreground">Select a Template</p>
              <p className="text-xs text-muted-foreground mt-1">
                Select a registered template from the list to view version history and configure shape mappings.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Add New Template Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-lg border border-border bg-card p-6 space-y-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Plus className="h-4 w-4 text-primary" /> Register New PowerPoint Master Template
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
              >
                ✕
              </button>
            </div>

            {regResult ? (
              <div className="space-y-4">
                <div className="p-4 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 text-xs space-y-1">
                  <p className="font-bold flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4" /> {regResult.message}
                  </p>
                  <p>Template ID: {regResult.template.template_id}</p>
                </div>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer"
                >
                  Done
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Template Name</label>
                  <input
                    type="text"
                    value={newTemplateName}
                    onChange={(e) => setNewTemplateName(e.target.value)}
                    placeholder="e.g. KONE Quarterly Recognition"
                    className="w-full text-xs rounded-md border border-border bg-background p-2.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Master PowerPoint File (.pptx)</label>
                  <FileUpload
                    accept=".pptx"
                    acceptLabel="Master PowerPoint presentation (.pptx)"
                    onFileSelect={(file) => setSelectedFile(file)}
                    isLoading={isRegistering}
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="rounded-md border border-border bg-card px-4 py-2 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRegister}
                    disabled={isRegistering || !newTemplateName.trim() || !selectedFile}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {isRegistering ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                    Register Template
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
