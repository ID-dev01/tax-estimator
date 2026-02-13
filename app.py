import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2025-2026 TAX RULES ---
LAW = {
    "Fed": {"std": 31500.0, "ctc": 2200.0, "loss_limit": 3000.0},
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)],
        "prop_cap": 15000.0
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

st.set_page_config(layout="wide", page_title="Tax Auditor")
st.title("🛡️ 2025 Household Tax Auditor")

col_in, col_res = st.columns([1.5, 1], gap="large")

with col_in:
    st.subheader("1. Wage & Tax Inputs")
    c1, c2 = st.columns(2)
    with c1:
        y_b1 = st.number_input("Your Box 1 (Fed Wages)", 0.0)
        y_fwh = st.number_input("Your Box 2 (Fed Withholding)", 0.0)
        y_swh = st.number_input("Your Box 17 (NJ Withholding)", 0.0)
    with c2:
        s_b1 = st.number_input("Spouse Box 1 (Fed Wages)", 0.0)
        s_fwh = st.number_input("Spouse Box 2 (Fed Withholding)", 0.0)
        s_ny_wh = st.number_input("Spouse Box 17 (NY Tax Paid)", 0.0)

    st.subheader("2. Brokerage & 1099")
    b1, b2 = st.columns(2)
    brokerage_gain = b1.number_input("Total Investment Gains", 0.0)
    # Changed to positive input for ease of use
    brokerage_loss = b2.number_input("Total Investment Losses (Enter as Positive)", 0.0)
    
    st.subheader("3. Home & Family")
    h1, h2 = st.columns(2)
    prop_tax = h1.number_input("Property Taxes Paid", 0.0)
    num_kids = h2.number_input("Children Under 17", 0, 10, 0)

# --- ENGINE ---
# Net Brokerage Math
net_brokerage = brokerage_gain - brokerage_loss

# Federal: Allow up to $3k loss offset
fed_investment_impact = max(net_brokerage, -LAW["Fed"]["loss_limit"])
fed_agi = y_b1 + s_b1 + fed_investment_impact
fed_taxable = max(0, fed_agi - LAW["Fed"]["std"])
fed_tax = calc_tax(fed_taxable, [(23850, 0.10), (96950, 0.12), (206700, 0.22)])
fed_refund = (y_fwh + s_fwh) - max(0, fed_tax - (num_kids * LAW["Fed"]["ctc"]))

# NJ: Losses ONLY offset gains. Cannot go below $0.
nj_investment_impact = max(0, net_brokerage)
nj_gross = y_b1 + s_b1 + nj_investment_impact
nj_taxable = max(0, nj_gross - min(prop_tax, LAW["NJ"]["prop_cap"]) - (num_kids * 1000) - 2000)
nj_tax_raw = calc_tax(nj_taxable, LAW["NJ"]["brackets"])

# NY Credit
ny_liab = calc_tax(max(0, s_b1 - LAW["NY"]["std"]), LAW["NY"]["brackets"])
nj_credit = min(ny_liab, nj_tax_raw * (s_b1 / max(1, nj_gross)))
nj_refund = y_swh - max(0, nj_tax_raw - nj_credit)

with col_res:
    st.subheader("Final Summary")
    
    # Graphs
    fig = go.Figure(data=[
        go.Bar(name='Federal', x=['Refund'], y=[fed_refund], marker_color='#002d72'),
        go.Bar(name='NJ State', x=['Refund'], y=[nj_refund], marker_color='#28a745')
    ])
    fig.update_layout(barmode='group', height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.metric("Federal Refund", f"${fed_refund:,.2f}")
    st.metric("NJ State Refund", f"${nj_refund:,.2f}")

    with st.expander("Why is the Brokerage different?"):
        st.write(f"**Federal:** Used **${abs(fed_investment_impact):,.2f}** of your loss to lower your tax.")
        st.write(f"**NJ State:** NJ ignored your loss because you have no other gains to offset. NJ taxable income remains based on wages.")
