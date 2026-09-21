# KONE Recognition Automation Architecture Document

## Overview

**KONE Recognition Automation** automates employee recognition presentation generation from Excel data to PowerPoint formats.

## Phase 0 Architecture Boundary

```
[ Frontend (React/Vite/TS) ] ── (HTTP GET /health) ──> [ Backend (FastAPI) ]
```

### Clean Project Boundaries
- **Independent Project**: Completely separate from AutoHR. Shares zero database models, API routes, or auth handlers.
- **Frontend Layer**: React + Vite + TypeScript. Design system inspired by AutoHR tokens (KONE Blue `oklch(0.52 0.16 250)`).
- **Backend Layer**: FastAPI lightweight backend providing configuration management and basic health diagnostics.
- **Future Rendering Service Boundary (Phase 1+)**:
  ```
  Excel Input ──> Recognition Data Validation ──> Layout Planning ──> Template Selection ──> PowerPoint Rendering ──> Editable PPTX
  ```

## Deferral Rationale

Master newspaper-style PowerPoint template pending delivery from KONE. PowerPoint manipulation (`python-pptx`) and Excel parsing (`openpyxl`) deferred to Phase 1.
