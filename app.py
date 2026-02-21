import streamlit as st
import plotly.graph_objects as go
import pandas as pd
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

st.set_page_config(layout="wide", page_title="2026 Tax Auditor Pro")
st.title("⚖️ 2026 Master Tax Auditor")

# --- 1. INPUTS ---
col_u, col_s = st.columns(2)
with col_u:
    st.header("👤 Your Income (NJ)")
    y_w1 = st.number_input("Wages (W-2 Box 1)", value=145000.0)
    y_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=19000.0)
    y_s17 = st.number_input("NJ Withheld (W-2 Box 17)", value=7000.0)
    y_b12 = st.number_input("401k (Box 12)", value=10000.0)

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_w1 = st.number_input("Wages (W-2 Box 1)", value=135000.0)
    s_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=17000.0)
    s_ny_wh = st.number_input("NY Withheld (W-2 Box 17)", value=11000.0)
    s_b12 = st.number_input("401k (Box 12)", value=10000.0)

st.divider()
i1, i2, i3 = st.columns(3)
int_div = i1.number_input("Interest/Dividends", value=2500.0)
cap_gains = i2.number_input("Capital Gains", value=5000.0)
cap_loss = i3.number_input("Capital Losses", value=0.0)

st.header("🏠 Deductions")
d1, d2, d3 = st.columns(3)
mrtg_int = d1.number_input("Mortgage Interest", value=22000.0)
prop_tax = d1.number_input("Property Taxes", value=16000.0)
med_exp = d2.number_input("Medical Costs", value=2000.0)
charity = d2.number_input("Annual Charity", value=8000.0)
kids = d3.number_input("Kids < 17", value=2)
nj_529 = d3.number_input("NJ 529 Contribution", value=0.0)

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
fed_deduction = max(LAW_2026["Fed"]["MFJ"]["std"] + 2000, fed_itemized)
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
m1.metric("Federal", f"${(y_f2 + s_f2) - fed_liab:,.2f}")
m2.metric("New Jersey", f"${y_s17 - nj_liab_final:,.2f}")
m3.metric("New York", f"${s_ny_wh - ny_liab:,.2f}")

# --- 4. PDF GENERATOR ---
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="2026 Tax Audit Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    data = [
        ["Total Household AGI", f"${agi:,.2f}"],
        ["Federal Taxable Income", f"${fed_taxable:,.2f}"],
        ["Federal Tax Liability", f"${fed_liab:,.2f}"],
        ["NJ Tax Liability", f"${nj_liab_final:,.2f}"],
        ["NY Tax Liability", f"${ny_liab:,.2f}"],
        ["Total Taxes Paid (Withholding)", f"${(y_f2 + s_f2 + y_s17 + s_ny_wh):,.2f}"],
        ["Deduction Method", "Itemized" if fed_itemized > (LAW_2026["Fed"]["MFJ"]["std"]+2000) else "Standard"]
    ]
    
    pdf.set_font("Arial", 'B', 12)
    for row in data:
        pdf.cell(90, 10, row[0], border=1)
        pdf.cell(90, 10, row[1], border=1, ln=True)
    
    return pdf.output(dest='S')

with st.sidebar:
    st.header("📥 Export Center")
    if st.button("Generate PDF Report"):
        pdf_bytes = generate_pdf()
        st.download_button(label="Download PDF", data=pdf_bytes, file_name="Tax_Audit_2026.pdf", mime="application/pdf")
