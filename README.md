# BiztelAI – Manufacturing Document Digitizer

An AI-powered web application that digitizes handwritten manufacturing/operational documents and converts them into structured, reviewable records with analytics and validation workflows.

## Features

- **Document Upload** – Upload JPG/PNG images of handwritten manufacturing documents
- **AI Extraction** – Automatically extracts all data rows using Groq Vision AI (LLaMA 4)
- **Multi-row Support** – Handles tables with multiple data rows per document
- **Confidence Scoring** – Each extracted field is assigned a confidence score (🟢🟡🔴)
- **Review Workflow** – Editable forms to correct and confirm extracted data
- **Validation Engine** – Business rules catch missing fields, invalid shifts, suspicious quantities, duplicate work orders
- **Search & History** – Filter and browse all processed records
- **Dashboard Analytics** – Shift-wise, machine-wise, quantity summaries and charts

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend + Backend | Python + Streamlit |
| AI / Vision OCR | Groq API (meta-llama/llama-4-scout-17b-16e-instruct) |
| Database | SQLite (via Python sqlite3) |

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd biztel-ai
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

Get a free Groq API key at: https://console.groq.com

### 5. Run the app
```bash
streamlit run main.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
biztel-ai/
├── main.py                  # Streamlit entry point
├── pages/
│   ├── 1_Upload.py          # Document upload + AI extraction
│   ├── 2_Review.py          # Edit and confirm records
│   ├── 3_History.py         # Search and browse records
│   └── 4_Dashboard.py       # Analytics dashboard
├── core/
│   ├── database.py          # SQLite setup and all DB helpers
│   ├── extraction.py        # Groq Vision API integration
│   └── validation.py        # Business rules and validation logic
├── uploads/                 # Uploaded files (auto-created)
├── .env.example
├── requirements.txt
├── README.md
└── AGENTS.md
```

## Assumptions & Tradeoffs

- **SQLite over PostgreSQL** – Zero setup, sufficient for prototype scale
- **Groq over OpenAI** – Free tier available, fast inference, good vision capability
- **Streamlit over React** – Rapid development, pure Python, sufficient for prototype UI
- **Single file per upload** – Each image is processed independently; multi-page PDFs not supported in this version
- **Roman numeral shifts (I/II/III)** – Supported in addition to A/B/C and Morning/Afternoon/Night
- **Duplicate WO detection** – Warns but does not block saving (operator may override)
