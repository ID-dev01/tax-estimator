import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 2025 TAX RULES ---
RULES = {
    "Fed": {"std": 31500, "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24), (501050, 0.32)]},
    "NJ": {"std": 2000, "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)]},
    "NY": {"std": 16050, "brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06)]}
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0: tax += amt * rate; prev = limit
        else: break
    return tax

st.set_page_config(page_title="2025 Tax Auditor", layout="wide")

# --- UI STYLING ---
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .header { background-color: #002d72; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .stNumberInput div div input { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header'><h1>📊 2025-2026 Comprehensive Tax Auditor</h1></div>", unsafe_allow_html=True)

# --- INPUT SECTION ---
with st.sidebar:
    st.header("1. Filing Metadata")
    status = st.selectbox("Status", ["Married Filing Jointly", "Single"])
    has_1095c = st.checkbox("1095-C Health Coverage?", value=True)
    st.divider()
    
    st.header("2. Investment Income")
    int_1099 = st.number_input("1099-INT (Interest)", 0.0)
    div_1099 = st.number_input("1099-DIV (Dividends)", 0.0)
    brokerage = st.number_input("Net Brokerage Gain/Loss", value=0.0)

col_in, col_res = st.columns([1.5, 1], gap="large")

with col_in:
    st.subheader("W-2 Data (Match your W-2 Boxes)")
    # Taxpayer
    c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1, 1, 1])
    tp_b1 = c1.number_input("T: Box 1 (Fed)", 0.0)
    tp_b16 = c2.number_input("T: Box 16 (NJ)", 0.0)
    tp_fwh = c3.number_input("T: Box 2 (Wh)", 0.0)
    tp_loc = c4.selectbox("Work State", ["NJ", "NY"], key="tl")
    tp_swh = c5.number_input("T: Box 17 (Wh)", 0.0)

    # Spouse
    if status == "Married Filing Jointly":
        s1, s2, s3, s4, s5 = st.columns([1.5, 1.5, 1, 1, 1])
        sp_b1 = s1.number_input("S: Box 1 (Fed)", 0.0)
        sp_b16 = s2.number_input("S: Box 16 (NJ)", 0.0)
        sp_fwh = s3.number_input("S: Box 2 (Wh)", 0.0)
        sp_loc = s4.selectbox("Work State", ["NJ", "NY"], key="sl")
        sp_swh = s5.number_input("S: Box 17 (Wh)", 0.0)
    else: sp_b1 = sp_b16 = sp_fwh = sp_swh = 0.0; sp_loc = "NJ"

# --- CALCULATION ENGINE ---
# Federal logic (Brokerage loss capped at -3k)
fed_invest = max(brokerage, -3000.0) if brokerage < 0 else brokerage
fed_taxable = max(0, (tp_b1 + sp_b1 + int_1099 + div_1099 + fed_invest) - 31500)
fed_tax = calc_tax(fed_taxable, RULES["Fed"]["brackets"])
fed_refund = (tp_fwh + sp_fwh) - fed_tax

# NY State logic (Liability for Schedule G)
ny_inc = (tp_b1 if tp_loc == "NY" else 0) + (sp_b1 if sp_loc == "NY" else 0)
ny_taxable = max(0, ny_inc - 16050)
ny_tax = calc_tax(ny_taxable, RULES["NY"]["brackets"])

# NJ State logic (No brokerage loss offset for W-2)
nj_gross = tp_b16 + sp_b16 + int_1099 + div_1099 + max(0, brokerage)
nj_tax_raw = calc_tax(max(0, nj_gross - 2000), RULES["NJ"]["brackets"])
# Schedule G Credit Calculation
nj_credit_cap = nj_tax_raw * (ny_inc / max(1, nj_gross))
actual_credit = min(ny_tax, nj_credit_cap)
nj_tax_final = max(0, nj_tax_raw - actual_credit)
nj_refund = (tp_swh + sp_swh) - nj_tax_final

# --- RESULTS VIZ ---
with col_res:
    st.subheader("Audit Results")
    st.metric("Total Est. Refund", f"${(fed_refund + nj_refund):,.2f}")
    
    # Audit Table for CSV
    audit_data = {
        "Category": ["Fed Taxable", "NJ Gross", "NY Income", "NJ Credit (Sched G)", "Fed Refund", "State Refund"],
        "Value": [fed_taxable, nj_gross, ny_inc, actual_credit, fed_refund, nj_refund]
    }
    df_audit = pd.DataFrame(audit_data)
    st.table(df_audit)

    # Charts
    fig = px.pie(names=["Tax Owed", "Take Home"], 
                 values=[fed_tax + nj_tax_final, (tp_b1+sp_b1) - (fed_tax + nj_tax_final)],
                 title="Income Allocation", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # --- SAVE TO CSV BUTTON ---
    csv = df_audit.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Audit Data for CPA",
        data=csv,
        file_name=f"tax_audit_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
