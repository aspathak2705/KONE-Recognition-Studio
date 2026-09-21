# KONE Recognition Studio

Internal application for generating quarterly employee recognition presentations and posters from structured Excel data into KONE-approved PowerPoint formats.

## Development Phase

**Current Phase**: `Phase 1 — Excel Intelligence, Validation, and PowerPoint Template Inspection`

## Tech Stack

- **Backend**: Python, FastAPI, Pydantic, Uvicorn, openpyxl, python-pptx, pytest
- **Frontend**: React, TypeScript, Vite, Tailwind CSS v4, Lucide React
- **Future Generation Layer**: `python-pptx` presentation builder engine (Deferred to Phase 2)

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

## Phase 1 Feature Summary

1. **Excel Parsing & Schema Validation**:
   - Parses `.xlsx` workbooks using `openpyxl`.
   - Supports canonical headers: `employee_name`, `designation`, `branch`, `award_name` (with flexible aliases like `name`, `role`, `city`, `award`).
   - Identifies empty cell values, missing required headers, corrupt workbooks, and duplicate records.
   - Returns structured JSON validation feedback with row-level error reporting.

2. **PowerPoint Template Inspection**:
   - Inspects master PowerPoint templates (`.pptx`) using `python-pptx`.
   - Extracts presentation metadata (slide count, slide dimensions, aspect ratio).
   - Analyzes slide-level text frames, shape types, shape positions, and placeholder counts without modifying the original template file.

3. **Safe Local File Storage**:
   - Stores uploaded files under `storage/uploads/excel` and `storage/uploads/templates` using UUID filenames to prevent path traversal.

---

## Separation from AutoHR

This project is completely separate from AutoHR. It reuses only visual design tokens (KONE Blue aesthetic) for visual consistency across internal tools. No database models, auth routes, or business logic are shared.
