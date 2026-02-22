import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime

# --- 2026 MASTER DATA ---
LAW_2026 = {
    "Fed": {"MFJ": {"std": 32200, "salt_cap_base": 40400, "salt_phase": 505000, "ctc": 2200, 
            "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)],
            "universal_charity": 2000}},
    "NJ": {"brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (1000000, 0.0897), (float('inf'), 0.1075)],
           "prop_cap": 15000, "exemption": 1000},
    "NY": {"brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06), (float('inf'), 0.0685)], "std": 16050}
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

# --- SIDEBAR: PAYCHECK CALCULATOR ---
with st.sidebar:
    st.header("⚙️ Paycheck Adjustment")
    pay_periods_left = st.number_input("Pay periods remaining in 2026", value=20, min_value=1)
    st.divider()
    st.header("📥 Export Center")

st.title("⚖️ 2026 Full Master Tax Auditor")

# --- 1. INCOME INPUTS ---
col_u, col_s = st.columns(2)
with col_u:
    st.header("👤 Your Income (NJ)")
    y_w1 = st.number_input("Wages (W-2 Box 1)", value=145000.0, key="y_w1_k")
    y_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=19000.0, key="y_f2_k")
    y_s17 = st.number_input("NJ Withheld (W-2 Box 17)", value=7000.0, key="y_s17_k")
    y_b12 = st.number_input("401k (Box 12, Code D)", value=10000.0, key="y_401k_k")

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_w1 = st.number_input("Wages (W-2 Box 1)", value=135000.0, key="s_w1_k")
    s_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=17000.0, key="s_f2_k")
    s_ny_wh = st.number_input("NY Withheld (W-2 Box 17)", value=11000.0, key="s_ny_k")
    s_b12 = st.number_input("401k (Box 12, Code D)", value=10000.0, key="s_401k_k")

st.divider()
st.header("📈 Investments & Deductions")
i1, i2, i3 = st.columns(3)
int_div = i1.number_input("Interest/Dividends", value=2500.0, key="int_k")
cap_gains = i2.number_input("Capital Gains", value=5000.0, key="gain_k")
cap_loss = i3.number_input("Capital Losses", value=0.0, key="loss_k")

d1, d2, d3 = st.columns(3)
mrtg_int = d1.number_input("Mortgage Interest (1098)", value=22000.0, key="mrtg_k")
prop_tax = d1.number_input("Property Taxes", value=16000.0, key="prop_k")
med_exp = d2.number_input("Medical Costs", value=2000.0, key="med_k")
charity = d2.number_input("Annual Charity", value=8000.0, key="charity_k")
kids = d3.number_input("Kids < 17", value=2, key="kids_k")
nj_529 = d3.number_input("NJ 529 Contribution", value=0.0, key="529_k")

# --- 2. ENGINE ---
fed_net_cap = max(-3000, cap_gains - cap_loss)
agi = y_w1 + s_w1 + int_div + fed_net_cap

# NY Calculation
ny_taxable = max(0, (s_w1 - s_b12) - LAW_2026["NY"]["std"])
ny_liab = calc_tax(ny_taxable, LAW_2026["NY"]["brackets"])

# Federal Calculation
salt_cap = max(10000, 40400 - (max(0, agi - 505000) * 0.30))
allowed_salt = min(prop_tax + y_s17 + s_ny_wh, salt_cap)
fed_med = max(0, med_exp - (agi * 0.075))
fed_charity = max(0, charity - (agi * 0.005))
fed_itemized = mrtg_int + allowed_salt + fed_med + fed_charity
std_ded_total = LAW_2026["Fed"]["MFJ"]["std"] + 2000
fed_deduction = max(std_ded_total, fed_itemized)
fed_taxable = max(0, agi - fed_deduction)
fed_liab = max(0, calc_tax(fed_taxable, LAW_2026["Fed"]["MFJ"]["brackets"]) - (kids * 2200))

# NJ Calculation
nj_med = max(0, med_exp - (agi * 0.02))
nj_529_ded = nj_529 if agi <= 200000 else 0
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000 - nj_med - nj_529_ded)
nj_tax_pre = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
nj_credit = min(ny_liab, nj_tax_pre * ((s_w1 - s_b12) / max(1, agi)))
nj_liab_final = nj_tax_pre - nj_credit

