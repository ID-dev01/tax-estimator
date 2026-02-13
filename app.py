import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2025-2026 TAX RULES ---
LAW = {
    "Fed": {"std": 31500.0, "ctc": 2200.0, "loss_limit": 3000.0, "salt_cap": 10000.0},
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)],
        "prop_cap": 15000.0, "exemption": 1000.0
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

st.set_page_config(layout="wide", page_title="Full Household Auditor")
st.title("🛡️ 2025-2026 Full Household Tax Auditor")

col_in, col_res = st.columns([1.5, 1], gap="large")

with col_in:
    st.markdown("### 1. W-2 Details")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("👤 Your Info (NJ Job)")
        y_b1 = st.number_input("Box 1: Fed Wages", 0.0, key="y1")
        y_b16 = st.number_input("Box 16: NJ Wages", 0.0, key="y16")
        y_fwh = st.number_input("Box 2: Fed Withholding", 0.0, key="y2")
        y_swh = st.number_input("Box 17: NJ Withholding", 0.0, key="y17")
    with c2:
        st.caption("🗽 Spouse Info (NY Job)")
        s_b1 = st.number_input("Box 1: Fed Wages ", 0.0, key="s1")
        s_b16 = st.number_input("Box 16: State Wages ", 0.0, key="s16")
        s_fwh = st.number_input("Box 2: Fed Withholding ", 0.0, key="s2")
        s_ny_wh = st.number_input("Box 17: NY State Tax", 0.0, key="s17ny")

    st.markdown("### 2. Investments & Interest (1099)")
    b1, b2, b3 = st.columns(3)
    int_inc = b1.number_input("1099-INT (Interest)", 0.0)
    brk_gain = b2.number_input("Brokerage Gains", 0.0)
    brk_loss = b3.number_input("Brokerage Losses (as Positive)", 0.0)
    
    st.markdown("### 3. Home & Family (1098)")
    h1, h2, h3 = st.columns(3)
    mrtg_int = h1.number_input("1098 Mortgage Int", 0.0)
    prop_tax = h2.number_input("Property Tax Paid", 0.0)
    num_kids = h3.number_input("Children (<17)", 0, 10, 0)

# --- CALCULATIONS ---
# Investment Logic
net_brokerage = brk_gain - brk_loss
fed_inv = max(net_brokerage, -LAW["Fed"]["loss_limit"])
nj_inv = max(0, net_brokerage) # NJ doesn't allow loss offsets against wages

# Federal Math
fed_agi = y_b1 + s_b1 + int_inc + fed_inv
# Itemized vs Standard
total_salt = min(LAW["Fed"]["salt_cap"], prop_tax + y_swh + s_ny_wh)
fed_deduct = max(LAW["Fed"]["std"], mrtg_int + total_salt)
fed_taxable = max(0, fed_agi - fed_deduct)
fed_tax_raw = calc_tax(fed_taxable, [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24)])
fed_final_tax = max(0, fed_tax_raw - (num_kids * LAW["Fed"]["ctc"]))
fed_refund = (y_fwh + s_fwh) - fed_final_tax

# NJ Math
nj_gross = y_b16 + s_b1 + int_inc + nj_inv
nj_deduct = 2000.0 + (num_kids * LAW["NJ"]["exemption"]) + min(prop_tax, LAW["NJ"]["prop_cap"])
nj_taxable = max(0, nj_gross - nj_deduct)
nj_tax_raw = calc_tax(nj_taxable, LAW["NJ"]["brackets"])
# NY Credit
ny_liab = calc_tax(max(0, s_b1 - LAW["NY"]["std"]), LAW["NY"]["brackets"])
nj_credit = min(ny_liab, nj_tax_raw * (s_b1 / max(1, nj_gross)))
nj_final_tax = max(0, nj_tax_raw - nj_credit)
nj_refund = y_swh - nj_final_tax

with col_res:
    st.header("Results")
    st.metric("Federal Refund/Owed", f"${fed_refund:,.2f}")
    st.metric("NJ State Refund/Owed", f"${nj_refund:,.2f}")

    # Charts
    fig = go.Figure(data=[
        go.Bar(name='Fed', x=['Refund'], y=[fed_refund], marker_color='#002d72'),
        go.Bar(name='NJ', x=['Refund'], y=[nj_refund], marker_color='#28a745')
    ])
    st.plotly_chart(fig, use_container_width=True)

    # THE $5,000 EXPLAINER
    st.divider()
    st.subheader("💡 Why is my result >$5,000?")
    
    if fed_refund > 5000:
        st.write("✅ **High Fed Refund:** Likely due to the **Child Tax Credit ($2,200/kid)** combined with high **Itemized Deductions** (Mortgage Interest).")
    elif fed_refund < -5000:
        st.error("⚠️ **Large Fed Tax Owed:** Your 1099 interest and brokerage gains likely didn't have any tax withheld, or your W-4 at work is set too low for your combined income bracket.")

    if nj_refund > 5000:
        st.write(f"✅ **High NJ Refund:** This is driven by the **NY Tax Credit (-${nj_credit:,.0f})**. Your spouse paid NY, and NJ is giving you that money back since you're a resident.")
