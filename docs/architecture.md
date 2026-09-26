# KONE Recognition Studio Architecture Document

## Overview

**KONE Recognition Studio** automates employee recognition presentation generation from Excel data to PowerPoint formats.

## Phase 2 System Architecture

```
[ Frontend (React/Vite/TS) - Create Presentation Wizard ] 
       │
       ├── (GET /health) ──────────────────────────> [ Backend (FastAPI) ]
       ├── (POST /api/recognitions/validate-excel) ─> [ Excel Parser Service ]
       ├── (POST /api/templates/inspect) ─────────> [ Template Inspector (python-pptx) ]
       ├── (GET /api/templates/{file_id}/readiness) ─> [ Mapping Readiness Service ]
       ├── (POST /api/recognitions/generate) ─────> [ PPTX Generator Engine ]
       └── (GET /api/generations/{id}/download) ───> [ File Download Response ]
                                                            │
                                                            ▼
                                                [ Storage Abstraction ]
                                        (storage/uploads/ & storage/generated/)
```

## PPTX Presentation Generation Pipeline

```text
Validated Excel Records + Master Template (.pptx) + Field Mapping Config
  ↓
Validation & Readiness Engine (Verifies required shape mappings)
  ↓
python-pptx Layout Cloner (Clones slide 0 for multi-employee batches)
  ↓
Text Substitution (Substitutes text while preserving font, size, color, & wrapping)
  ↓
Overflow Detection (Flags values > 40 chars)
  ↓
Save Output (storage/generated/<generation_id>.pptx)
  ↓
Readability Verification (Re-inspects generated PPTX using python-pptx)
  ↓
Return File Download Endpoint (/api/generations/{generation_id}/download)
```