# Final Settlement Totals
fed_paid, nj_paid, ny_paid = (y_f2 + s_f2), y_s17, s_ny_wh
fed_bal, nj_bal, ny_bal = fed_paid - fed_liab, nj_paid - nj_liab_final, ny_paid - ny_liab

# --- 3. UI RESULTS ---
st.divider()
st.header("🏁 Final Settlement Summary")
m1, m2, m3 = st.columns(3)
m1.metric("Federal Refund/Owe", f"${fed_bal:,.2f}", delta="Refund" if fed_bal >= 0 else "Owe")
m2.metric("NJ Refund/Owe", f"${nj_bal:,.2f}", delta="Refund" if nj_bal >= 0 else "Owe")
m3.metric("NY Refund/Owe", f"${ny_bal:,.2f}", delta="Refund" if ny_bal >= 0 else "Owe")

# --- 4. DATA AUDIT TABLE ---
st.subheader("📊 Detailed Audit Trail")
audit_comparison = pd.DataFrame({
    "Jurisdiction": ["Federal (IRS)", "New Jersey (NJ)", "New York (NY)"],
    "Taxable Income": [f"${fed_taxable:,.0f}", f"${nj_taxable:,.0f}", f"${ny_taxable:,.0f}"],
    "Total Liability": [f"${fed_liab:,.2f}", f"${nj_liab_final:,.2f}", f"${ny_liab:,.2f}"],
    "Amount Paid": [f"${fed_paid:,.2f}", f"${nj_paid:,.2f}", f"${ny_paid:,.2f}"],
    "Final Balance": [f"${fed_bal:,.2f}", f"${nj_bal:,.2f}", f"${ny_bal:,.2f}"]
})
st.table(audit_comparison)

# Paycheck Adjustment Info
if fed_bal < 0 or nj_bal < 0:
    st.warning("⚠️ **Underpayment Detected**")
    c1, c2 = st.columns(2)
    if fed_bal < 0:
        c1.write(f"Increase Federal withholding by **${abs(fed_bal)/pay_periods_left:,.2f}** per period.")
    if nj_bal < 0:
        c2.write(f"Increase NJ withholding by **${abs(nj_bal)/pay_periods_left:,.2f}** per period.")

# --- 5. VISUALIZATIONS ---
st.divider()
g1, g2 = st.columns(2)
with g1:
    labels = ['Take Home', 'Fed Tax', 'State Taxes', 'Savings']
    values = [agi - fed_liab - nj_liab_final - ny_liab, fed_liab, nj_liab_final + ny_liab, y_b12 + s_b12]
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
    fig_pie.update_layout(title_text="Income Allocation")
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = allowed_salt,
        title = {'text': f"SALT Cap Use (${salt_cap:,.0f})"},
        gauge = {'axis': {'range': [None, 50000]}, 'threshold': {'line': {'color': "red", 'width': 4}, 'value': salt_cap}}))
    st.plotly_chart(fig_gauge, use_container_width=True)

# --- 6. PDF EXPORT ---
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(w=190, h=10, text="2026 Master Tax Audit", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=10)
    pdf.ln(10)
    
    entities = [["Federal", fed_liab, fed_paid, fed_bal], ["NJ State", nj_liab_final, nj_paid, nj_bal], ["NY State", ny_liab, ny_paid, ny_bal]]
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(45, 10, "Entity", 1); pdf.cell(45, 10, "Liability", 1); pdf.cell(45, 10, "Paid", 1); pdf.cell(45, 10, "Balance", 1, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=10)
    for e in entities:
        pdf.cell(45, 10, e[0], 1); pdf.cell(45, 10, f"${e[1]:,.2f}", 1); pdf.cell(45, 10, f"${e[2]:,.2f}", 1); pdf.cell(45, 10, f"${e[3]:,.2f}", 1, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

if st.sidebar.button("Generate PDF Report"):
    st.sidebar.download_button("Download Now", data=generate_pdf(), file_name="Audit_2026.pdf")
