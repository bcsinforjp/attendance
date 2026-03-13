"""
Attendance PDF → Excel Converter
Parses Japanese attendance PDFs, saves to PostgreSQL, exports Excel.
"""

import io
import re
from datetime import datetime, date
from pathlib import Path

import pdfplumber
import psycopg2
import psycopg2.pool
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
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


# ─── Database Connection Pool ─────────────────────────────────

db_pool = None


def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1, maxconn=10,
            host="localhost", port=5432,
            database="attendance_db",
            user="attendance", password="attendance2026"
        )
    return db_pool


def get_db():
    """Get a database connection from the pool."""
    pool = get_db_pool()
    return pool.getconn()


def release_db(conn):
    """Release connection back to pool."""
    pool = get_db_pool()
    pool.putconn(conn)


# ─── Time Parsing ─────────────────────────────────────────────

def parse_jp_time(raw: str, is_leave: bool = False) -> tuple:
    """
    Parse Japanese attendance time strings.
    Returns (display_time, decimal_hours) or (None, None) if invalid.

    For Time to Leave (is_leave=True):
        Hours 1-6 without 翌 prefix also get +24 (after midnight = next day).
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

    # For Time to Leave: add 24 if 翌 prefix OR small hours (1-6) after midnight
    if is_leave:
        if prefix == "翌":
            hour += 24
        elif 1 <= hour <= 6:
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
    """Extract employee records from raw attendance PDF."""
    records = []
    seen_codes = set()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue

                    flat = []
                    for cell in row:
                        if cell is None:
                            flat.append("")
                        else:
                            flat.append(str(cell).replace("\n", " ").strip())

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

                    row_text = " ".join(flat)
                    if "小計" in row_text:
                        continue

                    seen_codes.add(code)

                    name = flat[code_idx + 1] if code_idx + 1 < len(flat) else ""

                    start_time = None
                    end_time = None
                    start_dec = None
                    end_dec = None

                    raw_time_cells = []
                    for cell in flat[code_idx + 2:]:
                        parsed, dec = parse_jp_time(cell)
                        if parsed:
                            raw_time_cells.append(cell)

                    if len(raw_time_cells) >= 2:
                        start_time, start_dec = parse_jp_time(raw_time_cells[0])
                        end_time, end_dec = parse_jp_time(raw_time_cells[1], is_leave=True)
                    elif len(raw_time_cells) == 1:
                        start_time, start_dec = parse_jp_time(raw_time_cells[0])

                    wh = calc_working_hours(start_dec, end_dec)

                    records.append({
                        "code": code,
                        "name": name,
                        "start_time": start_time or "",
                        "end_time": end_time or "",
                        "working_hours": wh,
                    })

    return records


# ─── Database Save ────────────────────────────────────────────

def save_to_db(records: list, filename: str) -> int:
    """Save extracted records to PostgreSQL. Returns batch ID."""
    conn = get_db()
    try:
        cur = conn.cursor()

        # Create upload batch
        cur.execute(
            "INSERT INTO upload_batches (file_name, total_records) VALUES (%s, %s) RETURNING id",
            (filename, len(records))
        )
        batch_id = cur.fetchone()[0]

        # Insert records
        today = date.today()
        month_year = today.strftime("%Y-%m")

        for rec in records:
            cur.execute("""
                INSERT INTO attendance_records
                (upload_date, file_name, personal_code, full_name, commute_time, time_to_leave, working_hours, record_date, month_year)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(), filename, rec["code"], rec["name"],
                rec["start_time"], rec["end_time"], rec["working_hours"],
                today, month_year
            ))

        conn.commit()
        cur.close()
        log(f"Saved {len(records)} records to DB (batch {batch_id})")
        return batch_id
    except Exception as e:
        conn.rollback()
        log(f"DB save error: {e}")
        raise
    finally:
        release_db(conn)


# ─── Excel Generation ─────────────────────────────────────────

def create_excel(records: list) -> bytes:
    """Create Excel file with attendance data."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    headers = ["Personal Code", "Full Name", "Commute Time", "Time to Leave", "Working Hours"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    for row_idx, rec in enumerate(records, 2):
        values = [rec["code"], rec["name"], rec["start_time"], rec["end_time"], rec["working_hours"]]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.border = thin_border
            if col in (3, 4, 5):
                cell.alignment = Alignment(horizontal='center')

    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 35
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15

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
    """Convert raw attendance PDF to Excel AND save to database."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Please upload a PDF file")

    log(f"Processing: {file.filename}")

    try:
        pdf_bytes = await file.read()
        records = extract_records(pdf_bytes)

        if not records:
            raise HTTPException(400, "No employee records found in PDF. Check the file format.")

        # Save to database
        batch_id = save_to_db(records, file.filename)

        log(f"Extracted {len(records)} records (batch {batch_id})")

        excel_bytes = create_excel(records)
        out_path = Path("/tmp/attendance_output.xlsx")
        out_path.write_bytes(excel_bytes)

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


# ─── Management Dashboard API ─────────────────────────────────

