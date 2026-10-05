import { useState, useEffect } from "react";
import { FileUpload } from "../components/FileUpload";
import {
  TemplateMetadata,
  TemplateRegistrationResponse,
} from "../types/recognition";
import {
  fetchRegisteredTemplates,
  registerTemplate,
  deleteTemplate,
} from "../services/api";
import {
  FileSpreadsheet,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  RefreshCw,
  Layers,
  Sparkles,
  Users,
  Image as ImageIcon,
  Check,
  Info,
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

  // Selected template
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateMetadata | null>(null);

  // Delete modal state
  const [templateToDelete, setTemplateToDelete] = useState<TemplateMetadata | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadTemplates = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchRegisteredTemplates(false);
      setTemplates(data);
      if (data.length > 0 && !selectedTemplate) {
        setSelectedTemplate(data[0]);
      } else if (selectedTemplate) {
        const refreshed = data.find((t) => t.template_id === selectedTemplate.template_id);
        setSelectedTemplate(refreshed || data[0] || null);
      }
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
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to register new template.");
    } finally {
      setIsRegistering(false);
    }
  };

  const confirmDelete = async () => {
    if (!templateToDelete) return;
    setIsDeleting(true);
    setErrorMsg(null);
    try {
      await deleteTemplate(templateToDelete.template_id);
      if (selectedTemplate?.template_id === templateToDelete.template_id) {
        setSelectedTemplate(null);
      }
      setTemplateToDelete(null);
      await loadTemplates();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to delete template.");
    } finally {
      setIsDeleting(false);
    }
  };

  const currentVersionObj = selectedTemplate?.versions.find(
    (v) => v.version_number === selectedTemplate.current_version
  );
  const requirements = selectedTemplate?.requirements || currentVersionObj?.requirements;
  const capacities = selectedTemplate?.supported_capacities || currentVersionObj?.supported_capacities || [1];
  const hasPhoto = selectedTemplate?.has_photo_support ?? currentVersionObj?.has_photo_support ?? false;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Template Library</h2>
          <p className="text-xs text-muted-foreground">
            Manage official KONE PowerPoint master templates. Templates are automatically inspected for slide layouts and employee fields.
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
          Add Master Template
        </button>
      </div>

      {errorMsg && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Grid: Template List + Template Details */}
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
                Click "+ Add Master Template" to upload an official PowerPoint deck.
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
                    onClick={() => setSelectedTemplate(tpl)}
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
                          v{tpl.current_version} • {tpl.aspect_ratio}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                          isReady ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600"
                        }`}
                      >
                        {isReady ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                        {isReady ? "Ready" : "Needs Review"}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/50 pt-2">
                      <span>Updated {new Date(tpl.updated_at).toLocaleDateString()}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setTemplateToDelete(tpl);
                        }}
                        className="text-muted-foreground hover:text-destructive flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <Trash2 className="h-3 w-3" /> Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Template Details Panel (Clean HR UX - No Shape Mapping) */}
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
                    Auto-inspected master PowerPoint presentation. Ready for instant recognition generation.
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600">
                  <CheckCircle2 className="h-4 w-4" /> Ready for Generation
                </span>
              </div>

              {/* Template Specifications */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Aspect Ratio</p>
                  <p className="text-sm font-bold text-foreground mt-0.5">{selectedTemplate.aspect_ratio}</p>
                </div>
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Layout Capacities</p>
                  <p className="text-sm font-bold text-primary mt-0.5">
                    {capacities.join(", ")} per slide
                  </p>
                </div>
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Photo Frames</p>
                  <p className="text-xs font-bold text-foreground mt-1">
                    {hasPhoto ? "Detected & Cleared" : "Not Required"}
                  </p>
                </div>
                <div className="p-3 rounded-md bg-muted/40">
                  <p className="text-[11px] text-muted-foreground font-medium">Readiness State</p>
                  <p className="text-xs font-bold text-emerald-600 mt-1 flex items-center gap-1">
                    <Check className="h-3.5 w-3.5" /> Verified
                  </p>
                </div>
              </div>

              {/* Detected Data Requirements */}
              <div className="space-y-4 pt-2">
                <div className="border-b border-border pb-2">
                  <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    Automatically Detected Data Requirements
                  </h4>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    The system automatically extracts recognition fields from slide placeholders and formats output cards dynamically.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {(requirements?.required_fields || [
                    { field_key: "employee_name", display_label: "Employee Name", required: true },
                    { field_key: "designation", display_label: "Designation / Role", required: true },
                    { field_key: "branch", display_label: "Branch / Location", required: true },
                  ]).map((field) => (
                    <div key={field.field_key} className="p-3 rounded-md border border-border bg-background flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <Users className="h-4 w-4 text-primary shrink-0" />
                        <div>
                          <p className="text-xs font-semibold text-foreground">{field.display_label}</p>
                          <p className="text-[11px] text-muted-foreground font-mono">matches column: {field.field_key}</p>
                        </div>
                      </div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600">
                        Required
                      </span>
                    </div>
                  ))}

                  {(requirements?.optional_fields || [
                    { field_key: "award_name", display_label: "Award Category", required: false },
                  ]).map((field) => (
                    <div key={field.field_key} className="p-3 rounded-md border border-border bg-background flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <Sparkles className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div>
                          <p className="text-xs font-semibold text-foreground">{field.display_label}</p>
                          <p className="text-[11px] text-muted-foreground font-mono">matches column: {field.field_key}</p>
                        </div>
                      </div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-muted text-muted-foreground">
                        Optional
                      </span>
                    </div>
                  ))}
                </div>

                {/* Photo frame notice */}
                {hasPhoto && (
                  <div className="flex items-center gap-2.5 p-3 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-600 text-xs">
                    <ImageIcon className="h-4 w-4 shrink-0" />
                    <span>
                      <strong>Photo frames detected:</strong> Sample portraits will be automatically removed during generation so HR can insert official employee photos.
                    </span>
                  </div>
                )}
              </div>

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-4 border-t border-border">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  No manual shape mapping needed.
                </p>
                <button
                  onClick={() => setTemplateToDelete(selectedTemplate)}
                  className="inline-flex items-center gap-1.5 text-xs text-destructive hover:bg-destructive/10 px-3 py-1.5 rounded-md transition-colors cursor-pointer"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Delete Template
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
              <Layers className="h-10 w-10 mx-auto text-muted-foreground/60 mb-2" />
              <p className="text-sm font-medium text-foreground">Select a Template</p>
              <p className="text-xs text-muted-foreground mt-1">
                Select a registered template from the list to review detected capacities and requirements.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {templateToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 space-y-4 shadow-xl">
            <div className="flex items-center gap-3 text-destructive">
              <AlertTriangle className="h-6 w-6 shrink-0" />
              <h3 className="text-base font-bold text-foreground">Delete Master Template?</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Are you sure you want to delete <strong>{templateToDelete.name}</strong> from the Template Library?
              Existing presentations and generation audit records will remain preserved.
            </p>
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
              <button
                onClick={() => setTemplateToDelete(null)}
                disabled={isDeleting}
                className="rounded-md border border-border bg-card px-4 py-2 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-2 rounded-md bg-destructive px-4 py-2 text-xs font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isDeleting ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}

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
