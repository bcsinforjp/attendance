# 📊 Attendance PDF → Excel Converter Stable + Management Dashboard

> 🇯🇵 Transform Japanese attendance PDFs into clean roster-based Excel reports + SQLite database + Grafana management dashboard

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success)
![Version](https://img.shields.io/badge/Version-2.0-orange)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **PDF Parsing** | Extracts employee data from Japanese attendance PDFs |
| ⏰ **Smart Time Handling** | Auto-converts `当`/`翌` prefixes to 24h+ format |
| 🧮 **Auto Calculate** | Working hours computed from clock-in/out times |
| 📥 **Excel Export** | Beautiful `.xlsx` with headers, borders & auto-width |
| 👀 **Preview Mode** | See extracted data before downloading |
| 🧾 **Roster Output** | Excel rows follow a fixed employee master list with blanks for missing data |
| 🗂️ **Multi-File Upload** | Convert multiple PDFs at once and download a ZIP bundle |
| 💾 **SQLite Database** | Converted uploads are saved locally for dashboard summaries |
| 📊 **Grafana Dashboard** | Management dashboard with charts & analytics |
| 🎨 **Modern UI** | Drag-and-drop web interface with single and multi-file support |

---

## 🕐 Time Conversion Logic

### Commute Time (Start)
```
当11:22  →  11:22   (Same day, raw)
翌07:47  →   7:47   (Raw, no +24)
__:__    →  blank    (No data)
```

### Time to Leave (End)
```
当19:33  →  19:33   (Same day, raw)
翌03:57  →  27:57   (Next day +24h)
01:00    →  25:00   (After midnight +24h, no prefix)
__:__    →  blank    (No data)
----     →  blank    (No data)
```

---

## 🛠 Tech Stack

```
🐍 Python 3.13      — Core language
⚡ FastAPI          — Web framework + REST API
📑 pdfplumber       — PDF text/table extraction
📗 openpyxl         — Excel generation
🗄️ SQLite          — Embedded database
📊 Grafana          — Management dashboard
🌐 HTML/CSS/JS      — Frontend (dark theme)
```

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn pdfplumber openpyxl python-multipart

# Run server
cd projects/attendance
uvicorn main:app --host 0.0.0.0 --port 8002
```

Open `http://localhost:8002` and drop your PDF! 🎉

---

## 📡 API Endpoints

### Attendance
| Method | Endpoint | Description |
|:------:|----------|-------------|
| `GET` | `/` | 🖥️ Web interface |
| `POST` | `/api/convert` | 📤 Upload PDF → Download Excel + Save to DB |
| `POST` | `/api/convert-multiple` | 🗂️ Upload many PDFs → Download ZIP bundle + Save to DB |
| `POST` | `/api/preview` | 👁️ Upload PDF → JSON preview |
| `POST` | `/api/preview-multiple` | 👁️ Preview a multi-file upload batch |
| `GET` | `/api/health` | 💚 Health check + DB status |

### Management Dashboard
| Method | Endpoint | Description |
|:------:|----------|-------------|
| `GET` | `/api/dashboard/summary` | 📊 Monthly summary (employees, avg hours, daily stats) |
| `GET` | `/api/dashboard/employees` | 👥 All employees with summary |
| `GET` | `/api/dashboard/employee/{code}` | 🔍 Individual employee details |
| `GET` | `/api/dashboard/months` | 📅 Available months with data |

---

## 📊 Grafana Dashboard

Access at `http://<server-ip>/grafana/`

**Panels:**
- 👥 Total Employees This Month
- 📋 Total Records
- ⏱️ Average Working Hours
- 📅 Days in Month
- 📈 Daily Attendance Count (chart)
- 📊 Avg Working Hours by Day (chart)
- 🏆 Top 10 Workers (table)
- ⚠️ Late Arrivals After 9:00 (table)
- 🔄 Upload Batches History

---

## 📁 Project Structure

```
attendance/
├── 📄 main.py        # FastAPI app + PDF parser + Excel builder + DB + API
├── 🎨 index.html     # Web UI (upload, preview, download)
├── 👥 employee_roster.json  # Fixed output roster for Excel generation
├── 🚫 .gitignore
└── 📖 README.md      # You are here!
```

---

## 📜 Version History

| Version | Date | Description |
|:-------:|------|-------------|
| `stable-roster` | 2026-03-31 | 🎯 Fixed roster-based Excel output + SQLite persistence + multi-file ZIP export |
| `v2.0` | 2026-03-13 | 🎉 PostgreSQL + Grafana management dashboard + DB API |
| `v1.1` | 2026-03-13 | 🔧 Fix Time to Leave +24: only end time, start stays raw |
| `v1.0` | 2026-03-13 | 🎉 Initial stable release |

---

<div align="center">

**Made with ❤️ for efficient attendance management**

</div>
