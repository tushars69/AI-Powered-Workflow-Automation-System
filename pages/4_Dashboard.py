import streamlit as st
import pandas as pd
from core.database import get_dashboard_stats, get_all_records

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Operations Dashboard")

stats = get_dashboard_stats()
records = get_all_records()

if not records:
    st.info("No records yet. Upload and process some documents to see analytics.")
    st.stop()

# ── KPI Row 1: Core counts ────────────────────────────────────────
st.subheader("Overview")
k1, k2, k3, k4 = st.columns(4)
k1.metric("📁 Total Uploads", stats["total_uploads"])
k2.metric("📝 Records Extracted", stats["total_records"])
k3.metric("✔️ Reviewed", stats["reviewed"],
          delta=f"{stats['total_records']-stats['reviewed']} pending",
          delta_color="inverse")
k4.metric("⚠️ Validation Failures", stats["validation_failures"],
          delta=f"{stats['validation_failures']/max(stats['total_records'],1)*100:.0f}% of records",
          delta_color="inverse")

st.divider()

# ── KPI Row 2: AI accuracy stats ─────────────────────────────────
st.subheader("🤖 AI Extraction Quality")

all_scores = []
field_score_sums = {}
field_score_counts = {}
fields = ["date","shift","employee_number","operation_code","machine_number","work_order_number","quantity_produced","time_taken"]

for r in records:
    scores = r.get("confidence_scores", {})
    for f in fields:
        s = scores.get(f)
        if s is not None:
            all_scores.append(s)
            field_score_sums[f] = field_score_sums.get(f, 0) + s
            field_score_counts[f] = field_score_counts.get(f, 0) + 1

avg_conf = sum(all_scores) / len(all_scores) if all_scores else 0
high_conf = sum(1 for s in all_scores if s >= 0.85)
low_conf  = sum(1 for s in all_scores if s < 0.60)

a1, a2, a3, a4 = st.columns(4)
a1.metric("Avg Confidence", f"{avg_conf:.0%}")
a2.metric("🟢 High Confidence Fields", f"{high_conf/max(len(all_scores),1)*100:.0f}%")
a3.metric("🔴 Low Confidence Fields", f"{low_conf/max(len(all_scores),1)*100:.0f}%")

# Most problematic field
if field_score_sums:
    worst_field = min(field_score_sums, key=lambda f: field_score_sums[f]/max(field_score_counts.get(f,1),1))
    worst_avg = field_score_sums[worst_field] / field_score_counts[worst_field]
    a4.metric("🔴 Hardest Field to Read", worst_field.replace("_"," ").title(), delta=f"{worst_avg:.0%} avg conf", delta_color="inverse")

# Per-field confidence bar chart
field_avgs = {
    f.replace("_"," ").title(): round(field_score_sums[f]/field_score_counts[f], 3)
    for f in fields if f in field_score_sums
}
df_conf = pd.DataFrame({"Field": list(field_avgs.keys()), "Avg Confidence": list(field_avgs.values())})
st.bar_chart(df_conf.set_index("Field"), height=220)

st.divider()

# ── Operational summaries ─────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔄 Shift-wise Summary")
    if stats["shift_summary"]:
        df_shift = pd.DataFrame(stats["shift_summary"])
        df_shift.columns = ["Shift", "Records", "Total Qty"]
        df_shift["Avg Qty"] = (df_shift["Total Qty"] / df_shift["Records"]).round(1)
        st.dataframe(df_shift, use_container_width=True, hide_index=True)
        st.bar_chart(df_shift.set_index("Shift")["Total Qty"], height=200)
    else:
        st.info("No shift data available.")

with col_right:
    st.subheader("🏭 Machine-wise Summary")
    if stats["machine_summary"]:
        df_machine = pd.DataFrame(stats["machine_summary"])
        df_machine.columns = ["Machine", "Records", "Total Qty"]
        df_machine["Avg Qty"] = (df_machine["Total Qty"] / df_machine["Records"]).round(1)
        st.dataframe(df_machine, use_container_width=True, hide_index=True)
        st.bar_chart(df_machine.set_index("Machine")["Total Qty"], height=200)
    else:
        st.info("No machine data available.")

st.divider()

# ── Validation error breakdown ────────────────────────────────────
st.subheader("🔍 Most Common Validation Issues")
error_counts = {}
for r in records:
    for e in r.get("validation_errors", []):
        # Bucket the error type
        if "shift" in e.lower():
            key = "Invalid Shift Value"
        elif "missing mandatory" in e.lower():
            key = "Missing Mandatory Field"
        elif "quantity" in e.lower():
            key = "Quantity Issue"
        elif "duplicate" in e.lower():
            key = "Duplicate Work Order"
        elif "machine" in e.lower():
            key = "Machine Number Format"
        elif "work order" in e.lower():
            key = "Work Order Format"
        else:
            key = "Other"
        error_counts[key] = error_counts.get(key, 0) + 1

if error_counts:
    df_err = pd.DataFrame({"Issue Type": list(error_counts.keys()), "Count": list(error_counts.values())})
    df_err = df_err.sort_values("Count", ascending=False)
    c1, c2 = st.columns([1,2])
    with c1:
        st.dataframe(df_err, use_container_width=True, hide_index=True)
    with c2:
        st.bar_chart(df_err.set_index("Issue Type"), height=220)
else:
    st.success("✅ No validation issues across all records!")

st.divider()

# ── Quantity trend ────────────────────────────────────────────────
st.subheader("📈 Quantity Produced — All Records")
qty_rows = [{"Record": f"#{r['id']}", "Qty": r.get("quantity_produced") or 0,
             "Machine": r.get("machine_number") or "?",
             "Shift": r.get("shift") or "?"}
            for r in records if r.get("quantity_produced")]
if qty_rows:
    df_qty = pd.DataFrame(qty_rows)
    st.bar_chart(df_qty.set_index("Record")["Qty"], height=220)

    # Summary stats
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Qty Produced", f"{df_qty['Qty'].sum():.0f}")
    s2.metric("Avg Qty per Record", f"{df_qty['Qty'].mean():.1f}")
    s3.metric("Max Qty", f"{df_qty['Qty'].max():.0f}")
    s4.metric("Min Qty", f"{df_qty['Qty'].min():.0f}")
    