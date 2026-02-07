import streamlit as st
import plotly.express as px
import pandas as pd

# --- 2026 CONFIGURATION ---
st.set_page_config(page_title="Universal 2026 Tax Optimizer", layout="wide")

FED_DATA = {
    "Single": {
        "std_deduct": 16100, "sr_boost": 2050, "obbb_sr": 6000,
        "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)],
        "salt_base_cap": 20200, "salt_phaseout": 252500, "hsa_max": 4400
    },
    "Married Filing Jointly": {
        "std_deduct": 32200, "sr_boost": 1650, "obbb_sr": 6000,
        "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)],
        "salt_base_cap": 40400, "salt_phaseout": 505000, "hsa_max": 8750
    }
}

NJ_BRACKETS_MFJ = [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)]

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0:
            tax += amt * rate
            prev = limit
        else: break
    return tax

# --- SIDEBAR: USER PROFILE ---
with st.sidebar:
    st.header("👤 User Profile")
    status = st.selectbox("Filing Status", ["Married Filing Jointly", "Single"])
    
    # Generic age triggers
    u_age = st.number_input("Your Age", 18, 100, 35)
    s_age = 0
    if status == "Married Filing Jointly":
        s_age = st.number_input("Spouse Age", 18, 100, 35)
    
    is_homeowner = st.toggle("Homeowner in NJ?", value=True)
    mode = st.radio("Optimization Mode", ["Manual (Binary)", "Auto-Optimize (Max)"])

t1, t2, t3 = st.tabs(["💰 Income", "📑 Deductions & Credits", "📊 Results"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        tp_w2 = st.number_input("Taxpayer W-2 Wages", 0.0)
        tp_fwh = st.number_input("Fed Withheld", 0.0)
        tp_swh = st.number_input("NJ State Withheld", 0.0)
    with c2:
        if status == "Married Filing Jointly":
            sp_w2 = st.number_input("Spouse W-2 Wages", 0.0)
            sp_fwh = st.number_input("Fed Withheld", 0.0)
            sp_swh = st.number_input("NJ State Withheld", 0.0)
        else: sp_w2 = sp_fwh = sp_swh = 0.0
    
    inv_inc = st.number_input("Investment/Other Income", 0.0)
    total_gross = tp_w2 + sp_w2 + inv_inc

# --- CALCULATION LOGIC ---

# 1. Federal Senior Deductions (Triggered by Age)
extra_sr_deduct = 0.0
# Standard Sr Add-on
if u_age >= 65: extra_sr_deduct += FED_DATA[status]["sr_boost"]
if s_age >= 65: extra_sr_deduct += FED_DATA[status]["sr_boost"]
# OBBBA Sr Boost ($6k each, phases out at $150k MFJ)
if total_gross < 150000:
    if u_age >= 65: extra_sr_deduct += 6000
    if s_age >= 65: extra_sr_deduct += 6000

# 2. HSA Logic
if mode == "Auto-Optimize (Max)":
    hsa = FED_DATA[status]["hsa_max"]
else:
    hsa = FED_DATA[status]["hsa_max"] if st.checkbox("Take Max HSA") else 0.0

# 3. Federal Tax Result
fed_agi = max(0.0, total_gross - hsa - extra_sr_deduct)
fed_tax = calc_tax(fed_agi - FED_DATA[status]["std_deduct"], FED_DATA[status]["brackets"])
fed_res = (tp_fwh + sp_fwh) - fed_tax

# 4. NJ Benefit Logic (ANCHOR vs STAY NJ)
prop_tax = st.number_input("Annual Property Taxes", 0.0) if is_homeowner else 0.0
nj_taxable = max(0.0, total_gross - min(prop_tax, 15000.0))
nj_tax = calc_tax(nj_taxable, NJ_BRACKETS_MFJ)

anchor = 0.0
stay_nj = 0.0

if is_homeowner:
    # ANCHOR (Age 65+ gets +$250)
    sr_bonus = 250.0 if (u_age >= 65 or s_age >= 65) else 0.0
    if total_gross <= 150000: anchor = 1500.0 + sr_bonus
    elif total_gross <= 250000: anchor = 1000.0 + sr_bonus
    
    # STAY NJ (Only triggers if Age 65+ and income < $500k)
    if (u_age >= 65 or s_age >= 65) and total_gross < 500000:
        stay_nj = min(6500.0, prop_tax * 0.50)

# The "Greater Of" Logic
final_nj_benefit = max(anchor, stay_nj)
benefit_name = "Stay NJ" if stay_nj > anchor else "ANCHOR"

with t3:
    st.header("📊 Total 2026 Strategy")
    m1, m2, m3 = st.columns(3)
    m1.metric("Federal Refund", f"${fed_res:,.0f}")
    m2.metric("NJ State Refund", f"${(tp_swh + sp_swh - nj_tax):,.0f}")
    m3.metric(f"NJ {benefit_name} Rebate", f"${final_nj_benefit:,.0f}")

    if extra_sr_deduct > 0:
        st.success(f"👴 Senior Benefits Active: ${extra_sr_deduct:,.0f} extra federal deduction applied.")
