import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# --- 2026 MASTER DATA (Post-OBBBA Legislation) ---
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

st.set_page_config(layout="wide", page_title="2026 Master Tax Auditor")
st.title("📊 2026 Master Tax Auditor & Paycheck Fixer")

# --- 1. INPUT SECTION (Spouse-Specific) ---
with st.sidebar:
    st.header("🚀 Pre-Tax Planning")
    add_401k = st.slider("Additional 401(k) / HSA Contribution", 0, 30000, 5000)
    pay_periods = st.number_input("Paychecks left in 2026", 1, 26, 20)

col_u, col_s = st.columns(2)
with col_u:
    st.subheader("👤 Your Income (NJ)")
    y_wages = st.number_input("Your W-2 Wages", value=145000.0)
    y_fwh = st.number_input("Your Fed Withheld", value=19000.0)
    y_swh = st.number_input("Your NJ Withheld", value=7000.0)
    y_k = st.number_input("Your Current 401k/HSA", value=10000.0)

with col_s:
    st.subheader("👤 Spouse Income (NY)")
    s_wages = st.number_input("Spouse W-2 Wages", value=135000.0)
    s_fwh = st.number_input("Spouse Fed Withheld", value=17000.0)
    s_ny_tax = st.number_input("Spouse NY Tax Liability", value=9500.0)
    s_k = st.number_input("Spouse Current 401k/HSA", value=10000.0)

prop_tax = st.number_input("Household Property Taxes", value=16500.0)
mrtg_int = st.number_input("Mortgage Interest", value=22000.0)
kids = st.number_input("Qualifying Children", value=2)

# --- 2. THE ENGINE ---
agi = (y_wages + s_wages) - (y_k + s_k + add_401k)
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

# NJ Credit (NJ-COJ)
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["brackets"])
nj_credit_ratio = (s_wages - s_s_k if 's_s_k' in locals() else s_wages) / max(1, agi)
nj_credit = min(s_ny_tax, nj_tax_pre_credit * nj_credit_ratio)
nj_liab = nj_tax_pre_credit - nj_credit
nj_diff = y_swh - nj_liab

# --- 3. VISUALS (THE GRAPHS ARE BACK) ---
st.divider()
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    st.subheader("Income Waterfall")
    fig_pie = go.Figure(data=[go.Pie(
        labels=['Net Pay', 'Federal Tax', 'NJ State Tax', 'Deductions'],
        values=[agi - fed_liab - nj_liab, fed_liab, nj_liab, fed_deduct],
        hole=.4, marker_colors=['#2ECC71', '#E74C3C', '#F1C40F', '#3498DB']
    )])
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("SALT Cap Utilization")
    fig_salt = go.Figure(go.Indicator(
        mode = "gauge+number", value = allowed_salt,
        title = {'text': f"Cap: ${salt_cap:,.0f}"},
        gauge = {'axis': {'range': [0, 40000]}, 'bar': {'color': "#3498DB"},
                 'threshold': {'line': {'color': "red", 'width': 4}, 'value': salt_cap}}
    ))
    st.plotly_chart(fig_salt, use_container_width=True)

with c3:
    st.subheader("NJ-NY Resident Credit")
    fig_nj = go.Figure(data=[
        go.Bar(name='NJ Tax Owed', x=['State'], y=[nj_tax_pre_credit], marker_color='#E74C3C'),
        go.Bar(name='NY Credit', x=['State'], y=[nj_credit], marker_color='#2ECC71')
    ])
    fig_nj.update_layout(barmode='stack', height=300)
    st.plotly_chart(fig_nj, use_container_width=True)

# --- 4. THE PAYCHECK FIXER ---
st.divider()
st.header("🛠️ The Paycheck Fixer (W-4 Instructions)")
if fed_diff < -1000 or nj_diff < -500:
    st.error(f"Underpayment Alert: You are on track to owe **${abs(fed_diff + nj_diff):,.2f}** total.")
    f_fix, n_fix = abs(min(0, fed_diff))/pay_periods, abs(min(0, nj_diff))/pay_periods
    
    col_f, col_n = st.columns(2)
    col_f.metric("Add to Federal W-4 Line 4(c)", f"${f_fix:,.2f}")
    col_n.metric("Add to NJ-W4 Line 5", f"${n_fix:,.2f}")
else:
    st.success(f"Withholding Safe: Estimated total refund is **${(fed_diff + nj_diff):,.2f}**.")

# 5. Summary Table
st.table(pd.DataFrame({
    "Metric": ["Gross AGI", "Taxable Federal", "Taxable NJ", "Federal Refund", "NJ Refund"],
    "Value": [f"${agi:,.2f}", f"${fed_taxable:,.2f}", f"${nj_taxable:,.2f}", f"${fed_diff:,.2f}", f"${nj_diff:,.2f}"]
}))
