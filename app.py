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
    prop_tax = d2.number
