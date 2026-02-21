import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 AUDITOR DATA ---
LAW_2026 = {
    "Fed": {
        "MFJ": {"std": 32200, "salt_cap": 40000, "salt_phase": 500000, "ctc": 2200, "ctc_phase": 400000,
                "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24), (501050, 0.32), (751600, 0.35), (float('inf'), 0.37)]},
        "Single": {"std": 16100, "salt_cap": 40000, "salt_phase": 500000, "ctc": 2200, "ctc_phase": 200000,
                   "brackets": [(11925, 0.10), (48475, 0.12), (103350, 0.22), (197300, 0.24), (250525, 0.32), (626350, 0.35), (float('inf'), 0.37)]}
    },
    "NJ": {
        "MFJ": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (1000000, 0.0897), (float('inf'), 0.1075)],
        "prop_cap": 15000, "exemption": 1000
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

st.set_page_config(layout="wide", page_title="2026 NJ/NY Tax Auditor")
st.title("📊 2026 Multi-State Tax Auditor & Savings Planner")

# --- SIDEBAR: PRE-TAX PLANNING ---
with st.sidebar:
    st.header("🚀 Pre-Tax Planning")
    st.info("Every $1,000 you move to 'Pre-Tax' reduces your Federal & State taxable income.")
    add_401k = st.slider("Additional 401(k) Contribution", 0, 24500, 5000)
    add_hsa = st.slider("Additional HSA (Family)", 0, 8750, 3000)
    total_pretax_shift = add_401k + add_hsa

# --- MAIN INPUTS ---
col_in, col_res = st.columns([1, 1.2], gap="large")

with col_in:
    st.header("1. Income & Filing")
    status = st.selectbox("Filing Status", ["MFJ", "Single"])
    f_conf = LAW_2026["Fed"][status]
    
    y_b1 = st.number_input("Your NJ Wages (W2 Box 1)", value=145000.0)
    s_b1 = st.number_input("Spouse NY Wages (W2 Box 1)", value=135000.0) if status == "MFJ" else 0.0
    y_fwh = st.number_input("Total Fed Withheld (Household)", value=38000.0)
    y_swh = st.number_input("NJ Withheld (Box 17)", value=6500.0)
    s_ny_liab = st.number_input("Actual NY Tax Liability (from NY IT-203)", value=9200.0) if status == "MFJ" else 0.0
    
    st.header("2. SALT & Property")
    prop_tax = st.number_input("Property Taxes", value=16500.0)
    mrtg_int = st.number_input("Mortgage Interest", value=22000.0)
    kids = st.number_input("Kids < 17", value=2)

# --- ENGINE ---
# Adjusted Gross Income (Applying your Pre-Tax Planning)
agi = (y_b1 + s_b1) - total_pretax_shift

# SALT 2026 Logic
salt_cap = max(10000, f_conf["salt_cap"] - (max(0, agi - f_conf["salt_phase"]) * 0.30))
actual_salt_deduction = min(prop_tax + y_swh + s_ny_liab, salt_cap)

# Federal Liability
fed_deduct = max(f_conf["std"], mrtg_int + actual_salt_deduction)
fed_taxable = max(0, agi - fed_deduct)
ctc = max(0, (kids * f_conf["ctc"]) - ((max(0, agi - f_conf["ctc_phase"]) // 1000) * 50))
fed_liab = max(0, calc_tax(fed_taxable, f_conf["brackets"]) - ctc)
fed_result = y_fwh - fed_liab

# NJ Resident Credit (Schedule NJ-COJ)
nj_gross = agi 
nj_taxable = max(0, nj_gross - min(prop_tax, 15000) - (kids * 1000) - 2000)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["MFJ"])

# NJ-COJ Formula: Lesser of NY Tax or (NJ Tax * (NY_Income / Total_Income))
income_ratio = s_b1 / max(1, nj_gross)
nj_credit_limit = nj_tax_pre_credit * income_ratio
nj_credit = min(s_ny_liab, nj_credit_limit)
nj_final_liab = nj_tax_pre_credit - nj_credit
nj_result = y_swh - nj_final_liab

# --- VISUALS ---
with col_res:
    st.header("Audit Summary")
    
    # 1. NJ-COJ Resident Credit Visualization
    st.subheader("🛡️ Double Taxation Shield (NJ-COJ)")
    fig_nj = go.Figure(data=[
        go.Bar(name='NJ Tax Owed (Pre-Credit)', x=['State Tax'], y=[nj_tax_pre_credit], marker_color='#E74C3C'),
        go.Bar(name='Credit for NY Tax Paid', x=['State Tax'], y=[nj_credit], marker_color='#2ECC71')
    ])
    fig_nj.update_layout(barmode='stack', height=300, title="How NJ cancels out your NY Tax")
    st.plotly_chart(fig_nj, use_container_width=True)

    # 2. Results Metrics
    r1, r2 = st.columns(2)
    r1.metric("Federal Refund", f"${fed_result:,.2f}", delta="Capped at $40k SALT" if salt_cap > 10000 else "SALT Phased Out")
    r2.metric("NJ State Refund", f"${nj_result:,.2f}", delta=f"Credit: ${nj_credit:,.0f}")

    # 3. Planning Impact Chart
    st.divider()
    st.subheader("💰 Savings Impact")
    current_liab_no_plan = calc_tax(agi + total_pretax_shift - fed_deduct, f_conf["brackets"])
    tax_savings = current_liab_no_plan - fed_liab
    
    st.success(f"Your pre-tax contributions are saving you **${tax_savings:,.2f}** in federal taxes this year.")
    
    fig_plan = go.Figure(go.Indicator(
        mode = "number+delta",
        value = fed_result,
        delta = {'reference': fed_result - tax_savings, 'relative': False, 'position': "top"},
        title = {"text": "Federal Refund Increase from Pre-Tax Planning"},
        domain = {'x': [0, 1], 'y': [0, 1]}
    ))
    st.plotly_chart(fig_plan, use_container_width=True)

    with st.expander("🔍 View Technical Breakdown"):
        st.write(f"Federal Taxable Income: **${fed_taxable:,.0f}**")
        st.write(f"Effective SALT Cap: **${salt_cap:,.0f}**")
        st.write(f"NJ Tax Rate Ratio: **{income_ratio*100:.1f}%** of income taxed by NY.")
