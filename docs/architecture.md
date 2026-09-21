# KONE Recognition Studio Architecture Document

## Overview

**KONE Recognition Studio** automates employee recognition presentation generation from Excel data to PowerPoint formats.

## Phase 1 System Architecture

```
[ Frontend (React/Vite/TS) ] 
       │
       ├── (GET /health) ──────────────────────> [ Backend (FastAPI) ]
       ├── (GET /api/recognitions/schema) ─────> [ Schema Specification ]
       ├── (POST /api/recognitions/validate) ──> [ Excel Parser Service (openpyxl) ]
       └── (POST /api/templates/inspect) ─────> [ Template Inspector (python-pptx) ]
                                                       │
                                                       ▼
                                            [ Safe Storage Abstraction ]
                                            (storage/uploads/excel & templates)
```

## Data Processing Pipelines

### 1. Excel Parsing & Validation Pipeline
```text
Uploaded .xlsx File
  ↓
File Storage Service (UUID filename, path traversal guard)
  ↓
openpyxl Workbook Loader (data_only=True)
  ↓
Header Canonicalization (employee_name, designation, branch, award_name)
  ↓
Row-Level Validation (empty check, whitespace trim, duplicate detection)
  ↓
Structured Validation Response (Pydantic models)
```

### 2. PowerPoint Inspection Pipeline
```text
Uploaded .pptx Master Template
  ↓
File Storage Service (UUID filename)
  ↓
python-pptx Presentation Inspector (Read-Only)
  ↓
Extract Slide Metadata (Count, Width, Height, Aspect Ratio 16:9 / 4:3)
  ↓
Extract Shape Breakdown (Text frames, Positions, Width/Height, Placeholders)
  ↓
Template Inspection Response & Warnings
```

## Phase 2 Deferred Architecture

PowerPoint presentation generation (`python-pptx` layout builder) and database persistence are deferred to Phase 2 after final template shape mapping alignment.
