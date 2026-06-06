import streamlit as st
import json
from core.database import (get_all_uploads, get_all_records, update_record,
                            update_upload_status, get_connection)
from core.validation import validate_record, get_confidence_color, get_confidence_label, fields_needing_review

st.set_page_config(page_title="Review", page_icon="🔍", layout="wide")
st.title("🔍 Review Extracted Records")

# ── Select upload ────────────────────────────────────────────────
uploads = get_all_uploads()
extracted_uploads = [u for u in uploads if u["status"] in ("extracted", "reviewed")]

if not extracted_uploads:
    st.info("No extracted documents yet. Go to **Upload** to process a document.")
    st.stop()

options = {f"{u['filename']} (ID: {u['id']}) — {u['status']}": u["id"] for u in extracted_uploads}
selected_label = st.selectbox("Select a document to review:", list(options.keys()))
upload_id = options[selected_label]

# Get all records for this upload
conn = get_connection()
rows = conn.execute("SELECT * FROM records WHERE upload_id=?", (upload_id,)).fetchall()
conn.close()

records = []
for row in rows:
    r = dict(row)
    r["confidence_scores"] = json.loads(r["confidence_scores"] or "{}")
    r["validation_errors"] = json.loads(r["validation_errors"] or "[]")
    records.append(r)

if not records:
    st.error("No records found for this upload.")
    st.stop()

st.markdown(f"**{len(records)} record(s)** found for this document.")
st.divider()

# ── Review each record ───────────────────────────────────────────
for idx, record in enumerate(records):
    confidence_scores = record.get("confidence_scores", {})
    low_conf_fields = fields_needing_review(confidence_scores)
    errors = record.get("validation_errors", [])

    status = "✔️ Reviewed" if record.get("is_reviewed") else "⏳ Pending"
    label = f"Row {idx+1} — Record ID: {record['id']} — {status}"
    if errors:
        label += f" — ⚠️ {len(errors)} issue(s)"

    with st.expander(label, expanded=not record.get("is_reviewed")):
        if low_conf_fields:
            st.warning(f"⚠️ Low confidence in: **{', '.join(low_conf_fields)}**")
        if errors:
            st.error("❌ Validation issues: " + " | ".join(errors))

        def conf_badge(field):
            score = confidence_scores.get(field, 0)
            label = get_confidence_label(score)
            emoji = {"green": "🟢", "orange": "🟡", "red": "🔴"}[get_confidence_color(score)]
            return f"{emoji} Confidence: **{label}** ({score:.0%})"

        with st.form(f"form_{record['id']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(conf_badge("date"))
                date_val = st.text_input("Date", value=record.get("date") or "", key=f"date_{record['id']}")

                st.markdown(conf_badge("shift"))
                shift_options = ["", "I", "II", "III", "Morning", "Afternoon", "Night", "A", "B", "C", "1", "2", "3"]
                cur_shift = record.get("shift") or ""
                shift_idx = shift_options.index(cur_shift) if cur_shift in shift_options else 0
                shift_val = st.selectbox("Shift", shift_options, index=shift_idx, key=f"shift_{record['id']}")

                st.markdown(conf_badge("employee_number"))
                emp_val = st.text_input("Employee Number", value=record.get("employee_number") or "", key=f"emp_{record['id']}")

                st.markdown(conf_badge("operation_code"))
                op_val = st.text_input("Operation Code", value=record.get("operation_code") or "", key=f"op_{record['id']}")

            with col2:
                st.markdown(conf_badge("machine_number"))
                machine_val = st.text_input("Machine Number", value=record.get("machine_number") or "", key=f"mc_{record['id']}")

                st.markdown(conf_badge("work_order_number"))
                wo_val = st.text_input("Work Order Number", value=record.get("work_order_number") or "", key=f"wo_{record['id']}")

                st.markdown(conf_badge("quantity_produced"))
                qty_val = st.number_input("Quantity Produced", value=float(record.get("quantity_produced") or 0),
                                          min_value=0.0, step=1.0, key=f"qty_{record['id']}")

                st.markdown(conf_badge("time_taken"))
                time_val = st.number_input("Time Taken (hours)", value=float(record.get("time_taken") or 0),
                                           min_value=0.0, step=0.5, key=f"time_{record['id']}")

            submitted = st.form_submit_button("💾 Save & Mark Reviewed", type="primary", use_container_width=True)

        if submitted:
            updated = {
                "date": date_val, "shift": shift_val, "employee_number": emp_val,
                "operation_code": op_val, "machine_number": machine_val,
                "work_order_number": wo_val, "quantity_produced": qty_val,
                "time_taken": time_val, "id": record["id"],
            }
            new_errors = validate_record(updated)
            updated["validation_errors"] = new_errors
            update_record(record["id"], updated)
            update_upload_status(upload_id, "reviewed")
            if new_errors:
                st.warning("Saved with issues: " + " | ".join(new_errors))
            else:
                st.success(f"✅ Record {record['id']} saved!")
            st.rerun()

        with st.expander("🔎 Raw AI Response"):
            st.code(record.get("raw_extraction", "N/A"), language="json")