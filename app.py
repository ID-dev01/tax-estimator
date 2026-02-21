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
total_salt_paid = prop_tax + y_s17 + s_ny_wh
allowed_salt = min(total_salt_paid, salt_cap)
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

# --- 3. UI RESULTS ---
st.divider()
st.header("🏁 Final Settlement Summary")
m1, m2, m3 = st.columns(3)
fed_bal = (y_f2 + s_f2) - fed_liab
nj_bal = y_s17 - nj_liab_final
ny_bal = s_ny_wh - ny_liab

m1.metric("Federal Refund/Owe", f"${fed_bal:,.2f}")
m2.metric("NJ Refund/Owe", f"${nj_bal:,.2f}")
m3.metric("NY Refund/Owe", f"${ny_bal:,.2f}")

# --- 4. VISUALIZATIONS ---
st.divider()
g1, g2 = st.columns(2)

with g1:
    # Pie Chart
    labels = ['Take Home', 'Fed Tax', 'NJ/NY Tax', '401k Savings']
    values = [agi - fed_liab - nj_liab_final - ny_liab, fed_liab, nj_liab_final + ny_liab, y_b12 + s_b12]
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
    fig_pie.update_layout(title_text="Income Allocation")
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    # SALT Gauge
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = allowed_salt,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"SALT Cap: ${salt_cap:,.0f}"},
        gauge = {'axis': {'range': [None, 50000]},
                 'bar': {'color': "#3498DB"},
                 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': salt_cap}}))
    st.plotly_chart(fig_gauge, use_container_width=True)

# Deduction Bar Chart
st.subheader("Itemized Breakdown vs Standard Deduction")
ded_df = pd.DataFrame({
    "Category": ["Mortgage", "SALT", "Medical (Excess)", "Charity (Excess)"],
    "Amount": [mrtg_int, allowed_salt, fed_med, fed_charity]
})
st.bar_chart(ded_df, x="Category", y="Amount")
st.write(f"Your Itemized Total: **${fed_itemized:,.2f}** | Standard Deduction: **${std_ded_total:,.2f}**")

# --- 5. DATA AUDIT TABLE ---
st.table(pd.DataFrame({
    "Metric": ["Total AGI", "Fed Taxable", "NJ Taxable", "NY Taxable", "Fed Liab", "NJ Liab", "NY Liab"],
    "Value": [f"${agi:,.0f}", f"${fed_taxable:,.0f}", f"${nj_taxable:,.0f}", f"${ny_taxable:,.0f}", f"${fed_liab:,.0f}", f"${nj_liab_final:,.0f}", f"${ny_liab:,.0f}"]
}))

# --- 6. PDF EXPORT ---
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(w=190, h=10, text="2026 Master Tax Audit", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=12)
    pdf.ln(10)
    pdf.cell(w=190, h=10, text=f"Total AGI: ${agi:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=190, h=10, text=f"Federal Taxable: ${fed_taxable:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=190, h=10, text=f"Total Fed Liability: ${fed_liab:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w=190, h=10, text=f"Total NJ Liability: ${nj_liab_final:,.2f}", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

if st.sidebar.button("Generate PDF Report"):
    pdf_bytes = generate_pdf()
    st.sidebar.download_button("Download Audit PDF", data=pdf_bytes, file_name="Audit.pdf", mime="application/pdf")
