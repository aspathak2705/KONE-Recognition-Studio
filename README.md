# KONE Recognition Automation

Internal application for generating quarterly employee recognition presentations and posters from structured Excel data into KONE-approved PowerPoint formats.

## Development Phase

**Current Phase**: `Phase 0 — Project Foundation & Architecture Setup`

## Tech Stack

- **Backend**: Python, FastAPI, Pydantic, Uvicorn
- **Frontend**: React, TypeScript, Vite, Tailwind CSS v4
- **Future Generation Layer**: `python-pptx`, `openpyxl` (Deferred to Phase 1)

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
uvicorn app.main:app --reload --port 8000
```

Verify backend health check at `http://127.0.0.1:8000/health`.

Response:
```json
{
  "status": "ok",
  "service": "kone-recognition-automation"
}
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Project Structure

```
KONE Recognition Studio/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   └── config.py
│   │   └── api/
│   │       └── health.py
│   ├── tests/
│   │   └── test_health.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── AppShell.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── RecognitionProjects.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── templates/
│   └── README.md
├── docs/
│   └── architecture.md
├── .env.example
├── .gitignore
└── README.md
```

---

## Separation from AutoHR

This project is completely separate from AutoHR. It reuses only design tokens (KONE Blue aesthetic) for visual consistency across internal tools. No database models, auth routes, or business logic are shared.