@app.get("/api/dashboard/summary")
def dashboard_summary(month: str = Query(None, description="YYYY-MM format, e.g. 2026-03")):
    """Get attendance summary for management dashboard."""
    conn = get_db()
    try:
        cur = conn.cursor()

        if not month:
            month = date.today().strftime("%Y-%m")

        # Total employees who clocked in
        cur.execute("""
            SELECT COUNT(DISTINCT personal_code) as total_employees,
                   COUNT(*) as total_records,
                   AVG(CASE WHEN working_hours != '' THEN
                       CAST(SPLIT_PART(working_hours, ':', 1) AS FLOAT) +
                       CAST(SPLIT_PART(working_hours, ':', 2) AS FLOAT) / 60.0
                   END) as avg_hours
            FROM attendance_records
            WHERE month_year = %s
        """, (month,))
        row = cur.fetchone()

        # Daily summary
        cur.execute("""
            SELECT record_date,
                   COUNT(DISTINCT personal_code) as employees,
                   COUNT(*) as records,
                   AVG(CASE WHEN working_hours != '' THEN
                       CAST(SPLIT_PART(working_hours, ':', 1) AS FLOAT) +
                       CAST(SPLIT_PART(working_hours, ':', 2) AS FLOAT) / 60.0
                   END) as avg_hours
            FROM attendance_records
            WHERE month_year = %s
            GROUP BY record_date
            ORDER BY record_date DESC
            LIMIT 30
        """, (month,))
        daily = []
        for r in cur.fetchall():
            daily.append({
                "date": str(r[0]),
                "employees": r[1],
                "records": r[2],
                "avg_hours": round(r[3], 2) if r[3] else 0
            })

        # Top workers by hours
        cur.execute("""
            SELECT personal_code, full_name,
                   COUNT(*) as days_worked,
                   AVG(CASE WHEN working_hours != '' THEN
                       CAST(SPLIT_PART(working_hours, ':', 1) AS FLOAT) +
                       CAST(SPLIT_PART(working_hours, ':', 2) AS FLOAT) / 60.0
                   END) as avg_hours
            FROM attendance_records
            WHERE month_year = %s AND working_hours != ''
            GROUP BY personal_code, full_name
            ORDER BY avg_hours DESC
            LIMIT 20
        """, (month,))
        top_workers = []
        for r in cur.fetchall():
            top_workers.append({
                "code": r[0],
                "name": r[1],
                "days_worked": r[2],
                "avg_hours": round(r[3], 2) if r[3] else 0
            })

        cur.close()

        return {
            "month": month,
            "total_employees": row[0] if row else 0,
            "total_records": row[1] if row else 0,
            "avg_working_hours": round(row[2], 2) if row and row[2] else 0,
            "daily": daily,
            "top_workers": top_workers
        }
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")
    finally:
        release_db(conn)


@app.get("/api/dashboard/employee/{code}")
def employee_detail(code: str, month: str = Query(None)):
    """Get individual employee attendance details."""
    conn = get_db()
    try:
        cur = conn.cursor()

        if not month:
            month = date.today().strftime("%Y-%m")

        cur.execute("""
            SELECT record_date, commute_time, time_to_leave, working_hours
            FROM attendance_records
            WHERE personal_code = %s AND month_year = %s
            ORDER BY record_date
        """, (code, month))

        records = []
        for r in cur.fetchall():
            records.append({
                "date": str(r[0]),
                "commute_time": r[1],
                "time_to_leave": r[2],
                "working_hours": r[3]
            })

        # Employee info
        cur.execute("""
            SELECT full_name, COUNT(*),
                   AVG(CASE WHEN working_hours != '' THEN
                       CAST(SPLIT_PART(working_hours, ':', 1) AS FLOAT) +
                       CAST(SPLIT_PART(working_hours, ':', 2) AS FLOAT) / 60.0
                   END) as avg_hours
            FROM attendance_records
            WHERE personal_code = %s AND month_year = %s
            GROUP BY full_name
        """, (code, month))
        info = cur.fetchone()

        cur.close()

        return {
            "code": code,
            "name": info[0] if info else "",
            "month": month,
            "days_worked": info[1] if info else 0,
            "avg_hours": round(info[2], 2) if info and info[2] else 0,
            "records": records
        }
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")
    finally:
        release_db(conn)


@app.get("/api/dashboard/employees")
def list_employees(month: str = Query(None)):
    """List all employees with summary."""
    conn = get_db()
    try:
        cur = conn.cursor()

        if not month:
            month = date.today().strftime("%Y-%m")

        cur.execute("""
            SELECT personal_code, full_name,
                   COUNT(*) as days,
                   MIN(commute_time) FILTER (WHERE commute_time != '') as earliest_in,
                   MAX(time_to_leave) FILTER (WHERE time_to_leave != '') as latest_out,
                   AVG(CASE WHEN working_hours != '' THEN
                       CAST(SPLIT_PART(working_hours, ':', 1) AS FLOAT) +
                       CAST(SPLIT_PART(working_hours, ':', 2) AS FLOAT) / 60.0
                   END) as avg_hours
            FROM attendance_records
            WHERE month_year = %s
            GROUP BY personal_code, full_name
            ORDER BY personal_code
        """, (month,))

        employees = []
        for r in cur.fetchall():
            employees.append({
                "code": r[0],
                "name": r[1],
                "days_worked": r[2],
                "earliest_in": r[3],
                "latest_out": r[4],
                "avg_hours": round(r[5], 2) if r[5] else 0
            })

        cur.close()
        return {"month": month, "employees": employees}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")
    finally:
        release_db(conn)


@app.get("/api/dashboard/months")
def available_months():
    """List months with data."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT month_year, COUNT(*) as records, COUNT(DISTINCT personal_code) as employees
            FROM attendance_records
            GROUP BY month_year
            ORDER BY month_year DESC
        """)
        months = []
        for r in cur.fetchall():
            months.append({
                "month": r[0],
                "records": r[1],
                "employees": r[2]
            })
        cur.close()
        return {"months": months}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")
    finally:
        release_db(conn)


@app.get("/api/health")
def health():
    """Health check with DB status."""
    db_ok = False
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        release_db(conn)
        db_ok = True
    except:
        pass
    return {"status": "ok", "service": "attendance-converter", "database": "connected" if db_ok else "disconnected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
