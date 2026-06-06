import streamlit as st
import pandas as pd
import io
from core.database import search_records, get_connection

st.set_page_config(page_title="History", page_icon="📋", layout="wide")
st.title("📋 Search & History")

# ── Sidebar tools ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗑️ Database Tools")
    if st.button("Clear All Records", type="secondary", use_container_width=True):
        conn = get_connection()
        conn.execute("DELETE FROM records")
        conn.execute("DELETE FROM uploads")
        conn.commit()
        conn.close()
        st.success("All records cleared!")
        st.rerun()

# ── Filters ──────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    keyword = st.text_input("🔍 Search", placeholder="Work order, machine, employee...")
with col2:
    shift_filter = st.selectbox("Shift", ["All", "I", "II", "III", "Morning", "Afternoon", "Night", "A", "B", "C"])
with col3:
    reviewed_filter = st.selectbox("Status", ["All", "Reviewed", "Pending"])

records = search_records(keyword, shift_filter, reviewed_filter)
st.markdown(f"**{len(records)} record(s) found**")

# ── Export buttons ───────────────────────────────────────────────
if records:
    ecol1, ecol2 = st.columns(2)

    # Build export dataframe
    export_rows = []
    for r in records:
        scores = r.get("confidence_scores", {})
        errors = r.get("validation_errors", [])
        export_rows.append({
            "Record ID": r["id"],
            "File": r.get("filename", ""),
            "Date": r.get("date") or "",
            "Shift": r.get("shift") or "",
            "Employee Number": r.get("employee_number") or "",
            "Operation Code": r.get("operation_code") or "",
            "Machine Number": r.get("machine_number") or "",
            "Work Order Number": r.get("work_order_number") or "",
            "Quantity Produced": r.get("quantity_produced") or "",
            "Time Taken (hrs)": r.get("time_taken") or "",
            "Status": "Reviewed" if r.get("is_reviewed") else "Pending",
            "Validation Issues": len(errors),
            "Issue Details": "; ".join(errors) if errors else "",
            "Conf: Date": scores.get("date", ""),
            "Conf: Shift": scores.get("shift", ""),
            "Conf: Employee": scores.get("employee_number", ""),
            "Conf: Machine": scores.get("machine_number", ""),
            "Conf: Work Order": scores.get("work_order_number", ""),
            "Conf: Qty": scores.get("quantity_produced", ""),
        })

    export_df = pd.DataFrame(export_rows)

    with ecol1:
        # CSV export
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Export as CSV",
            data=csv_data,
            file_name="biztel_records.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with ecol2:
        # Excel export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Records")
            # Auto-size columns
            ws = writer.sheets["Records"]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
        buffer.seek(0)
        st.download_button(
            label="⬇️ Export as Excel (.xlsx)",
            data=buffer,
            file_name="biztel_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

st.divider()

# ── Table view ───────────────────────────────────────────────────
if not records:
    st.info("No records match your filters.")
else:
    rows = []
    for r in records:
        errors = r.get("validation_errors", [])
        rows.append({
            "ID": r["id"],
            "File": r.get("filename", "—"),
            "Date": r.get("date") or "—",
            "Shift": r.get("shift") or "—",
            "Employee": r.get("employee_number") or "—",
            "Machine": r.get("machine_number") or "—",
            "Work Order": r.get("work_order_number") or "—",
            "Qty": r.get("quantity_produced") or "—",
            "Time (h)": r.get("time_taken") or "—",
            "Status": "✔️ Reviewed" if r.get("is_reviewed") else "⏳ Pending",
            "⚠️ Issues": len(errors),
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "File": st.column_config.TextColumn(width="medium"),
            "Date": st.column_config.TextColumn(width="small"),
            "Shift": st.column_config.TextColumn(width="small"),
            "Employee": st.column_config.TextColumn(width="medium"),
            "Machine": st.column_config.TextColumn(width="medium"),
            "Work Order": st.column_config.TextColumn(width="medium"),
            "Qty": st.column_config.NumberColumn(width="small"),
            "Time (h)": st.column_config.NumberColumn(width="small"),
            "Status": st.column_config.TextColumn(width="medium"),
            "⚠️ Issues": st.column_config.NumberColumn(width="small"),
        }
    )

    # ── Detail view ───────────────────────────────────────────────
    st.divider()
    st.subheader("Record Details")
    record_ids = {f"ID {r['id']} — {r.get('filename','')} | {r.get('date','?')} Shift {r.get('shift','?')}": r["id"] for r in records}
    selected = st.selectbox("Select a record to view details:", list(record_ids.keys()))
    sel_id = record_ids[selected]
    sel_record = next(r for r in records if r["id"] == sel_id)

    fields = [
        ("Date", "date"), ("Shift", "shift"),
        ("Employee #", "employee_number"), ("Operation Code", "operation_code"),
        ("Machine #", "machine_number"), ("Work Order #", "work_order_number"),
        ("Qty Produced", "quantity_produced"), ("Time Taken", "time_taken"),
    ]
    col1, col2 = st.columns(2)
    for i, (label, key) in enumerate(fields):
        val = sel_record.get(key)
        score = sel_record.get("confidence_scores", {}).get(key, None)
        badge = ""
        if score is not None:
            badge = f" {'🟢' if score>=0.85 else '🟡' if score>=0.60 else '🔴'} {score:.0%}"
        with (col1 if i % 2 == 0 else col2):
            st.metric(label=f"{label}{badge}", value=str(val) if val else "—")

    errors = sel_record.get("validation_errors", [])
    if errors:
        st.warning("**Validation Issues:**")
        for e in errors:
            st.write(f"  • {e}")
    else:
        st.success("✅ No validation issues.")