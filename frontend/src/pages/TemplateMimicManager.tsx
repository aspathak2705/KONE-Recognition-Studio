import React, { useState, useEffect, useRef } from "react";
import {
  UploadCloud,
  FileCheck,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Palette,
  Type,
  Layout,
  Sliders,
  ChevronRight,
} from "lucide-react";
import {
  TemplateMimicConfig,
  SlideLayoutConfig,
  VisualElementConfig,
  RoleCandidate,
} from "../types/template_mimic";

const API_BASE = "http://127.0.0.1:8000";

export function TemplateMimicManager() {
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateMimicConfig | null>(null);
  const [activeSlideIdx, setActiveSlideIdx] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedElement, setSelectedElement] = useState<VisualElementConfig | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchTemplates = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/templates/mimic`);
      if (res.ok) {
        const data = await res.json();
        if (data.length > 0 && !selectedTemplate) {
          setSelectedTemplate(data[0]);
        }
      }
    } catch {
      // Server may be offline or starting
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];

    setIsUploading(true);
    setErrorMsg(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/templates/mimic/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }
      setSelectedTemplate(data.config);
      setActiveSlideIdx(0);
      setSelectedElement(null);
      await fetchTemplates();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to analyze template.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleRoleUpdate = async (elemId: string, newRole: RoleCandidate) => {
    if (!selectedTemplate) return;
    try {
      const res = await fetch(`${API_BASE}/api/templates/mimic/${selectedTemplate.template_id}/role`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slide_index: activeSlideIdx,
          element_id: elemId,
          role: newRole,
          user_confirmed: true,
        }),
      });
      if (res.ok) {
        const updatedConfig = await res.json();
        setSelectedTemplate(updatedConfig);
        const updatedElem = updatedConfig.slides[activeSlideIdx].elements.find(
          (e: VisualElementConfig) => e.element_id === elemId
        );
        setSelectedElement(updatedElem || null);
      }
    } catch (err: any) {
      alert(`Failed to update role: ${err.message}`);
    }
  };

  const activeSlide: SlideLayoutConfig | undefined = selectedTemplate?.slides[activeSlideIdx];

  const getRoleBadge = (role: RoleCandidate) => {
    switch (role) {
      case "STATIC":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-700">STATIC</span>;
      case "CONTAINER":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-700">CARD CONTAINER</span>;
      case "REPLACEABLE_TEXT":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">REPLACEABLE TEXT</span>;
      case "REPLACEABLE_IMAGE":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-100 text-purple-800">REPLACEABLE PHOTO</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">UNCONFIGURED</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            Generic Template Mimic Engine (Phase 1)
          </div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Template Layout & Visual Style Analyzer
          </h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
            Upload custom PowerPoint (.pptx) master templates to analyze typography, colors, aspect ratio, and candidate content regions. Zero business or employee assumptions are imposed.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pptx"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 shadow-xs cursor-pointer disabled:opacity-50"
          >
            <UploadCloud className="h-4 w-4" />
            {isUploading ? "Analyzing PPTX..." : "Upload Master PPTX"}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-md border border-red-200 bg-red-50 text-red-800 text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Studio View */}
      {selectedTemplate ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Template Selector & Theme Metadata */}
          <div className="lg:col-span-3 space-y-4">
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <FileCheck className="h-3.5 w-3.5 text-primary" /> Active Template
              </h3>
              <div>
                <p className="text-sm font-bold text-foreground truncate">{selectedTemplate.name}</p>
                <p className="text-[11px] text-muted-foreground truncate">{selectedTemplate.filename}</p>
              </div>

              <div className="pt-2 border-t text-[11px] space-y-1.5 text-muted-foreground">
                <div className="flex justify-between">
                  <span>Aspect Ratio:</span>
                  <span className="font-semibold text-foreground">{selectedTemplate.aspect_ratio}</span>
                </div>
                <div className="flex justify-between">
                  <span>Slide Size:</span>
                  <span className="font-semibold text-foreground">{selectedTemplate.slide_width_in}" × {selectedTemplate.slide_height_in}"</span>
                </div>
                <div className="flex justify-between">
                  <span>Total Slides:</span>
                  <span className="font-semibold text-foreground">{selectedTemplate.slide_count}</span>
                </div>
              </div>
            </div>

            {/* Extracted Theme & Typography */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Palette className="h-3.5 w-3.5 text-primary" /> Brand Theme Colors
              </h3>
              <div className="flex flex-wrap gap-2">
                {selectedTemplate.theme.detected_colors.map((cHex) => (
                  <div key={cHex} className="flex items-center gap-1.5 border rounded px-2 py-1 bg-muted/20">
                    <span className="w-3.5 h-3.5 rounded-full border shadow-2xs" style={{ backgroundColor: `#${cHex}` }} />
                    <span className="text-[10px] font-mono font-medium">#{cHex}</span>
                  </div>
                ))}
              </div>

              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 pt-2 border-t">
                <Type className="h-3.5 w-3.5 text-primary" /> Detected Typography
              </h3>
              <div className="space-y-1">
                {selectedTemplate.theme.detected_fonts.map((fName) => (
                  <p key={fName} className="text-xs text-foreground font-medium">
                    • {fName}
                  </p>
                ))}
              </div>
            </div>

            {/* Slide Navigation List */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Layout className="h-3.5 w-3.5 text-primary" /> Slide Layouts
              </h3>
              <div className="space-y-1">
                {selectedTemplate.slides.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setActiveSlideIdx(idx);
                      setSelectedElement(null);
                    }}
                    className={`w-full text-left px-3 py-2 rounded text-xs flex items-center justify-between transition-colors cursor-pointer ${
                      activeSlideIdx === idx
                        ? "bg-primary text-primary-foreground font-semibold"
                        : "hover:bg-muted text-foreground"
                    }`}
                  >
                    <span>Slide {idx + 1} ({s.elements.length} elements)</span>
                    <ChevronRight className="h-3.5 w-3.5 opacity-60" />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Middle Column: Slide Canvas & Interactive Elements List */}
          <div className="lg:col-span-6 space-y-4">
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <div className="flex items-center justify-between border-b pb-3">
                <h3 className="text-sm font-bold text-foreground">
                  Slide {activeSlideIdx + 1} Visual Elements Breakdown
                </h3>
                <span className="text-xs text-muted-foreground">
                  {activeSlide?.elements.length || 0} Shapes / Frames Analyzed
                </span>
              </div>

              {/* Elements Table */}
              <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                {activeSlide?.elements.map((elem) => {
                  const isSel = selectedElement?.element_id === elem.element_id;
                  return (
                    <div
                      key={elem.element_id}
                      onClick={() => setSelectedElement(elem)}
                      className={`p-3 rounded-md border transition-all cursor-pointer ${
                        isSel
                          ? "border-primary bg-primary/5 shadow-xs"
                          : "border-border hover:border-muted-foreground/30 bg-muted/10"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs text-foreground">
                              {elem.shape_name}
                            </span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              ({elem.element_type})
                            </span>
                          </div>

                          {elem.text_sample && (
                            <p className="text-[11px] text-muted-foreground italic line-clamp-1">
                              "{elem.text_sample}"
                            </p>
                          )}

                          <div className="text-[10px] text-muted-foreground flex gap-3">
                            <span>Pos: {elem.left_in}", {elem.top_in}"</span>
                            <span>Size: {elem.width_in}" × {elem.height_in}"</span>
                          </div>
                        </div>

                        <div className="flex flex-col items-end gap-1">
                          {getRoleBadge(elem.role)}
                          {elem.user_confirmed && (
                            <span className="text-[10px] text-emerald-600 flex items-center gap-0.5">
                              <CheckCircle2 className="h-3 w-3" /> Confirmed
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Element Role Inspector & Configuration */}
          <div className="lg:col-span-3 space-y-4">
            <div className="rounded-lg border border-border bg-card p-4 space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Sliders className="h-3.5 w-3.5 text-primary" /> Role Inspector
              </h3>

              {selectedElement ? (
                <div className="space-y-4 text-xs">
                  <div>
                    <span className="text-muted-foreground block text-[10px]">Element ID</span>
                    <span className="font-mono text-foreground">{selectedElement.element_id}</span>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[10px]">Heuristic Confidence</span>
                    <div className="w-full bg-muted rounded-full h-1.5 mt-1">
                      <div
                        className="bg-primary h-1.5 rounded-full"
                        style={{ width: `${Math.round(selectedElement.confidence_score * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground mt-0.5 block">
                      {Math.round(selectedElement.confidence_score * 100)}% algorithmic confidence
                    </span>
                  </div>

                  {selectedElement.text_style && (
                    <div className="p-2.5 rounded bg-muted/20 border space-y-1 text-[11px]">
                      <span className="font-semibold block text-foreground">Typography Specs</span>
                      <p>Font: {selectedElement.text_style.font_name || "Inherited"}</p>
                      <p>Size: {selectedElement.text_style.font_size_pt} pt</p>
                      <p>Weight: {selectedElement.text_style.bold ? "Bold" : "Regular"}</p>
                      {selectedElement.text_style.color_rgb && (
                        <p className="flex items-center gap-1">
                          Color: <span className="w-2.5 h-2.5 rounded-full border" style={{ backgroundColor: `#${selectedElement.text_style.color_rgb}` }} />
                          #{selectedElement.text_style.color_rgb}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Manual Role Confirmation Buttons */}
                  <div className="pt-2 border-t space-y-2">
                    <span className="font-bold text-xs text-foreground block">Assign Element Role</span>

                    <button
                      onClick={() => handleRoleUpdate(selectedElement.element_id, "STATIC")}
                      className={`w-full text-left px-3 py-2 rounded text-xs border transition-colors cursor-pointer ${
                        selectedElement.role === "STATIC"
                          ? "bg-gray-100 border-gray-400 font-bold"
                          : "hover:bg-muted"
                      }`}
                    >
                      <span className="font-semibold block">Static Visual</span>
                      <span className="text-[10px] text-muted-foreground block">Logo, branding, immutable header/footer</span>
                    </button>

                    <button
                      onClick={() => handleRoleUpdate(selectedElement.element_id, "CONTAINER")}
                      className={`w-full text-left px-3 py-2 rounded text-xs border transition-colors cursor-pointer ${
                        selectedElement.role === "CONTAINER"
                          ? "bg-blue-50 border-blue-400 text-blue-900 font-bold"
                          : "hover:bg-muted"
                      }`}
                    >
                      <span className="font-semibold block">Card Container</span>
                      <span className="text-[10px] text-muted-foreground block">Background rectangle enclosing card content</span>
                    </button>

                    {selectedElement.element_type === "TEXT" && (
                      <button
                        onClick={() => handleRoleUpdate(selectedElement.element_id, "REPLACEABLE_TEXT")}
                        className={`w-full text-left px-3 py-2 rounded text-xs border transition-colors cursor-pointer ${
                          selectedElement.role === "REPLACEABLE_TEXT"
                            ? "bg-emerald-50 border-emerald-400 text-emerald-900 font-bold"
                            : "hover:bg-muted"
                        }`}
                      >
                        <span className="font-semibold block">Replaceable Text</span>
                        <span className="text-[10px] text-muted-foreground block">Dynamically populated with data</span>
                      </button>
                    )}

                    {selectedElement.element_type === "IMAGE" && (
                      <button
                        onClick={() => handleRoleUpdate(selectedElement.element_id, "REPLACEABLE_IMAGE")}
                        className={`w-full text-left px-3 py-2 rounded text-xs border transition-colors cursor-pointer ${
                          selectedElement.role === "REPLACEABLE_IMAGE"
                            ? "bg-purple-50 border-purple-400 text-purple-900 font-bold"
                            : "hover:bg-muted"
                        }`}
                      >
                        <span className="font-semibold block">Replaceable Photo</span>
                        <span className="text-[10px] text-muted-foreground block">Image frame receiving dynamic photographs</span>
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  Select an element from the middle list to inspect its styling and assign its role.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-border p-12 text-center space-y-4 bg-card/40">
          <UploadCloud className="h-10 w-10 text-primary mx-auto opacity-70" />
          <div className="space-y-1">
            <h3 className="text-base font-bold text-foreground">No Template Loaded</h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Upload any PowerPoint (.pptx) file to inspect its geometric structure, extracted theme palette, and candidate replaceable elements.
            </p>
          </div>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 shadow-xs cursor-pointer"
          >
            <UploadCloud className="h-4 w-4" />
            Upload Master PPTX
          </button>
        </div>
      )}
    </div>
  );
}
