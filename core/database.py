import sqlite3
import os
import json
from datetime import datetime

DB_PATH = "biztel.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn

def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Table 1: tracks every uploaded file
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',   -- pending | extracted | reviewed
                file_path TEXT
            )
        """)
        # Table 2: stores extracted + reviewed records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL,
                date TEXT,
                shift TEXT,
                employee_number TEXT,
                operation_code TEXT,
                machine_number TEXT,
                work_order_number TEXT,
                quantity_produced REAL,
                time_taken REAL,
                confidence_scores TEXT,   -- JSON string: {"date": 0.95, "shift": 0.80, ...}
                validation_errors TEXT,   -- JSON string: ["Missing shift", ...]
                is_reviewed INTEGER DEFAULT 0,
                reviewed_at TEXT,
                raw_extraction TEXT,      -- full AI response for debugging
                FOREIGN KEY (upload_id) REFERENCES uploads(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()

# ── Upload helpers ──────────────────────────────────────────────

def insert_upload(filename, file_path):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO uploads (filename, uploaded_at, status, file_path)
            VALUES (?, ?, ?, ?)
        """, (filename, datetime.now().isoformat(), "pending", file_path))
        upload_id = cursor.lastrowid
        conn.commit()
        return upload_id
    finally:
        conn.close()

def update_upload_status(upload_id, status):
    conn = get_connection()
    try:
        conn.execute("UPDATE uploads SET status=? WHERE id=?", (status, upload_id))
        conn.commit()
    finally:
        conn.close()

def get_all_uploads():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM uploads ORDER BY uploaded_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_upload_by_id(upload_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM uploads WHERE id=?", (upload_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ── Record helpers ──────────────────────────────────────────────

def insert_record(upload_id, data: dict):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO records (
                upload_id, date, shift, employee_number, operation_code,
                machine_number, work_order_number, quantity_produced, time_taken,
                confidence_scores, validation_errors, raw_extraction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            upload_id,
            data.get("date"),
            data.get("shift"),
            data.get("employee_number"),
            data.get("operation_code"),
            data.get("machine_number"),
            data.get("work_order_number"),
            data.get("quantity_produced"),
            data.get("time_taken"),
            json.dumps(data.get("confidence_scores", {})),
            json.dumps(data.get("validation_errors", [])),
            data.get("raw_extraction", "")
        ))
        record_id = cursor.lastrowid
        conn.commit()
        return record_id
    finally:
        conn.close()

def update_record(record_id, data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE records SET
                date=?, shift=?, employee_number=?, operation_code=?,
                machine_number=?, work_order_number=?, quantity_produced=?,
                time_taken=?, is_reviewed=1, reviewed_at=?,
                validation_errors=?
            WHERE id=?
        """, (
            data.get("date"),
            data.get("shift"),
            data.get("employee_number"),
            data.get("operation_code"),
            data.get("machine_number"),
            data.get("work_order_number"),
            data.get("quantity_produced"),
            data.get("time_taken"),
            datetime.now().isoformat(),
            json.dumps(data.get("validation_errors", [])),
            record_id
        ))
        conn.commit()
    finally:
        conn.close()

def get_record_by_upload(upload_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM records WHERE upload_id=?", (upload_id,)).fetchone()
        if row:
            r = dict(row)
            r["confidence_scores"] = json.loads(r["confidence_scores"] or "{}")
            r["validation_errors"] = json.loads(r["validation_errors"] or "[]")
            return r
        return None
    finally:
        conn.close()

def get_all_records():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT r.*, u.filename FROM records r
            JOIN uploads u ON r.upload_id = u.id
            ORDER BY r.id DESC
        """).fetchall()
        result = []
        for row in rows:
            r = dict(row)
            r["confidence_scores"] = json.loads(r["confidence_scores"] or "{}")
            r["validation_errors"] = json.loads(r["validation_errors"] or "[]")
            result.append(r)
        return result
    finally:
        conn.close()

def search_records(keyword="", shift_filter="All", reviewed_filter="All"):
    conn = get_connection()
    try:
        query = """
            SELECT r.*, u.filename FROM records r
            JOIN uploads u ON r.upload_id = u.id
            WHERE 1=1
        """
        params = []

        if keyword:
            query += """ AND (
                r.work_order_number LIKE ? OR r.machine_number LIKE ?
                OR r.employee_number LIKE ? OR r.operation_code LIKE ?
            )"""
            like = f"%{keyword}%"
            params.extend([like, like, like, like])

        if shift_filter != "All":
            query += " AND r.shift = ?"
            params.append(shift_filter)

        if reviewed_filter == "Reviewed":
            query += " AND r.is_reviewed = 1"
        elif reviewed_filter == "Pending":
            query += " AND r.is_reviewed = 0"

        query += " ORDER BY r.id DESC"
        rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            r = dict(row)
            r["confidence_scores"] = json.loads(r["confidence_scores"] or "{}")
            r["validation_errors"] = json.loads(r["validation_errors"] or "[]")
            result.append(r)
        return result
    finally:
        conn.close()

def get_dashboard_stats():
    conn = get_connection()
    try:
        total_uploads = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        total_records = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        reviewed = conn.execute("SELECT COUNT(*) FROM records WHERE is_reviewed=1").fetchone()[0]

        all_records = conn.execute("SELECT validation_errors FROM records").fetchall()
        failed = sum(1 for r in all_records if r[0] and r[0] != "[]")

        shift_summary = conn.execute("""
            SELECT shift, COUNT(*) as count, SUM(quantity_produced) as total_qty
            FROM records WHERE shift IS NOT NULL AND shift != ''
            GROUP BY shift
        """).fetchall()

        machine_summary = conn.execute("""
            SELECT machine_number, COUNT(*) as count, SUM(quantity_produced) as total_qty
            FROM records WHERE machine_number IS NOT NULL AND machine_number != ''
            GROUP BY machine_number
        """).fetchall()

        return {
            "total_uploads": total_uploads,
            "total_records": total_records,
            "reviewed": reviewed,
            "validation_failures": failed,
            "shift_summary": [dict(r) for r in shift_summary],
            "machine_summary": [dict(r) for r in machine_summary],
        }
    finally:
        conn.close()
        