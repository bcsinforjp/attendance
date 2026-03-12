# 📄 Attendance PDF → Excel Converter

A web-based tool that converts Japanese attendance PDF reports into clean Excel spreadsheets with automatic working hours calculation.

## Features

- **PDF Parsing** — Extracts employee data from raw attendance PDFs (Japanese format)
- **Smart Time Handling**
  - `当11:22` → `11:22` (same day)
  - `翌03:57` → `27:57` (next day, +24h)
  - `__:__` / `----` → blank (no data)
- **Working Hours** — Calculated automatically from start/end times
- **Excel Export** — Clean `.xlsx` output with headers, borders, and auto-width columns
- **Preview** — See extracted data before downloading
- **Drag & Drop** — Modern web UI with dark theme

## Tech Stack

- **Backend:** Python 3 + FastAPI + Uvicorn
- **PDF Parsing:** pdfplumber
- **Excel Generation:** openpyxl
- **Frontend:** Vanilla HTML/CSS/JS (dark themed)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web interface |
| `POST` | `/api/convert` | Upload PDF → Download Excel |
| `POST` | `/api/preview` | Upload PDF → JSON preview (max 50 records) |
| `GET` | `/api/health` | Health check |

## Running Locally

```bash
cd projects/attendance
pip install fastapi uvicorn pdfplumber openpyxl python-multipart
uvicorn main:app --host 0.0.0.0 --port 8002
```

## Project Structure

```
attendance/
├── main.py        # FastAPI app with PDF parsing & Excel generation
├── index.html     # Web UI (upload, preview, download)
├── .gitignore
└── README.md
```

## Version History

- **v1.0** (2026-03-13) — Initial stable baseline
