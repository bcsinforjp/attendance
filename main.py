"""
Attendance PDF → Excel Converter
Parses Japanese attendance PDFs and exports clean Excel with working hours.
"""

import io
import re
from datetime import datetime
from pathlib import Path

import pdfplumber
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

app = FastAPI(title="Attendance PDF Converter")

LOG_DIR = Path("/var/log/ai_server")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    with open(LOG_DIR / "attendance.log", "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


# ─── Time Parsing ─────────────────────────────────────────────

def parse_jp_time(raw: str) -> tuple:
    """
    Parse Japanese attendance time strings.
    Returns (display_time, decimal_hours) or (None, None) if invalid.

    Examples:
        当11:22 -> ("11:22", 11.37)
        翌03:57 -> ("27:57", 27.95)   # +24 for next day
        __:__   -> (None, None)
        ----    -> (None, None)
    """
    if not raw or not isinstance(raw, str):
        return None, None

    raw = raw.strip()

    # Skip empty/no-data markers
    if raw in ("__:_", "__:__", "----", "", "------"):
        return None, None

    # Match patterns: 当HH:MM or 翌HH:MM or just HH:MM
    m = re.search(r'(当|翌)?\s*(\d{1,2}):(\d{2})', raw)
    if not m:
        return None, None

    prefix = m.group(1)
    hour = int(m.group(2))
    minute = int(m.group(3))

    # 翌 means next day, add 24 hours
    if prefix == "翌":
        hour += 24

    display = f"{hour}:{minute:02d}"
    decimal = hour + minute / 60.0
    return display, decimal


def calc_working_hours(start_decimal: float, end_decimal: float) -> str:
    """Calculate working hours as HH:MM string."""
    if start_decimal is None or end_decimal is None:
        return ""
    diff = end_decimal - start_decimal
    if diff < 0:
        return ""
    hours = int(diff)
    minutes = int((diff - hours) * 60)
    return f"{hours}:{minutes:02d}"


# ─── PDF Parsing ──────────────────────────────────────────────

def extract_records(pdf_bytes: bytes) -> list:
    """
    Extract employee records from raw attendance PDF.
    Returns list of dicts with: code, name, start_time, end_time, working_hours
    """
    records = []
    seen_codes = set()  # Avoid duplicates across pages

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue

                    # Flatten row (some cells may be nested)
                    flat = []
                    for cell in row:
                        if cell is None:
                            flat.append("")
                        else:
                            flat.append(str(cell).replace("\n", " ").strip())

                    # Employee code is 8 digits
                    code = None
                    code_idx = None
                    for i, cell in enumerate(flat):
                        c = cell.strip()
                        if re.match(r'^\d{8}$', c):
                            code = c
                            code_idx = i
                            break

                    if not code or code in seen_codes:
                        continue

                    # Skip 小計 (subtotal) rows
                    row_text = " ".join(flat)
                    if "小計" in row_text:
                        continue

                    seen_codes.add(code)

                    # Name is next column after code
                    name = flat[code_idx + 1] if code_idx + 1 < len(flat) else ""

                    # Find start and end times
                    # Look for time patterns in remaining cells
                    start_time = None
                    end_time = None
                    start_dec = None
                    end_dec = None

                    time_cells = []
                    for cell in flat[code_idx + 2:]:
                        parsed, dec = parse_jp_time(cell)
                        if parsed:
                            time_cells.append((parsed, dec))

                    if len(time_cells) >= 2:
                        start_time, start_dec = time_cells[0]
                        end_time, end_dec = time_cells[1]
                    elif len(time_cells) == 1:
                        start_time, start_dec = time_cells[0]

                    # Calculate working hours
                    wh = calc_working_hours(start_dec, end_dec)

                    records.append({
                        "code": code,
                        "name": name,
                        "start_time": start_time or "",
                        "end_time": end_time or "",
                        "working_hours": wh,
                    })

    return records


# ─── Excel Generation ─────────────────────────────────────────

def create_excel(records: list) -> bytes:
    """Create Excel file with attendance data matching template format."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"

    # Header style
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Headers (matching template PDF structure)
    headers = [
        "Personal Code",
        "Full Name",
        "Commute Time",
        "Time to Leave",
        "Working Hours",
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Data rows
    for row_idx, rec in enumerate(records, 2):
        values = [
            rec["code"],
            rec["name"],
            rec["start_time"],
            rec["end_time"],
            rec["working_hours"],
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = thin_border
            if col in (3, 4, 5):
                cell.alignment = Alignment(horizontal='center')

    # Auto-width
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 35
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15

    # Save to bytes
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ─── API Endpoints ────────────────────────────────────────────

@app.get("/")
def index():
    """Serve the web interface."""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text())
    return HTMLResponse("<h1>Attendance Converter</h1><p>Upload a raw attendance PDF.</p>")


@app.post("/api/convert")
async def convert_pdf(file: UploadFile = File(...)):
    """Convert raw attendance PDF to Excel."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Please upload a PDF file")

    log(f"Processing: {file.filename}")

    try:
        pdf_bytes = await file.read()
        records = extract_records(pdf_bytes)

        if not records:
            raise HTTPException(400, "No employee records found in PDF. Check the file format.")

        log(f"Extracted {len(records)} records")

        excel_bytes = create_excel(records)

        # Save to temp file for download
        out_path = Path("/tmp/attendance_output.xlsx")
        out_path.write_bytes(excel_bytes)

        log(f"Excel generated: {len(records)} employees")

        return FileResponse(
            out_path,
            filename="attendance_report.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise
    except Exception as e:
        log(f"Error: {e}")
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.post("/api/preview")
async def preview_pdf(file: UploadFile = File(...)):
    """Preview extracted data before download."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Please upload a PDF file")

    try:
        pdf_bytes = await file.read()
        records = extract_records(pdf_bytes)
        return {"count": len(records), "records": records[:50]}
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "attendance-converter"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
