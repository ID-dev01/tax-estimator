import streamlit as st
import pandas as pd

# --- CONSTANTS: 2025-2026 TAX LAW ---
LAW = {
    "Fed": {"std": 31500.0, "ctc": 2200.0, "salt_cap": 10000.0},
    "NJ": {
        "exemption": 1000.0, "prop_deduct_max": 15000.0, 
        "ui_cap": 184.02, "di_cap": 380.42, "fli_cap": 545.82,
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)]
    },
    "NY": {"std": 16050.0, "brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06)]}
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0: tax += amt * rate; prev = limit
        else: break
    return tax

st.set_page_config(layout="wide", page_title="2025 Household Tax Auditor")
st.title("🛡️ 2025-2026 Comprehensive Household Auditor")

# --- SIDE-BY-SIDE INPUTS ---
col1, col2 = st.columns(2, gap="large")

with col1:
    st.header("👤 Your W-2 (NJ)")
    y_b1 = st.number_input("Box 1: Fed Wages", 0.0, format="%.2f")
    y_b16 = st.number_input("Box 16: NJ Wages", 0.0, format="%.2f")
    y_fwh = st.number_input("Box 2: Fed Withholding", 0.0, format="%.2f")
    y_swh = st.number_input("Box 17: NJ Withholding", 0.0, format="%.2f")
    st.caption("Box 14 (NJ Payroll Taxes)")
    y_ui = st.number_input("NJ UI/WF/SWF Paid", 0.0)
    y_di = st.number_input("NJ DI (Disability) Paid", 0.0)
    y_fli = st.number_input("NJ FLI (Family Leave) Paid", 0.0)

with col2:
    st.header("🗽 Spouse W-2 (NY)")
    s_b1 = st.number_input("Box 1: Fed Wages ", 0.0, format="%.2f")
    s_fwh = st.number_input("Box 2: Fed Withholding ", 0.0, format="%.2f")
    s_ny_wh = st.number_input("Box 17: NY Withholding", 0.0, format="%.2f")
    s_nj_wh = st.number_input("Box 17: NJ Withholding (if any)", 0.0, format="%.2f")
    st.caption("Box 14 (NY Payroll Taxes)")
    s_ny_pfl = st.number_input("NY PFL Paid", 0.0)
    s_ny_sdi = st.number_input("NY SDI Paid", 0.0)

st.divider()

# --- 1099, BROKERAGE, & HOME ---
st.header("📁 Non-Wage Income & Deductions")
c3, c4, c5 = st.columns(3)
with c3:
    int_div = st.number_input("1099-INT/DIV (Interest/Dividends)", 0.0)
    cap_gains = st.number_input("1099-B (Net Capital Gains)", 0.0)
with c4:
    mortgage = st.number_input("1098 Mortgage Interest", 0.0)
    prop_tax = st.number_input("Property Taxes Paid", 0.0)
with c5:
    num_kids = st.number_input("Children Under 17", 0, 10, 0)
    num_kids_u6 = st.number_input("Children Under 6", 0, num_kids, 0)

# --- CALCULATIONS ---
# 1. Federal Total
fed_gross = y_b1 + s_b1 + int_div + cap_gains
# SALT Deduction Calculation
total_salt = prop_tax + y_swh + s_ny_wh
fed_deduction = max(LAW["Fed"]["std"], mortgage + min(total_salt, LAW["Fed"]["salt_cap"]))
fed_taxable = max(0, fed_gross - fed_deduction)
fed_tax_pre_credit = calc_tax(fed_taxable, [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24)])
fed_ctc = num_kids * LAW["Fed"]["ctc"]
fed_refund = (y_fwh + s_fwh) - max(0, fed_tax_pre_credit - fed_ctc)

# 2. NJ State
nj_gross = y_b16 + s_b1 + int_div + cap_gains # Add back spouse wages for NJ residency
nj_deduct = 2000.0 + (num_kids * LAW["NJ"]["exemption"]) + min(prop_tax, LAW["NJ"]["prop_deduct_max"])
nj_taxable = max(0, nj_gross - nj_deduct)
nj_tax_raw = calc_tax(nj_taxable, LAW["NJ"]["brackets"])

# NY Credit Calculation
ny_liab = calc_tax(max(0, s_b1 - LAW["NY"]["std"]), LAW["NY"]["brackets"])
nj_credit = min(ny_liab, nj_tax_raw * (s_b1 / max(1, nj_gross)))

# NJ Excess Payroll Refund (Form NJ-2450)
nj_excess = max(0, y_ui - LAW["NJ"]["ui_cap"]) + max(0, y_di - LAW["NJ"]["di_cap"]) + max(0, y_fli - LAW["NJ"]["fli_cap"])

nj_final_tax = max(0, nj_tax_raw - nj_credit)
nj_refund = (y_swh + s_nj_wh) - nj_final_tax + nj_excess

# --- OUTPUT ---
st.divider()
res_f, res_s = st.columns(2)
with res_f:
    st.metric("Estimated Federal Refund", f"${fed_refund:,.2f}")
    if fed_deduction > LAW["Fed"]["std"]: st.caption("✅ Benefiting from Itemized Deductions (Mortgage/SALT)")
with res_s:
    st.metric("Estimated NJ Refund", f"${nj_refund:,.2f}")
    if nj_excess > 0: st.success(f"Includes ${nj_excess:,.2f} in Excess Payroll Refund")

with st.expander("🔍 View NJ Math Breakdown"):
    st.write(f"NJ Taxable Income: ${nj_taxable:,.2f}")
    st.write(f"NJ Tax Before Credits: ${nj_tax_raw:,.2f}")
    st.write(f"Credit for NY Tax Paid (Spouse): -${nj_credit:,.2f}")
    st.write(f"NJ Total Liability: ${nj_final_tax:,.2f}")
