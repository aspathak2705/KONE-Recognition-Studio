# KONE Recognition Studio Architecture Document

## Overview

**KONE Recognition Studio** automates employee recognition presentation generation from Excel data to PowerPoint formats using a persistent, reusable **Template Registry**.

## Phase 2.4 System Architecture

```text
[ Frontend (React/Vite/TS) - HR Single Workflow ] 
       │
       ├── (GET /api/templates) ────────────────────> [ Template Registry Service ]
       │                                                      │
       ├── (POST /api/templates/register) ─────────> (SHA-256 Hash + python-pptx Inspector)
       │                                                      │
       ├── (POST /api/recognitions/validate-excel) ─> [ Excel Parser Service ]
       │                                                      │
       └── (POST /api/recognitions/generate) ───────> [ PPTX Generator Engine ]
                                                              │
                                                              ▼
                                                   [ Persistent Storage ]
                                            (storage/templates/ & storage/generated/)
```

---

## Template Registry Lifecycle & Versioning

```text
Upload Master PPTX
  ↓
Calculate SHA-256 Hash
  ↓
Existing Hash Match? ── (Yes) ──> Reuse Stored Template Version (Skip Inspection)
  ↓ (No)
Run PowerPoint Inspection ONCE
  ↓
Configure Canonical Field Mapping (employee_name, designation, branch, award_name)
  ↓
Persist Version Metadata & Binary (storage/templates/<template_id>/)
  ↓
Ready for Recurring Presentation Generation (No PPTX re-upload needed)
```

---

## Recurring HR Presentation Generation Pipeline

```text
Upload Excel Recognition File
  ↓
Select Existing Registered Template from Library
  ↓
Review Validation & Mapping Status
  ↓
python-pptx Layout Cloner (Clones slide 0 for multi-employee batches)
  ↓
Text Substitution (Substitutes text while preserving font, size, color, & wrapping)
  ↓
Save Output (storage/generated/<generation_id>.pptx)
  ↓
Return File Download Endpoint (/api/generations/{generation_id}/download)
```
