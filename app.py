import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 MASTER DATA (OBBBA LEGISLATION & STATE REFORM) ---
LAW_2026 = {
    "Fed": {
        "MFJ": {
            "std": 32200, 
            "salt_cap": 40000, 
            "salt_phase": 500000, 
            "ctc": 2200, 
            "ctc_phase": 400000,
            "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)],
            "universal_charity": 2000 # OBBBA Benefit for non-itemizers
        }
    },
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (1000000, 0.0897), (float('inf'), 0.1075)],
        "prop_cap": 15000, 
        "exemption": 1000,
        "529_limit": 200000
    },
    "NY": {
        "brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06), (float('inf'), 0.0685)],
        "std": 16050
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

st.set_page_config(layout="wide", page_title="2026 Master Auditor")
st.title("⚖️ 2026 Full Master Tax Auditor")

# --- 1. INCOME & W-2 INPUTS ---
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

# --- 2. INVESTMENTS & 1099s ---
st.divider()
st.header("📈 Brokerage & 1099s")
i1, i2, i3 = st.columns(3)
int_div = i1.number_input("Interest & Dividends (1099-INT/DIV)", value=2500.0)
cap_gains = i2.number_input("Net Capital Gains", value=5000.0)
cap_loss = i3.number_input("Net Capital Losses", value=0.0)

# --- 3. DEDUCTIONS, 1098 & STRATEGY ---
st.divider()
st.header("🏠 Household Deductions & Strategy")
d1, d2, d3 = st.columns(3)
mrtg_int = d1.number_input("Mortgage Interest (1098 Box 1)", value=22000.0)
prop_tax = d1.number_input("Property Taxes Paid", value=16000.0)
med_exp = d2.number_input("Medical Costs (Out-of-Pocket)", value=2000.0)
charity = d2.number_input("Annual Charity (Cash/DAF)", value=8000.0)
bunching = d2.checkbox("Apply 2-Year Charity Bunching Strategy", value=False)
kids = d3.number_input("Qualifying Children < 17", value=2)
nj_529 = d3.number_input("NJ 529 Contribution (max $10k)", value=0.0)

# --- 4. ENGINE: CALCULATION ---
# Net Capital Loss Logic
fed_net_cap = max(-3000, cap_gains - cap_loss)
agi = (y_w1 + s_w1 + int_div + fed_net_cap)

# A. NY Liability Calculation (Non-Resident)
ny_taxable = max(0, (s_w1 - s_b12) - LAW_2026["NY"]["std"])
ny_calc_liab = calc_tax(ny_taxable, LAW_2026["NY"]["brackets"])
ny_refund = s_ny_wh - ny_calc_liab

# B. Federal Logic (with 2026 Floors)
actual_charity = charity * 2 if bunching else charity
salt_cap = max(10000, 40000 - (max(0, agi - 500000) * 0.30))
allowed_salt = min(prop_tax + y_s17 + s_ny_wh, salt_cap)
fed_med = max(0, med_exp - (agi * 0.075))
fed_charity_deduct = max(0, actual_charity - (agi * 0.005))

fed_itemized = mrtg_int + allowed_salt + fed_med + fed_charity_deduct
# OBBBA Rule: If not itemizing, take the $2k universal charity deduction
fed_deduction_final = max(LAW_2026["Fed"]["MFJ"]["std"] + LAW_2026["Fed"]["MFJ"]["universal_charity"], fed_itemized)

fed_liab = max(0, calc_tax(agi - fed_deduction_final, LAW_2026["Fed"]["MFJ"]["brackets"]) - (kids * 2200))
fed_bal = (y_f2 + s_f2) - fed_liab

# C. NJ Logic (with ANCHOR and 529)
nj_med = max(0, med_exp - (agi * 0.02))
nj_529_deduct = nj_529 if agi <= 200000 else 0
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000 - nj_med - nj_529_deduct)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
# Resident Credit for NY Taxes
nj_credit = min(ny_calc_liab, nj_tax_pre_credit * ((s_w1 - s_b12) / max(1, agi)))
nj_bal = y_s17 - (nj_tax_pre_credit - nj_credit)

# ANCHOR Rebate
anchor = 0
if agi <= 150000: anchor = 1500
elif agi <= 250000: anchor = 1000

# --- 5. FINAL RESULTS ---
st.divider()
st.header("🏁 Final Settlement Summary")
m1, m2, m3, m4 = st.columns(4)
def style_m(v): return f"Refund: ${v:,.2f}" if v >= 0 else f"OWE: ${abs(v):,.2f}"

m1.metric("Federal (IRS)", style_m(fed_bal), delta=fed_bal)
m2.metric("New Jersey (NJ)", style_m(nj_bal), delta=nj_bal)
m3.metric("New York (NY)", style_m(ny_refund), delta=ny_refund)
m4.metric("ANCHOR Rebate", f"${anchor:,.0f}", help="Direct check from NJ Treasury")

# Visual Breakdown
g1, g2 = st.columns(2)
with g1:
    fig_pie = go.Figure(data=[go.Pie(labels=['Take Home', 'Fed Tax', 'State Taxes', 'Savings/Deductions'], 
                                    values=[agi-fed_liab-nj_tax_pre_credit, fed_liab, nj_tax_pre_credit, fed_deduction_final+y_b12+s_b12], hole=.4)])
    fig_pie.update_layout(title="Where Your Money Goes")
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    ded_data = pd.DataFrame({
        "Type": ["SALT (Cap)", "Mortgage", "Med (Excess)", "Charity (Excess)"],
        "Amount": [allowed_salt, mrtg_int, fed_med, fed_charity_deduct]
    })
    st.bar_chart(ded_data, x="Type", y="Amount")
    st.write(f"Itemized Total: **${fed_itemized:,.0f}** vs. Standard Deduction: **${LAW_2026['Fed']['MFJ']['std']:,.0f}**")

if nj_529 > 0 and agi > 200000:
    st.error(f"❌ NJ 529 Deduction Disallowed: Your AGI (${agi:,.0f}) is over the $200k limit.")
