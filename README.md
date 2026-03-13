# 📊 Attendance PDF → Excel Converter

> 🇯🇵 Transform Japanese attendance PDFs into clean Excel reports with one click

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success)
![Version](https://img.shields.io/badge/Version-1.1-orange)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **PDF Parsing** | Extracts employee data from Japanese attendance PDFs |
| ⏰ **Smart Time Handling** | Auto-converts `当`/`翌` prefixes to 24h+ format |
| 🧮 **Auto Calculate** | Working hours computed from clock-in/out times |
| 📥 **Excel Export** | Beautiful `.xlsx` with headers, borders & auto-width |
| 👀 **Preview Mode** | See extracted data before downloading |
| 🎨 **Modern UI** | Dark-themed drag & drop web interface |

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
🐍 Python 3.13    — Core language
⚡ FastAPI        — Web framework
📑 pdfplumber     — PDF text/table extraction
📗 openpyxl       — Excel generation
🌐 HTML/CSS/JS    — Frontend (dark theme)
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

| Method | Endpoint | Description |
|:------:|----------|-------------|
| `GET` | `/` | 🖥️ Web interface |
| `POST` | `/api/convert` | 📤 Upload PDF → Download Excel |
| `POST` | `/api/preview` | 👁️ Upload PDF → JSON preview |
| `GET` | `/api/health` | 💚 Health check |

---

## 📁 Project Structure

```
attendance/
├── 📄 main.py        # FastAPI app + PDF parser + Excel builder
├── 🎨 index.html     # Web UI (upload, preview, download)
├── 🚫 .gitignore
└── 📖 README.md      # You are here!
```

---

## 📜 Version History

| Version | Date | Description |
|:-------:|------|-------------|
| `v1.1` | 2026-03-13 | 🔧 Fix Time to Leave +24: only end time, start stays raw |
| `v1.0` | 2026-03-13 | 🎉 Initial stable release |

---

<div align="center">

**Made with ❤️ for efficient attendance management**

</div>
