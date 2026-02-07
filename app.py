import streamlit as st
import plotly.express as px
import pandas as pd

# --- 2026 CONFIGURATION ---
st.set_page_config(page_title="2026 Universal Tax Optimizer", layout="wide")

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
        st.markdown("### **Taxpayer**")
        tp_w2 = st.number_input("W-2 Fed Wages", 0.0, key="tp_w2_input")
        tp_fwh = st.number_input("Federal Withholding", 0.0, key="tp_fed_wh_input")
        tp_swh = st.number_input("NJ State Withholding", 0.0, key="tp_nj_wh_input")
    with c2:
        if status == "Married Filing Jointly":
            st.markdown("### **Spouse**")
            sp_w2 = st.number_input("W-2 Fed Wages", 0.0, key="sp_w2_input")
            sp_fwh = st.number_input("Federal Withholding", 0.0, key="sp_fed_wh_input")
            sp_swh = st.number_input("NJ State Withholding", 0.0, key="sp_nj_wh_input")
        else: 
            sp_w2 = sp_fwh = sp_swh = 0.0
    
    inv_inc = st.number_input("Investment/Other Income (Interest, Dividends, etc.)", 0.0, key="invest_input")
    total_gross = tp_w2 + sp_w2 + inv_inc

# --- CALCULATION ENGINE ---

# 1. Federal Senior Deductions
extra_sr_deduct = 0.0
if u_age >= 65: extra_sr_deduct += FED_DATA[status]["sr_boost"]
if s_age >= 65: extra_sr_deduct += FED_DATA[status]["sr_boost"]
# OBBBA Senior Relief ($6k)
if total_gross < 150000:
    if u_age >= 65: extra_sr_deduct += 6000
    if s_age >= 65: extra_sr_deduct += 6000

# 2. HSA Logic
if mode == "Auto-Optimize (Max)":
    hsa = FED_DATA[status]["hsa_max"]
else:
    hsa = FED_DATA[status]["hsa_max"] if st.checkbox("Apply Max HSA", key="hsa_chk") else 0.0

# 3. Federal Tax
fed_agi = max(0.0, total_gross - hsa - extra_sr_deduct)
fed_taxable = max(0.0, fed_agi - FED_DATA[status]["std_deduct"])
fed_tax = calc_tax(fed_taxable, FED_DATA[status]["brackets"])
fed_res = (tp_fwh + sp_fwh) - fed_tax

# 4. NJ State Logic (ANCHOR vs STAY NJ)
with t2:
    prop_tax = st.number_input("Total Annual Property Taxes Paid", 0.0, key="prop_tax_input") if is_homeowner else 0.0
    mort_int = st.number_input("Mortgage Interest Paid", 0.0, key="mort_int_input")

nj_taxable = max(0.0, total_gross - min(prop_tax, 15000.0))
nj_tax = calc_tax(nj_taxable, NJ_BRACKETS_MFJ)

anchor = 0.0
stay_nj = 0.0
benefit_name = "N/A"

if is_homeowner:
    # ANCHOR (Under 65: up to $1500, Over 65: +$250)
    sr_bonus = 250.0 if (u_age >= 65 or s_age >= 65) else 0.0
    if total_gross <= 150000: anchor = 1500.0 + sr_bonus
    elif total_gross <= 250000: anchor = 1000.0 + sr_bonus
    
    # STAY NJ (Over 65 only, up to $6,500)
    if (u_age >= 65 or s_age >= 65) and total_gross < 500000:
        stay_nj = min(6500.0, prop_tax * 0.50)

final_nj_benefit = max(anchor, stay_nj)
benefit_name = "Stay NJ" if stay_nj > anchor else "ANCHOR"

with t3:
    st.header("📊 Final 2026 Strategy Summary")
    r1, r2, r3 = st.columns(3)
    r1.metric("Federal Refund", f"${fed_res:,.0f}")
    r2.metric("NJ State Refund", f"${(tp_swh + sp_swh - nj_tax):,.0f}")
    
    if is_homeowner:
        r3.metric(f"NJ {benefit_name} Rebate", f"${final_nj_benefit:,.0f}")
    else:
        r3.metric("NJ Renter Credit", "$450") # NJ Renter Credit standard

    st.divider()
    total_impact = fed_res + (tp_swh + sp_swh - nj_tax) + (final_nj_benefit if is_homeowner else 450)
    st.write(f"### **Total Cash Impact: ${total_impact:,.0f}**")
    
    if u_age >= 65 or s_age >= 65:
        st.info(f"👴 Senior Mode Active: Using {benefit_name} for maximum benefit.")
