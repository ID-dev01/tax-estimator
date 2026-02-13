import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 2025-2026 OFFICIAL TAX RULES ---
RULES = {
    "Fed": {
        "std": 31500, # 2025 MFJ Standard Deduction
        "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24), (501050, 0.32)],
        "salt_cap": 40000, # 2025 OBBBA Act updated cap
        "aotc_phaseout": (160000, 180000) # MFJ Phaseout start/end
    },
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)],
        "tuition_cap": 10000,
        "prop_tax_deduct_cap": 15000
    },
    "NY": {
        "std": 16050,
        "brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06)]
    }
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0: tax += amt * rate; prev = limit
        else: break
    return tax

st.set_page_config(page_title="2025 Comprehensive Tax Auditor", layout="wide")

# --- CUSTOM STYLING ---
st.markdown("""
<style>
    .main { background-color: #fcfcfc; }
    .header-blue { background-color: #002d72; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; text-align: center; }
    .section-head { background-color: #e9ecef; padding: 8px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; border-left: 5px solid #002d72; }
    .metric-box { border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: white; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header-blue'><h1>📊 2025-2026 Comprehensive Tax Auditor</h1></div>", unsafe_allow_html=True)

col_in, col_res = st.columns([1.6, 1], gap="large")

with col_in:
    # 1. PROFILE & W-2s
    st.markdown("<div class='section-head'>1. Filing Status & W-2 Wages</div>", unsafe_allow_html=True)
    c_status, c_coverage = st.columns(2)
    status = c_status.selectbox("Status", ["Married Filing Jointly", "Single"])
    has_1095c = c_coverage.toggle("1095-C Health Coverage?", value=True)

    # Taxpayer Row
    st.caption("Taxpayer W-2")
    t1, t2, t3, t4, t5 = st.columns([1.5, 1.5, 1, 1, 1])
    tp_b1 = t1.number_input("Box 1 (Fed)", 0.0, key="tp1")
    tp_b16 = t2.number_input("Box 16 (NJ)", 0.0, key="tp16")
    tp_fwh = t3.number_input("Box 2 (Wh)", 0.0, key="tp2")
    tp_loc = t4.selectbox("Work State", ["NJ", "NY"], key="tploc")
    tp_swh = t5.number_input("Box 17 (Wh)", 0.0, key="tp17")

    # Spouse Row
    if status == "Married Filing Jointly":
        st.caption("Spouse W-2")
        s1, s2, s3, s4, s5 = st.columns([1.5, 1.5, 1, 1, 1])
        sp_b1 = s1.number_input("Box 1 (Fed)", 0.0, key="sp1")
        sp_b16 = s2.number_input("Box 16 (NJ)", 0.0, key="sp16")
        sp_fwh = s3.number_input("Box 2 (Wh)", 0.0, key="sp2")
        sp_loc = s4.selectbox("Work State", ["NJ", "NY"], key="sploc")
        sp_swh = s5.number_input("Box 17 (Wh)", 0.0, key="sp17")
    else: sp_b1 = sp_b16 = sp_fwh = sp_swh = 0.0; sp_loc = "NJ"

    # 2. 1098 & INVESTMENTS
    st.markdown("<div class='section-head'>2. 1098s, 1099s & Investments</div>", unsafe_allow_html=True)
    i1, i2, i3 = st.columns(3)
    int_1099 = i1.number_input("1099-INT (Interest)", 0.0)
    div_1099 = i2.number_input("1099-DIV (Dividends)", 0.0)
    brokerage = i3.number_input("Net Brokerage Gain/Loss", 0.0, help="Fed offsets $3k; NJ offsets $0.")

    d1, d2, d3 = st.columns(3)
    mrtg_int = d1.number_input("1098: Mortgage Interest", 0.0)
    prop_tax = d2.number_input("1098: Property Tax", 0.0)
    student_int = d3.number_input("1098-E: Student Loan Int", 0.0)

    t1, t2 = st.columns(2)
    tuition = t1.number_input("1098-T: Tuition (NJ Inst?)", 0.0)
    hsa = t2.number_input("HSA Contributions", 0.0)

# --- MATH ENGINE ---
# FEDERAL
fed_invest = max(brokerage, -3000.0) if brokerage < 0 else brokerage
fed_agi = (tp_b1 + sp_b1 + int_1099 + div_1099 + fed_invest) - hsa - min(student_int, 2500)
# Itemized vs Standard
total_itemized = mrtg_int + min(RULES["Fed"]["salt_cap"], (tp_swh + sp_swh + prop_tax))
fed_deduction = max(RULES["Fed"]["std"], total_itemized)
fed_taxable = max(0, fed_agi - fed_deduction)
fed_tax_pre_credit = calc_tax(fed_taxable, RULES["Fed"]["brackets"])

# AOTC Credit Logic (American Opportunity)
aotc_max = 2500 if tuition >= 4000 else (tuition if tuition <= 2000 else 2000 + (tuition-2000)*0.25)
# Phaseout
low, high = RULES["Fed"]["aotc_phaseout"]
phase_mult = max(0, min(1, (high - fed_agi) / (high - low)))
actual_aotc = aotc_max * phase_mult
fed_tax_final = max(0, fed_tax_pre_credit - actual_aotc)
fed_refund = (tp_fwh + sp_fwh) - fed_tax_final

# STATE (NJ Resident)
nj_invest = max(0, brokerage) + int_1099 + div_1099
nj_gross = tp_b16 + sp_b16 + nj_invest
nj_taxable = max(0, nj_gross - min(prop_tax, 15000) - min(tuition, 10000) - 2000)
nj_tax_raw = calc_tax(nj_taxable, RULES["NJ"]["brackets"])

# Schedule G Credit (NY)
ny_inc = (tp_b1 if tp_loc == "NY" else 0) + (sp_b1 if sp_loc == "NY" else 0)
ny_tax = calc_tax(max(0, ny_inc - 16050), RULES["NY"]["brackets"])
nj_credit = min(ny_tax, nj_tax_raw * (ny_inc / max(1, nj_gross)))
nj_tax_final = max(0, nj_tax_raw - nj_credit)
nj_refund = (tp_swh + sp_swh) - nj_tax_final

# --- RESULTS VIZ ---
with col_res:
    st.markdown("<div class='section-head'>Audit Summary</div>", unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m1.markdown(f"<div class='metric-box'>Fed Refund<br><h2 style='color:green'>${fed_refund:,.2f}</h2></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-box'>NJ Refund<br><h2 style='color:green'>${nj_refund:,.2f}</h2></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # Audit Table
    audit_data = {
        "Audit Point": ["Fed Taxable Income", "Itemized Deduction", "Education Credit (AOTC)", "NJ Gross (Box 16+)", "NJ Credit for NY Tax"],
        "Value": [f"${fed_taxable:,.0f}", f"${fed_deduction:,.0f}", f"${actual_aotc:,.0f}", f"${nj_gross:,.0f}", f"${nj_credit:,.0f}"]
    }
    st.table(pd.DataFrame(audit_data))

    # Pie Chart
    pie_df = pd.DataFrame({"Source": ["Fed Tax", "NJ Tax", "Take-Home"], "Amt": [fed_tax_final, nj_tax_final, (tp_b1+sp_b1)-fed_tax_final-nj_tax_final]})
    st.plotly_chart(px.pie(pie_df, values="Amt", names="Source", hole=0.5, title="Budget Allocation"), use_container_width=True)

    # Download
    csv = pd.DataFrame(audit_data).to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Final Audit CSV", data=csv, file_name="2025_Tax_Audit.csv", mime="text/csv")
