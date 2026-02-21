import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- 2026 MASTER DATA ---
LAW_2026 = {
    "Fed": {
        "MFJ": {
            "std": 32200, "salt_cap": 40000, "salt_phase": 500000, "ctc": 2200, "ctc_phase": 400000,
            "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]
        }
    },
    "NJ": {
        "brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (float('inf'), 0.1075)],
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

st.set_page_config(layout="wide", page_title="2026 Tax Auditor")
st.title("📊 2026 Master Tax Auditor & Paycheck Fixer")

# --- SIDEBAR: PRE-TAX PLANNING ---
with st.sidebar:
    st.header("🚀 2026 Planning Tools")
    st.info("Use these to see how 'Pre-Tax' changes affect your refund.")
    add_contrib = st.slider("Increase 401(k)/HSA by:", 0, 30000, 5000)
    pay_periods = st.number_input("Paychecks left in 2026", 1, 26, 20)

# --- 1. INCOME INPUTS (With W-2 Box Notations) ---
col_u, col_s = st.columns(2)

with col_u:
    st.header("👤 Your Income (NJ)")
    y_wages = st.number_input("Federal Wages (W-2 Box 1)", value=145000.0)
    y_fwh = st.number_input("Federal Withheld (W-2 Box 2)", value=19000.0)
    y_swh = st.number_input("NJ State Withheld (W-2 Box 17)", value=7000.0)
    y_k = st.number_input("401(k) Contribution (W-2 Box 12, Code D)", value=10000.0)

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_wages = st.number_input("Federal Wages (W-2 Box 1)", value=135000.0)
    s_fwh = st.number_input("Federal Withheld (W-2 Box 2)", value=17000.0)
    s_ny_tax = st.number_input("Actual NY Tax Paid (W-2 Box 17 / NY IT-203)", value=9500.0)
    s_k = st.number_input("401(k) Contribution (W-2 Box 12, Code D)", value=10000.0)

st.divider()
c1, c2 = st.columns(2)
prop_tax = c1.number_input("Property Taxes Paid", value=16500.0)
mrtg_int = c1.number_input("Mortgage Interest", value=22000.0)
kids = c2.number_input("Qualifying Children (<17)", value=2)

# --- 2. THE CALCULATION ENGINE ---
agi = (y_wages + s_wages) - add_contrib # Current AGI plus any new planning shift
f_conf = LAW_2026["Fed"]["MFJ"]

# SALT Calculation
salt_cap = max(10000, f_conf["salt_cap"] - (max(0, agi - f_conf["salt_phase"]) * 0.30))
total_salt_paid = prop_tax + y_swh + s_ny_tax
allowed_salt = min(total_salt_paid, salt_cap)

# Federal Liability
fed_deduct = max(f_conf["std"], mrtg_int + allowed_salt)
fed_taxable = max(0, agi - fed_deduct)
ctc = max(0, (kids * f_conf["ctc"]) - ((max(0, agi - f_conf["ctc_phase"]) // 1000) * 50))
fed_liab = max(0, calc_tax(fed_taxable, f_conf["brackets"]) - ctc)
fed_diff = (y_fwh + s_fwh) - fed_liab

# NJ Resident Credit (Schedule NJ-COJ)
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
nj_credit_ratio = (s_wages - s_k) / max(1, agi)
nj_credit = min(s_ny_tax, nj_tax_pre_credit * nj_credit_ratio)
nj_liab = nj_tax_pre_credit - nj_credit
nj_diff = y_swh - nj_liab

# --- 3. DYNAMIC GRAPHS ---
st.header("📊 Interactive Visuals")
g1, g2, g3 = st.columns(3)

with g1:
    fig_pie = go.Figure(data=[go.Pie(
        labels=['Take Home', 'Fed Tax', 'NJ State Tax', 'Deductions'],
        values=[agi - fed_liab - nj_liab, fed_liab, nj_liab, fed_deduct],
        hole=.4, marker_colors=['#2ECC71', '#E74C3C', '#F1C40F', '#3498DB']
    )])
    fig_pie.update_layout(title="Income Allocation", margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    fig_salt = go.Figure(go.Indicator(
        mode = "gauge+number", value = allowed_salt,
        title = {'text': f"SALT Cap: ${salt_cap:,.0f}"},
        gauge = {'axis': {'range': [0, 40000]}, 'bar': {'color': "#3498DB"},
                 'threshold': {'line': {'color': "red", 'width': 4}, 'value': salt_cap}}
    ))
    fig_salt.update_layout(height=250)
    st.plotly_chart(fig_salt, use_container_width=True)

with g3:
    fig_nj = go.Figure(data=[
        go.Bar(name='Gross NJ Tax', x=['Tax'], y=[nj_tax_pre_credit], marker_color='#E74C3C'),
        go.Bar(name='NY Credit', x=['Tax'], y=[nj_credit], marker_color='#2ECC71')
    ])
    fig_nj.update_layout(barmode='stack', title="NJ-NY Tax Shield", height=250)
    st.plotly_chart(fig_nj, use_container_width=True)

# --- 4. THE PAYCHECK FIXER ---
st.divider()
st.header("🛠️ Paycheck Correction (W-4)")
if fed_diff < -1000 or nj_diff < -500:
    st.error(f"You are underpaying by **${abs(fed_diff + nj_diff):,.2f}**.")
    f_fix = abs(min(0, fed_diff))/pay_periods
    n_fix = abs(min(0, nj_diff))/pay_periods
    
    fx1, fx2 = st.columns(2)
    fx1.metric("Federal W-4 Line 4(c)", f"${f_fix:,.2f} / check")
    fx2.metric("NJ-W4 Line 5", f"${n_fix:,.2f} / check")
else:
    st.success(f"Estimated Combined Refund: **${(fed_diff + nj_diff):,.2f}**")

# --- 5. TECHNICAL SUMMARY ---
with st.expander("🔍 View Filing Details"):
    st.table(pd.DataFrame({
        "Category": ["Federal AGI", "Fed Taxable", "NJ Taxable", "NY Resident Credit"],
        "Value": [f"${agi:,.2f}", f"${fed_taxable:,.2f}", f"${nj_taxable:,.2f}", f"${nj_credit:,.2f}"]
    }))
