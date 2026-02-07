import streamlit as st
import plotly.express as px
import pandas as pd

# --- 2026 CONFIGURATION ---
st.set_page_config(page_title="2026 Universal Tax Optimizer", layout="wide")

FED_DATA = {
    "Single": {
        "std_deduct": 16100, "sr_boost": 2050, 
        "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)],
        "salt_base_cap": 20200, "hsa_max": 4400, "cap_loss_limit": 3000
    },
    "Married Filing Jointly": {
        "std_deduct": 32200, "sr_boost": 1650, 
        "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)],
        "salt_base_cap": 40400, "hsa_max": 8750, "cap_loss_limit": 3000
    }
}

NJ_BRACKETS_MFJ = [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)]

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0:
            tax += amt * rate
            prev = limit
        else: break
    return tax

# --- SIDEBAR: USER PROFILE ---
with st.sidebar:
    st.header("👤 User Profile")
    status = st.selectbox("Filing Status", ["Married Filing Jointly", "Single"])
    u_age = st.number_input("Your Age", 18, 100, 35)
    s_age = st.number_input("Spouse Age", 18, 100, 35) if status == "Married Filing Jointly" else 0
    is_homeowner = st.toggle("NJ Homeowner?", value=True)
    mode = st.radio("Optimization Mode", ["Manual (Binary)", "Auto-Optimize (Max)"])

# --- TABBED INTERFACE ---
t1, t2, t3, t4 = st.tabs(["💼 W-2 Income", "📈 Investments", "📑 NJ Deductions", "📊 Results"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### **Taxpayer**")
        tp_w2 = st.number_input("W-2 Fed Wages (Box 1)", 0.0, key="tpw")
        tp_fwh = st.number_input("Fed Withheld (Box 2)", 0.0, key="tpf")
        tp_swh = st.number_input("NJ State Withheld (Box 17)", 0.0, key="tps")
    with c2:
        if status == "Married Filing Jointly":
            st.markdown("### **Spouse**")
            sp_w2 = st.number_input("W-2 Fed Wages (Box 1)", 0.0, key="spw")
            sp_fwh = st.number_input("Fed Withheld (Box 2)", 0.0, key="spf")
            sp_swh = st.number_input("NJ State Withheld (Box 17)", 0.0, key="sps")
        else: sp_w2 = sp_fwh = sp_swh = 0.0

with t2:
    st.markdown("### **Capital Gains & Losses**")
    st.info("You can enter negative numbers here to represent investment losses.")
    # Allowing negative numbers via min_value=None
    st_gains = st.number_input("Short-Term Gains/Losses", min_value=None, value=0.0, step=100.0)
    lt_gains = st.number_input("Long-Term Gains/Losses", min_value=None, value=0.0, step=100.0)
    other_inv = st.number_input("Interest/Dividends (1099-INT/DIV)", 0.0)
    
    total_invest_net = st_gains + lt_gains + other_inv

with t3:
    if mode == "Auto-Optimize (Max)":
        hsa, prop_tax, mort_int = FED_DATA[status]["hsa_max"], 15000.0, st.number_input("Mortgage Interest", 0.0)
    else:
        hsa = FED_DATA[status]["hsa_max"] if st.checkbox("Apply Max HSA") else 0.0
        prop_tax = st.number_input("NJ Property Tax Paid", 0.0) if is_homeowner else 0.0
        mort_int = st.number_input("Mortgage Interest Paid", 0.0)

# --- CALCULATION ENGINE ---

# 1. Federal Investment Logic (Apply $3k loss limit)
fed_invest_income = total_invest_net
if total_invest_net < 0:
    fed_invest_income = max(total_invest_net, -FED_DATA[status]["cap_loss_limit"])

# 2. Federal Result
total_w2 = tp_w2 + sp_w2
fed_agi = max(0.0, total_w2 + fed_invest_income - hsa)
fed_tax = calc_tax(fed_agi - FED_DATA[status]["std_deduct"], FED_DATA[status]["brackets"])
fed_res = (tp_fwh + sp_fwh) - fed_tax

# 3. NJ State Logic (NJ does NOT allow negative investment income to offset W-2)
nj_invest_income = max(0.0, total_invest_net) 
nj_taxable = max(0.0, total_w2 + nj_invest_income - min(prop_tax, 15000.0))
nj_tax = calc_tax(nj_taxable, NJ_BRACKETS_MFJ)
nj_res = (tp_swh + sp_swh) - nj_tax

# 4. NJ Rebate (ANCHOR vs Stay NJ)
rebate = 0.0
rebate_type = "None"
if is_homeowner:
    total_nj_gross = total_w2 + nj_invest_income
    sr_bonus = 250.0 if (u_age >= 65 or s_age >= 65) else 0.0
    anchor = 1500.0 + sr_bonus if total_nj_gross <= 150000 else (1000.0 + sr_bonus if total_nj_gross <= 250000 else 0.0)
    stay_nj = min(6500.0, prop_tax * 0.50) if ((u_age >= 65 or s_age >= 65) and total_nj_gross < 500000) else 0.0
    rebate = max(anchor, stay_nj)
    rebate_type = "Stay NJ" if stay_nj > anchor else "ANCHOR"

with t4:
    st.header("📊 2026 Tax & Benefit Summary")
    m1, m2, m3 = st.columns(3)
    m1.metric("Federal Refund", f"${fed_res:,.0f}")
    m2.metric("NJ State Refund", f"${nj_res:,.0f}")
    m3.metric(f"NJ {rebate_type}", f"${rebate:,.0f}")

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        df_pie = pd.DataFrame({"Category": ["Federal Tax", "NJ Tax", "Net Take-Home"], 
                               "Amount": [fed_tax, nj_tax, (total_w2 + fed_invest_income) - fed_tax - nj_tax]})
        st.plotly_chart(px.pie(df_pie, values="Amount", names="Category", hole=0.5, title="Income Allocation"), use_container_width=True)
    with c4:
        # Cash Progression
        net_final = (total_w2 + fed_invest_income) - fed_tax - nj_tax + rebate
        df_bar = pd.DataFrame({"Stage": ["Gross Income", "Net After Tax", "Final w/ Rebate"], 
                               "Cash": [total_w2 + total_invest_net, (total_w2 + fed_invest_income) - fed_tax - nj_tax, net_final]})
        st.plotly_chart(px.bar(df_bar, x="Stage", y="Cash", title="Cash Flow Progression"), use_container_width=True)

    st.write(f"### **Estimated Net Cash Position: ${net_final:,.0f}**")
