# KONE Recognition Studio

Internal application for generating quarterly employee recognition presentations and posters from structured Excel data into KONE-approved PowerPoint formats.

## Development Phase

**Current Phase**: `Phase 2.1 — Generation Verification, Template Fidelity & Production-Safety Hardening`

## Tech Stack

- **Backend**: Python, FastAPI, Pydantic, Uvicorn, openpyxl, python-pptx, pytest
- **Frontend**: React, TypeScript, Vite, Tailwind CSS v4, Lucide React
- **Presentation Engine**: `python-pptx` automated layout cloning and text substitution builder

---

## Local Setup & Quickstart

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm / bun

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt

# Run backend server
uvicorn app.main:app --reload --port 8000
```

Verify backend endpoints:
- Health check: `GET http://127.0.0.1:8000/health`
- Excel schema spec: `GET http://127.0.0.1:8000/api/recognitions/schema`
- Validate Excel upload: `POST http://127.0.0.1:8000/api/recognitions/validate-excel`
- Inspect PowerPoint template: `POST http://127.0.0.1:8000/api/templates/inspect`
- Template readiness status: `GET http://127.0.0.1:8000/api/templates/{file_id}/readiness`
- Validate field mapping: `POST http://127.0.0.1:8000/api/templates/mapping/validate`
- Generate presentation: `POST http://127.0.0.1:8000/api/recognitions/generate`
- Download generated `.pptx`: `GET http://127.0.0.1:8000/api/generations/{generation_id}/download`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Run Automated Tests

```bash
# Run all backend unit & integration tests
$env:PYTHONPATH="backend"; python -m pytest backend/tests

# Run frontend TypeScript type checks & production build
cd frontend
npm run build
```

---

## Phase 2 Feature Summary

1. **Template Mapping & Readiness Engine**:
   - Explicit field mapping contract (`employee_name`, `designation`, `branch`, `award_name`).
   - Auto-suggests mappings based on shape names and placeholder types.
   - Calculates explicit readiness states (`requires_template`, `requires_mapping`, `blocked_by_validation`, `ready_for_generation`).

2. **Controlled PowerPoint Presentation Generation**:
   - Clones slide layouts dynamically for multi-record Excel batches.
   - Substitutes dynamic text while preserving font family, size, color, alignment, and line wrapping.
   - Performs long-text overflow detection (>40 chars) and emits structured warnings.
   - Saves generated presentations to `storage/generated/<generation_id>.pptx`.
   - Post-build readability verification before returning download payload.

3. **Interactive Frontend Workflow**:
   - `GeneratePresentation` page allowing Excel upload, PPTX template upload, shape mapping configuration, progress tracking, and direct `.pptx` file download.

---

## Separation from AutoHR

This project is completely separate from AutoHR. It reuses only visual design tokens (KONE Blue aesthetic) for visual consistency across internal tools. No database models, auth routes, or business logic are shared.
