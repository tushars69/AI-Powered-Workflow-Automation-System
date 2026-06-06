# AI Workflow Document

## AI Tools Used

| Tool | Purpose |
|---|---|
| Claude (claude.ai) | Used as a coding assistant for specific parts |
| Groq API (LLaMA 4 Scout) | Vision model for document extraction |

## How I Used AI During Development

AI was used as a **helper**. I designed the architecture, 
made all product decisions, and wrote significant portions of the code myself. 
AI was used mostly to speed up repetitive boilerplate and debug specific errors.

### What I Designed and Decided

- Chose Streamlit + SQLite as the stack — wanted pure Python, zero frontend 
  overhead, fast to iterate
- Designed the 4-page navigation flow (Upload → Review → History → Dashboard)
- Decided to extract ALL rows from a table, not just the first row — noticed 
  the dataset had multi-row tables and redesigned the schema myself
- Chose PyMuPDF for PDF-to-image conversion after researching options
- Designed the validation rules based on reading the assignment requirements:
  mandatory fields, shift format checks, duplicate work order detection, 
  quantity range checks
- Decided to add batch upload, Excel export, and AI quality dashboard as 
  extra features based on what would actually be useful in a factory setting

### Where I Used AI Assistance

- Generated initial boilerplate for SQLite helper functions (insert, update, 
  fetch) which I then reviewed and modified
- Got help writing the Groq API call structure
- Used Claude to help debug two specific errors (described below)

### Debugging I Did Myself

- Noticed the Groq model was decommissioned from the error message, researched 
  the current model list on Groq's docs, updated it myself
- Caught the invisible text bug in the history table by visually testing the UI 
  and traced it to pandas `.style.apply()` conflicting with Streamlit's dark theme
- Identified that Roman numeral shifts (I, II, III) were being flagged as invalid 
  — found the VALID_SHIFTS set in validation.py and added them myself

### Prompting Strategy I Developed

Spent time iterating on the extraction prompt to get reliable JSON output:
- Added strict instruction to return only JSON with no markdown fences
- Designed the `rows[]` array schema myself to handle multi-row tables
- Added per-field confidence scores after realizing single-document confidence 
  wasn't granular enough for the review workflow
- Tested against actual dataset images and refined the prompt based on results

## What I Would Do Differently With More Time

- Add user authentication so multiple operators can use the system
- Store extracted images with bounding box annotations per field
- Add a re-extract button on the Review page
- Write unit tests for the validation rules