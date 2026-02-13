import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 2025-2026 TAX DATA (Verified) ---
LAW = {
    "Fed": {
        "std": 31500.0, 
        "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24), (501050, 0.32), (751600, 0.35)],
        "ctc": 2200.0, 
        "salt_cap": 10000.0,
        "hsa_limit": 8550.0,
        "401k_limit": 23500.0
    },
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)],
        "prop_cap": 15000.0,
        "exemption": 1000.0
    },
    "NY": {
        "std": 16050.0,
        "brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06)]
    }
}

def calc_tax(taxable, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if taxable > prev:
            amt = min(taxable, limit) - prev
            tax += amt * rate
            prev = limit
    # Handle top bracket overflow
    if taxable > brackets[-1][0]:
        top_rate = 0.37 if len(brackets) > 5 else brackets[-1][1]
        tax += (taxable - brackets[-1][0]) * top_rate
    return tax

st.set_page_config(layout="wide", page_title="2025 Final Tax Auditor")

# --- UI LAYOUT ---
st.title("🛡️ 2025-2026 Household Tax Auditor & Visualizer")
st.markdown("---")

col_in, col_res = st.columns([1.5, 1], gap="large")

with col_in:
    # Section 1: Income
    st.subheader("1. W-2 Income & Withholding")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**👤 Your W-2 (NJ)**")
        y_b1 = st.number_input("Box 1: Fed Wages", 0.0, key="y1")
        y_b16 = st.number_input("Box 16: NJ Wages", 0.0, key="y16")
        y_fwh = st.number_input("Box 2: Fed Withheld", 0.0, key="y2")
        y_swh = st.number_input("Box 17: NJ Withheld", 0.0, key="y17")
    with c2:
        st.markdown("**🗽 Spouse W-2 (NY)**")
        s_b1 = st.number_input("Box 1: Fed Wages ", 0.0, key="s1")
        s_b16 = st.number_input("Box 16: NY Wages ", 0.0, key="s16")
        s_fwh = st.number_input("Box 2: Fed Withheld ", 0.0, key="s2")
        s_ny_wh = st.number_input("Box 17: NY Tax Paid", 0.0, key="s17ny")

    # Section 2: Investments
    st.subheader("2. 1099 Interest & Brokerage")
    b1, b2, b3 = st.columns(3)
    int_inc = b1.number_input("1099-INT Interest", 0.0)
    brk_gain = b2.number_input("Brokerage Gains", 0.0)
    brk_loss = b3.number_input("Brokerage Losses (Positive #)", 0.0)

    # Section 3: Deductions
    st.subheader("3. 1098 Home & Family")
    h1, h2, h3 = st.columns(3)
    mrtg_int = h1.number_input("Mortgage Interest", 0.0)
    prop_tax = h2.number_input("Property Taxes Paid", 0.0)
    num_kids = h3.number_input("Children Under 17", 0, 10, 0)

# --- CALCULATIONS ---
# Investment Netting
net_inv = brk_gain - brk_loss
fed_inv_impact = max(net_inv, -3000.0) # Fed allows $3k loss
nj_inv_impact = max(0, net_inv)        # NJ does NOT allow wage offsets

# Federal Math
fed_agi = y_b1 + s_b1 + int_inc + fed_inv_impact
salt_total = min(LAW["Fed"]["salt_cap"], prop_tax + y_swh + s_ny_wh)
fed_deduction = max(LAW["Fed"]["std"], mrtg_int + salt_total)
fed_taxable = max(0, fed_agi - fed_deduction)
fed_liab = calc_tax(fed_taxable, LAW["Fed"]["brackets"])
fed_final_tax = max(0, fed_liab - (num_kids * LAW["Fed"]["ctc"]))
fed_result = (y_fwh + s_fwh) - fed_final_tax

# NJ State Math
nj_gross = y_b16 + s_b1 + int_inc + nj_inv_impact
nj_deduct = 2000.0 + (num_kids * LAW["NJ"]["exemption"]) + min(prop_tax, LAW["NJ"]["prop_cap"])
nj_taxable = max(0, nj_gross - nj_deduct)
nj_tax_raw = calc_tax(nj_taxable, LAW["NJ"]["brackets"])

# NY Credit Calculation (The Resident Credit)
ny_liab = calc_tax(max(0, s_b1 - LAW["NY"]["std"]), LAW["NY"]["brackets"])
nj_credit = min(ny_liab, nj_tax_raw * (s_b1 / max(1, nj_gross)))
nj_final_tax = max(0, nj_tax_raw - nj_credit)
nj_result = y_swh - nj_final_tax

# --- RESULTS DASHBOARD ---
with col_res:
    st.subheader("Final Audit Summary")
    
    # Visual 1: Bar Chart
    fig_bar = go.Figure(data=[
        go.Bar(name='Federal', x=['Fed'], y=[fed_result], marker_color='#002d72'),
        go.Bar(name='NJ State', x=['NJ'], y=[nj_result], marker_color='#28a745')
    ])
    fig_bar.update_layout(title="Refund vs. Owed", height=300)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.metric("Federal Refund/Owed", f"${fed_result:,.2f}", delta_color="normal")
    st.metric("NJ State Refund/Owed", f"${nj_result:,.2f}")

    # Section 4: Refund Strategies
    st.divider()
    st.subheader("🚀 Potential Pre-Tax Wins")
    st.write("If you had maxed these out, your Fed Owed would decrease:")
    
    strat_col1, strat_col2 = st.columns(2)
    with strat_col1:
        # HSA Simulation
        hsa_savings = LAW["Fed"]["hsa_limit"] * 0.3165 # 24% tax + 7.65% FICA
        st.info(f"**Max HSA:**\n+${hsa_savings:,.2f} Refund")
    with strat_col2:
        # 401k Simulation
        k_savings = 5000 * 0.24 # $5k more in 401k
        st.info(f"**+$5k 401(k):**\n+${k_savings:,.2f} Refund")

    # The 5k Logic Explainer
    if fed_result < -5000:
        with st.expander("🔍 Why do I owe > $5,000?"):
            st.error(f"""
            - **Investment Drag:** You have ${int_inc + max(0, net_inv):,.0f} in untaxed income.
            - **Bracket Creep:** Your combined income pushed you into the 24% bracket.
            - **SALT Cap:** You lost the ability to deduct ${max(0, salt_total - 10000):,.0f} of your state taxes.
            """)

# --- WITHHOLDING ADJUSTER ---
st.divider()
st.subheader("📈 How to Fix This for Next Year")
pay_left = st.number_input("How many paychecks left this year?", 1, 26, 22)
if fed_result < 0:
    extra_withholding = abs(fed_result) / pay_left
    st.success(f"To break even, add **${extra_withholding:,.2f}** to Line 4(c) on your Federal W-4.")
