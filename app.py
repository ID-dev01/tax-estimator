import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 MASTER DATA (OBBBA LEGISLATION & STATE REFORM) ---
LAW_2026 = {
    "Fed": {
        "MFJ": {
            "std": 32200, 
            "salt_cap_base": 40400, 
            "salt_phase": 505000, 
            "ctc": 2200, 
            "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)],
            "universal_charity": 2000 
        }
    },
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (1000000, 0.0897), (float('inf'), 0.1075)],
        "prop_cap": 15000, 
        "exemption": 1000
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

# --- 1. INPUT SECTION ---
col_u, col_s = st.columns(2)
with col_u:
    st.header("👤 Your Income (NJ)")
    y_w1 = st.number_input("Wages (W-2 Box 1)", value=145000.0)
    y_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=19000.0)
    y_s17 = st.number_input("NJ Withheld (W-2 Box 17)", value=7000.0)
    y_b12 = st.number_input("401k (Box 12, Code D)", value=10000.0)

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_w1 = st.number_input("Wages (W-2 Box 1)", value=135000.0)
    s_f2 = st.number_input("Fed Withheld (W-2 Box 2)", value=17000.0)
    s_ny_wh = st.number_input("NY Withheld (W-2 Box 17)", value=11000.0)
    s_b12 = st.number_input("401k (Box 12, Code D)", value=10000.0)

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

# --- 2. THE CALCULATION ENGINE ---
# Adjusted Gross Income (AGI)
fed_net_cap = max(-3000, cap_gains - cap_loss)
total_gross = y_w1 + s_w1 + int_div + fed_net_cap
agi = total_gross # Simplified for standard MFJ

# A. NY Liability (Non-Resident Calculation)
ny_taxable = max(0, (s_w1 - s_b12) - LAW_2026["NY"]["std"])
ny_liab = calc_tax(ny_taxable, LAW_2026["NY"]["brackets"])
ny_bal = s_ny_wh - ny_liab

# B. Federal Calculation (OBBBA Rules)
salt_cap = max(10000, 40400 - (max(0, agi - 505000) * 0.30))
allowed_salt = min(prop_tax + y_s17 + s_ny_wh, salt_cap)
fed_med = max(0, med_exp - (agi * 0.075))
fed_charity = max(0, charity - (agi * 0.005)) # 0.5% AGI Floor
fed_itemized = mrtg_int + allowed_salt + fed_med + fed_charity

is_itemizing = fed_itemized > (LAW_2026["Fed"]["MFJ"]["std"] + LAW_2026["Fed"]["MFJ"]["universal_charity"])
fed_deduction = fed_itemized if is_itemizing else (LAW_2026["Fed"]["MFJ"]["std"] + LAW_2026["Fed"]["MFJ"]["universal_charity"])

fed_taxable = max(0, agi - fed_deduction)
fed_tax_pre_credit = calc_tax(fed_taxable, LAW_2026["Fed"]["MFJ"]["brackets"])
fed_liab = max(0, fed_tax_pre_credit - (kids * 2200))
fed_bal = (y_f2 + s_f2) - fed_liab

# C. NJ Calculation (Resident)
nj_med = max(0, med_exp - (agi * 0.02))
nj_529_ded = nj_529 if agi <= 200000 else 0
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000 - nj_med - nj_529_ded)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
nj_credit = min(ny_liab, nj_tax_pre_credit * ((s_w1 - s_b12) / max(1, agi)))
nj_liab_final = nj_tax_pre_credit - nj_credit
nj_bal = y_s17 - nj_liab_final

# --- 3. FINAL SUMMARY & AUDIT TABLE ---
st.divider()
st.header("🏁 Final Settlement Summary")
m1, m2, m3 = st.columns(3)
m1.metric("Federal (IRS)", f"${fed_bal:,.2f}", delta="Refund" if fed_bal >=0 else "Owe")
m2.metric("New Jersey (NJ)", f"${nj_bal:,.2f}", delta="Refund" if nj_bal >=0 else "Owe")
m3.metric("New York (NY)", f"${ny_bal:,.2f}", delta="Refund" if ny_bal >=0 else "Owe")

# --- 4. DETAILED DATA AUDIT ---
st.subheader("📊 Internal Audit Data")
audit_data = {
    "Category": [
        "Total Household AGI", 
        "Federal Taxable Income", 
        "NY Taxable Income (Spouse Only)",
        "NJ Taxable Income",
        "Total Federal Tax Liability",
        "Total NJ Tax Liability (After NY Credit)",
        "Total NY Tax Liability",
        "Total Taxes Paid (Withholding)",
        "Effective Tax Rate (Fed)"
    ],
    "Amount": [
        f"${agi:,.2f}",
        f"${fed_taxable:,.2f}",
        f"${ny_taxable:,.2f}",
        f"${nj_taxable:,.2f}",
        f"${fed_liab:,.2f}",
        f"${nj_liab_final:,.2f}",
        f"${ny_liab:,.2f}",
        f"${(y_f2 + s_f2 + y_s17 + s_ny_wh):,.2f}",
        f"{(fed_liab / max(1, agi))*100:.2f}%"
    ]
}
st.table(pd.DataFrame(audit_data))

with st.expander("🔍 View Deduction Breakdown"):
    st.write(f"**Standard Deduction:** ${LAW_2026['Fed']['MFJ']['std']:,.0f}")
    st.write(f"**Your Total Itemized:** ${fed_itemized:,.2f}")
    st.write(f"---")
    st.write(f"Mortgage Interest: ${mrtg_int:,.0f}")
    st.write(f"Allowed SALT (Capped at ${salt_cap:,.0f}): ${allowed_salt:,.0f}")
    st.write(f"Charity (After 0.5% floor): ${fed_charity:,.2f}")
    st.write(f"Medical (After 7.5% floor): ${fed_med:,.2f}")
