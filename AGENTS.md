# AI Workflow Document

## AI Tools Used

| Tool | Purpose |
|---|---|
| Claude (claude.ai) | Primary development assistant — architecture, code generation, debugging |
| Groq API (LLaMA 4 Scout) | Vision model for extracting structured data from document images |

## How AI Was Used During Development

### Architecture & Planning
Claude was used to design the full project structure — deciding on Streamlit + SQLite as the simplest viable stack, planning the 4-page navigation flow, and defining the database schema upfront before writing any code.

### Code Generation
All core files were generated with Claude assistance:
- `core/database.py` – Full SQLite schema and all CRUD helpers
- `core/extraction.py` – Groq Vision API integration with multi-row JSON extraction
- `core/validation.py` – Business rules (mandatory fields, shift validation, duplicate WO detection)
- All 4 Streamlit pages – Upload, Review, History, Dashboard

### Prompting Strategy
For the extraction prompt sent to LLaMA Vision:
- Explicitly instructed to return **only valid JSON**, no markdown
- Defined exact JSON schema with `rows[]` array for multi-row documents
- Asked for per-field confidence scores (0.0–1.0) inline with each row
- Instructed to skip empty rows and use `null` for illegible fields

### Debugging Workflow
- **Model deprecation error** – Groq's `llama-3.2-11b-vision-preview` was decommissioned; Claude identified the replacement model `meta-llama/llama-4-scout-17b-16e-instruct`
- **List vs dict bug** – When extraction changed from single-row to multi-row (returning a list), the upload page still called `.get()` on the list; Claude identified the mismatch and fixed both files together
- **Shift validation false positives** – Roman numerals (I, II, III) used in the dataset weren't in the valid shifts set; fixed by expanding `VALID_SHIFTS`

## Extra Features Added Beyond Requirements

These were product decisions made to improve real-world usability:

- **Batch Upload** – Upload multiple images/PDFs at once with a progress bar. In a real factory, operators process dozens of sheets daily — one-by-one upload would be unusable.
- **PDF Support** – PDFs are converted page-by-page to images using PyMuPDF before sending to the vision model, since Groq's API only accepts images.
- **Export to CSV/Excel** – Operations managers need data in spreadsheets. Added one-click export with confidence scores included as extra columns.
- **AI Extraction Quality Dashboard** – Added per-field average confidence charts and a validation error breakdown chart so supervisors can see which fields the AI struggles with most.
- **Multi-row extraction** – The sample dataset has tables with 3+ rows per image. Redesigned the extraction prompt and response schema to return a `rows[]` array instead of a single record.

## Areas Where AI Helped Most

- **Boilerplate elimination** – Database helpers, form layouts, and Streamlit page structure written in seconds
- **Prompt engineering** – Structuring the extraction prompt to reliably return parseable JSON with confidence scores
- **Cross-file consistency** – When one file's return type changed, Claude identified all downstream callers that needed updating

## Areas Requiring Manual Intervention

- **Model selection** – Had to check Groq's live model list to find the correct current vision model name
- **UI tweaking** – Streamlit's dark theme caused invisible text in styled dataframes; required visual inspection to catch
- **Dataset-specific field names** – The sample dataset uses "Opn Code" and "MC-XXX" format; the prompt needed manual tuning after seeing actual document images