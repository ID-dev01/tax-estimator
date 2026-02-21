import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 MASTER DATA (OBBBA LEGISLATION) ---
LAW_2026 = {
    "Fed": {
        "MFJ": {
            "std": 32200, "salt_cap": 40000, "salt_phase": 500000, "ctc": 2200, "ctc_phase": 400000,
            "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]
        }
    },
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (1000000, 0.0897), (float('inf'), 0.1075)],
        "prop_cap": 15000, "exemption": 1000, "529_limit": 200000
    }
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

st.set_page_config(layout="wide", page_title="2026 Tax Auditor Pro")
st.title("🛡️ 2026 Master Tax Auditor & Strategic Planner")

# --- 1. SIDEBAR STRATEGY ---
with st.sidebar:
    st.header("📈 Strategy Controls")
    bunch_years = st.radio("Charity Bunching Cycle", [1, 2], index=0, help="2 = Pre-pay next year's charity to beat the 0.5% AGI floor.")
    add_401k = st.slider("Increase Pre-Tax Savings (Box 12)", 0, 30000, 0)
    pay_periods = st.number_input("Paychecks Remaining in 2026", 1, 26, 20)
    st.divider()
    st.subheader("🎓 Education & State")
    nj_529 = st.number_input("NJ 529 Contrib (max $10k)", 0, 10000, 0)

# --- 2. INCOME INPUTS (SPOUSE SPLIT) ---
col_u, col_s = st.columns(2)
with col_u:
    st.header("👤 Your Income (NJ)")
    y_w1 = st.number_input("Wages (W-2 Box 1)", value=145000.0, key="y_w1")
    y_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=19000.0, key="y_f2")
    y_s17 = st.number_input("NJ Withheld (W-2 Box 17)", value=7000.0, key="y_s17")
    y_b12 = st.number_input("401k Contrib (W-2 Box 12, Code D)", value=10000.0, key="y_b12")

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_w1 = st.number_input("Wages (W-2 Box 1)", value=135000.0, key="s_w1")
    s_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=17000.0, key="s_f2")
    s_ny_wh = st.number_input("NY Withheld (W-2 Box 17)", value=11000.0, key="s_ny_wh")
    s_ny_liab = st.number_input("Actual NY Tax (Estimate)", value=9500.0, key="s_ny_liab")
    s_b12 = st.number_input("401k Contrib (W-2 Box 12, Code D)", value=10000.0, key="s_b12")

# --- 3. DEDUCTIONS ---
st.divider()
st.header("🏠 Household Deductions")
d1, d2, d3 = st.columns(3)
prop_tax = d1.number_input("Property Taxes", value=16000.0)
mrtg_int = d1.number_input("Mortgage Interest", value=22000.0)
med_exp = d2.number_input("Medical Costs", value=2000.0)
charity = d2.number_input("Annual Charity", value=8000.0)
kids = d3.number_input("Kids < 17", value=2)

# --- 4. ENGINE: CALCULATION ---
agi = (y_w1 + s_w1) - add_401k
f_conf = LAW_2026["Fed"]["MFJ"]

# Federal Itemizing (with 2026 Floors)
salt_cap = max(10000, f_conf["salt_cap"] - (max(0, agi - f_conf["salt_phase"]) * 0.30))
allowed_salt = min(prop_tax + y_s17 + s_ny_wh, salt_cap)
fed_med = max(0, med_exp - (agi * 0.075))
fed_charity = max(0, (charity * bunch_years) - (agi * 0.005))

fed_itemized = mrtg_int + allowed_salt + fed_med + fed_charity
fed_deduction = max(f_conf["std"], fed_itemized)
fed_liab = max(0, calc_tax(agi - fed_deduction, f_conf["brackets"]) - (kids * f_conf["ctc"]))
fed_bal = (y_f2 + s_f2) - fed_liab

# NJ State (NJ-COJ & ANCHOR)
nj_med = max(0, med_exp - (agi * 0.02))
nj_529_deduct = nj_529 if agi <= 200000 else 0
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000 - nj_med - nj_529_deduct)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
nj_credit = min(s_ny_liab, nj_tax_pre_credit * ((s_w1 - s_b12) / max(1, agi)))
nj_bal = y_s17 - (nj_tax_pre_credit - nj_credit)

# ANCHOR Logic
anchor_amt = 0
if agi <= 150000: anchor_amt = 1500
elif agi <= 250000: anchor_amt = 1000

# --- 5. RESULTS & CHARTS ---
st.divider()
st.header("🏁 Final Settlement Summary")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Federal (IRS)", f"${fed_bal:,.2f}")
m2.metric("New Jersey", f"${nj_bal:,.2f}")
m3.metric("New York", f"${s_ny_wh - s_ny_liab:,.2f}")
m4.metric("ANCHOR Rebate", f"${anchor_amt:,.0f}", help="Paid separately via check")

g1, g2 = st.columns(2)
with g1:
    fig_pie = go.Figure(data=[go.Pie(labels=['Take Home', 'Fed Tax', 'State Taxes', 'Deductions/Savings'], 
                                    values=[agi-fed_liab-nj_tax_pre_credit, fed_liab, nj_tax_pre_credit, fed_deduction+y_b12+s_b12], hole=.4)])
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    fig_salt = go.Figure(go.Indicator(mode="gauge+number", value=allowed_salt, title={'text': f"SALT Cap: ${salt_cap:,.0f}"},
                                     gauge={'axis': {'range': [0, 40000]}, 'threshold': {'line': {'color': "red", 'width': 4}, 'value': salt_cap}}))
    st.plotly_chart(fig_salt, use_container_width=True)

# --- 6. ACTION PLAN ---
st.divider()
if (fed_bal + nj_bal) < -500:
    st.error(f"⚠️ Underpayment: Increase Federal withholding by ${abs(fed_bal/pay_periods):,.2f} and NJ by ${abs(nj_bal/pay_periods):,.2f} per check.")
if nj_529 > 0 and agi > 200000:
    st.warning(f"Note: Your NJ 529 deduction of ${nj_529:,.0f} was disallowed because income exceeds $200k.")
