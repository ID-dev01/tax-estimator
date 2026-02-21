import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 MASTER DATA ---
LAW_2026 = {
    "Fed": {"MFJ": {"std": 32200, "salt_cap": 40000, "salt_phase": 500000, "ctc": 2200}},
    "NY": {"brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06), (float('inf'), 0.0685)], "std": 16050},
    "NJ": {"brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (float('inf'), 0.1075)]}
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
        else: break
    return tax

st.set_page_config(layout="wide", page_title="2026 Master Auditor")
st.title("⚖️ 2026 Master Tax Auditor")

# --- 1. INCOME & INVESTMENTS (ALL LOGIC RESTORED) ---
col_u, col_s = st.columns(2)
with col_u:
    st.header("👤 Your Income (NJ)")
    y_w1 = st.number_input("Wages (W-2 Box 1)", value=145000.0, key="y_w1")
    y_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=19000.0, key="y_f2")
    y_s17 = st.number_input("NJ Withheld (W-2 Box 17)", value=7000.0, key="y_s17")
    y_b12 = st.number_input("401k (W-2 Box 12, Code D)", value=10000.0, key="y_b12")

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_w1 = st.number_input("Wages (W-2 Box 1)", value=135000.0, key="s_w1")
    s_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=17000.0, key="s_f2")
    s_ny_wh = st.number_input("NY Withheld (W-2 Box 17)", value=11000.0, key="s_ny_wh")
    s_b12 = st.number_input("401k (W-2 Box 12, Code D)", value=10000.0, key="s_b12")

st.divider()
i1, i2, i3 = st.columns(3)
int_div = i1.number_input("1099-INT/DIV (Interest/Dividends)", value=2500.0)
cap_gains = i2.number_input("Brokerage Capital Gains", value=5000.0)
cap_loss = i3.number_input("Brokerage Capital Losses", value=0.0)

# --- 2. DEDUCTIONS & 1098 ---
st.header("🏠 Deductions & 1098")
d1, d2, d3 = st.columns(3)
mrtg_int = d1.number_input("Mortgage Int (1098 Box 1)", value=22000.0)
prop_tax = d1.number_input("Property Taxes", value=16000.0)
med_exp = d2.number_input("Medical Costs", value=2000.0)
charity = d2.number_input("Annual Charity", value=8000.0)
kids = d3.number_input("Kids < 17", value=2)
nj_529 = d3.number_input("NJ 529 Contrib (limit $200k AGI)", value=0.0)

# --- 3. THE ENGINE ---
fed_net_cap = max(-3000, cap_gains - cap_loss)
agi = (y_w1 + s_w1 + int_div + fed_net_cap)

# A. NY Liability Calculation (Non-Resident Estimate)
ny_taxable = max(0, (s_w1 - s_b12) - LAW_2026["NY"]["std"])
ny_calc_liab = calc_tax(ny_taxable, LAW_2026["NY"]["brackets"])
ny_bal = s_ny_wh - ny_calc_liab

# B. Federal Calculation
salt_cap = max(10000, 40000 - (max(0, agi - 500000) * 0.30))
allowed_salt = min(prop_tax + y_s17 + s_ny_wh, salt_cap)
fed_med = max(0, med_exp - (agi * 0.075))
fed_charity = max(0, charity - (agi * 0.005))
fed_deduction = max(LAW_2026["Fed"]["MFJ"]["std"], mrtg_int + allowed_salt + fed_med + fed_charity)
fed_liab = max(0, calc_tax(agi - fed_deduction, LAW_2026["Fed"]["MFJ"]["brackets"]) - (kids * 2200))
fed_bal = (y_f2 + s_f2) - fed_liab

# C. NJ Calculation (With Resident Credit)
nj_med = max(0, med_exp - (agi * 0.02))
nj_529_ded = nj_529 if agi <= 200000 else 0
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000 - nj_med - nj_529_ded)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
# NJ Credit for taxes paid to NY
nj_credit = min(ny_calc_liab, nj_tax_pre_credit * ((s_w1 - s_b12) / max(1, agi)))
nj_bal = y_s17 - (nj_tax_pre_credit - nj_credit)

# --- 4. RESULTS ---
st.divider()
st.header("🏁 Final Settlement Summary")
m1, m2, m3 = st.columns(3)
m1.metric("Federal (IRS)", f"${fed_bal:,.2f}")
m2.metric("New Jersey (NJ)", f"${nj_bal:,.2f}")
m3.metric("New York (NY)", f"${ny_bal:,.2f}")

st.info(f"💡 NY Logic: Estimated NY Tax Liability is **${ny_calc_liab:,.0f}**. Since you withheld **${s_ny_wh:,.0f}**, your NY refund is **${ny_bal:,.0f}**.")
