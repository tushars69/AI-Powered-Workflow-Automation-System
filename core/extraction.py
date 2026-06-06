import os
import json
import base64
import tempfile
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Best available Groq vision model (as of June 2026)
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

EXTRACTION_PROMPT = """
You are an AI assistant that extracts structured data from handwritten manufacturing/operational documents.

This document may contain a TABLE with MULTIPLE ROWS of data. Extract ALL rows that have data filled in.

For each row, extract these fields:
- date (format: YYYY-MM-DD if possible, otherwise as written)
- shift (e.g., "I", "II", "III", "Morning", "Afternoon", "Night", "A", "B", "C")
- employee_number (the Emp. No column)
- operation_code (the Opn Code column)
- machine_number (the Machine No column)
- work_order_number (the Work Order No column)
- quantity_produced (Qty. Prod. - numeric)
- time_taken (Time taken in hrs - numeric)

For each field assign a confidence score 0.0 to 1.0:
- 1.0 = clearly legible
- 0.7-0.9 = mostly clear
- 0.4-0.6 = partially legible
- 0.0-0.3 = unclear/guessed

You MUST respond ONLY with a valid JSON object. No markdown, no backticks, no extra text.
Use this exact structure:

{
  "rows": [
    {
      "date": "...",
      "shift": "...",
      "employee_number": "...",
      "operation_code": "...",
      "machine_number": "...",
      "work_order_number": "...",
      "quantity_produced": 25,
      "time_taken": 4.0,
      "confidence_scores": {
        "date": 0.9,
        "shift": 0.95,
        "employee_number": 0.85,
        "operation_code": 0.8,
        "machine_number": 0.9,
        "work_order_number": 0.85,
        "quantity_produced": 0.95,
        "time_taken": 0.95
      }
    }
  ],
  "notes": "any observations about document quality"
}

Only include rows that have at least some data. Skip completely empty rows.
Use null for any individual field that is completely missing or illegible.
"""

def encode_image_file(file_path: str) -> tuple[str, str]:
    """Encode a regular image file to base64."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    with open(file_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type

def pdf_to_images(pdf_path: str) -> list[str]:
    """
    Convert each page of a PDF to a PNG image.
    Returns list of temp image file paths.
    """
    import fitz  # pymupdf
    doc = fitz.open(pdf_path)
    image_paths = []
    tmp_dir = tempfile.mkdtemp()
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at 2x scale for better OCR quality
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_path = os.path.join(tmp_dir, f"page_{page_num + 1}.png")
        pix.save(img_path)
        image_paths.append(img_path)
    doc.close()
    return image_paths

def _call_vision_api(base64_image: str, media_type: str) -> str:
    """Send one image to Groq Vision and return raw text response."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        model=VISION_MODEL,
        temperature=0.1,
    )
    return chat_completion.choices[0].message.content.strip()

def _parse_rows(raw_text: str) -> tuple[list[dict], str]:
    """Parse raw JSON text into list of row dicts. Returns (rows, notes)."""
    text = raw_text
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    parsed = json.loads(text)
    rows = parsed.get("rows", [])
    notes = parsed.get("notes", "")

    result = []
    for row in rows:
        for num_field in ["quantity_produced", "time_taken"]:
            val = row.get(num_field)
            if val is not None:
                try:
                    row[num_field] = float(str(val).replace(",", "").split()[0])
                except (ValueError, IndexError):
                    row[num_field] = None
        if "confidence_scores" not in row:
            row["confidence_scores"] = {k: 0.5 for k in [
                "date", "shift", "employee_number", "operation_code",
                "machine_number", "work_order_number", "quantity_produced", "time_taken"
            ]}
        row["raw_extraction"] = raw_text
        row["notes"] = notes
        row["validation_errors"] = []
        result.append(row)
    return result, notes

def extract_from_document(file_path: str) -> list[dict]:
    """
    Accepts images (JPG/PNG/WEBP) or PDFs.
    PDFs are converted page-by-page to images before extraction.
    Returns a LIST of row dicts — one per data row found across all pages.
    """
    try:
        suffix = Path(file_path).suffix.lower()

        # ── PDF: convert each page to image, extract from each ──
        if suffix == ".pdf":
            image_paths = pdf_to_images(file_path)
            if not image_paths:
                return [_error_result("PDF has no pages")]

            all_rows = []
            for img_path in image_paths:
                try:
                    b64, media_type = encode_image_file(img_path)
                    raw_text = _call_vision_api(b64, media_type)
                    rows, _ = _parse_rows(raw_text)
                    all_rows.extend(rows)
                except Exception as e:
                    # One page failing shouldn't kill the whole PDF
                    all_rows.append(_error_result(f"Page extraction error: {e}"))
                finally:
                    # Clean up temp image
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass

            return all_rows if all_rows else [_error_result("No data extracted from PDF")]

        # ── Image: direct extraction ─────────────────────────────
        else:
            b64, media_type = encode_image_file(file_path)
            raw_text = _call_vision_api(b64, media_type)
            rows, _ = _parse_rows(raw_text)
            return rows if rows else [_error_result("No rows extracted", raw_text)]

    except json.JSONDecodeError as e:
        raw = raw_text if 'raw_text' in locals() else ""
        return [_error_result(f"JSON parse error: {e}", raw)]
    except Exception as e:
        return [_error_result(str(e))]

def _error_result(error_msg: str, raw: str = "") -> dict:
    return {
        "date": None, "shift": None, "employee_number": None,
        "operation_code": None, "machine_number": None,
        "work_order_number": None, "quantity_produced": None, "time_taken": None,
        "confidence_scores": {k: 0.0 for k in [
            "date", "shift", "employee_number", "operation_code",
            "machine_number", "work_order_number", "quantity_produced", "time_taken"
        ]},
        "notes": f"Extraction failed: {error_msg}",
        "raw_extraction": raw,
        "validation_errors": [f"Extraction error: {error_msg}"],
    }