import streamlit as st
import os
import time
from core.database import insert_upload, update_upload_status, get_all_uploads, insert_record
from core.extraction import extract_from_document
from core.validation import validate_record

st.set_page_config(page_title="Upload", page_icon="📤", layout="wide")
st.title("📤 Upload Documents")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── File uploader — accepts MULTIPLE files ───────────────────────
st.subheader("Upload manufacturing documents")
uploaded_files = st.file_uploader(
    "Choose images or PDFs — you can select multiple",
    type=["jpg", "jpeg", "png", "webp", "pdf"],
    accept_multiple_files=True,
    help="Hold Ctrl/Cmd to select multiple files. PDFs are processed page by page.",
)

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} file(s) selected:**")
    
    # Preview grid
    cols = st.columns(min(len(uploaded_files), 4))
    for i, f in enumerate(uploaded_files):
        with cols[i % 4]:
            if f.type == "application/pdf":
                st.markdown("📄")
                st.caption(f.name)
                st.caption(f"{f.size/1024:.1f} KB · PDF")
            else:
                st.image(f, caption=f.name, use_container_width=True)
                st.caption(f"{f.size/1024:.1f} KB")

    st.divider()

    if st.button(f"🚀 Extract All {len(uploaded_files)} Document(s) with AI", type="primary", use_container_width=True):
        
        all_results = []  # collect summary for all files
        
        overall_progress = st.progress(0, text="Starting batch extraction...")
        
        for file_idx, uploaded_file in enumerate(uploaded_files):
            overall_progress.progress(
                file_idx / len(uploaded_files),
                text=f"Processing {file_idx+1}/{len(uploaded_files)}: {uploaded_file.name}"
            )

            # Save to disk
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            upload_id = insert_upload(uploaded_file.name, file_path)

            with st.spinner(f"🤖 Extracting from **{uploaded_file.name}**..."):
                rows = extract_from_document(file_path)

            record_ids = []
            total_errors = 0
            for row in rows:
                errors = validate_record(row)
                row["validation_errors"] = errors
                total_errors += len(errors)
                record_id = insert_record(upload_id, row)
                record_ids.append(record_id)

            update_upload_status(upload_id, "extracted")
            all_results.append({
                "file": uploaded_file.name,
                "rows": len(rows),
                "records": record_ids,
                "errors": total_errors,
                "data": rows,
            })

        overall_progress.progress(1.0, text="✅ All files processed!")

        # ── Batch summary table ──────────────────────────────────
        st.subheader("📊 Batch Extraction Summary")
        summary_cols = st.columns(4)
        total_rows = sum(r["rows"] for r in all_results)
        total_err = sum(r["errors"] for r in all_results)
        summary_cols[0].metric("Files Processed", len(all_results))
        summary_cols[1].metric("Total Rows Extracted", total_rows)
        summary_cols[2].metric("Records Created", sum(len(r["records"]) for r in all_results))
        summary_cols[3].metric("Validation Issues", total_err, delta=f"{total_err} issues" if total_err else None, delta_color="inverse")

        st.divider()

        # ── Per-file results ─────────────────────────────────────
        for result in all_results:
            status_icon = "✅" if result["errors"] == 0 else "⚠️"
            with st.expander(f"{status_icon} **{result['file']}** — {result['rows']} row(s), {result['errors']} issue(s)", expanded=True):
                fields = ["date", "shift", "employee_number", "operation_code",
                          "machine_number", "work_order_number", "quantity_produced", "time_taken"]
                
                for i, (row, record_id) in enumerate(zip(result["data"], result["records"])):
                    scores = row.get("confidence_scores", {})
                    errors = row.get("validation_errors", [])
                    st.markdown(f"**Row {i+1}** — Record ID: `{record_id}`")
                    
                    mcols = st.columns(4)
                    for j, field in enumerate(fields):
                        val = row.get(field)
                        score = scores.get(field, 0)
                        icon = "🟢" if score >= 0.85 else "🟡" if score >= 0.60 else "🔴"
                        with mcols[j % 4]:
                            st.metric(
                                label=f"{icon} {field.replace('_',' ').title()}",
                                value=str(val) if val is not None else "—",
                                help=f"Confidence: {score:.0%}"
                            )
                    if errors:
                        st.warning(f"⚠️ {' | '.join(errors)}")
                    else:
                        st.success("✅ All validations passed!")
                    if i < len(result["data"]) - 1:
                        st.divider()

        st.info("👉 Go to **Review** to edit records or **History** to browse all.")

# ── Recent uploads ───────────────────────────────────────────────
st.divider()
st.subheader("📁 Recent Uploads")
uploads = get_all_uploads()
if uploads:
    for u in uploads[:10]:
        icon = {"pending": "⏳", "extracted": "✅", "reviewed": "✔️"}.get(u["status"], "❓")
        st.write(f"{icon} `{u['filename']}` — {u['uploaded_at'][:19]} — **{u['status']}**")
else:
    st.info("No uploads yet.")