import streamlit as st
import plotly.express as px
import pandas as pd

# --- TAX DATA 2025 ---
TAX_2025 = {
    "Fed": {
        "MFJ": {"std": 30000, "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24)], "hsa": 8550},
        "Single": {"std": 15000, "brackets": [(11925, 0.10), (48475, 0.12), (103350, 0.22), (197300, 0.24)], "hsa": 4300}
    },
    "NJ": {"brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)]},
    "NY": { # 2025 MFJ Brackets
        "std": 16050,
        "brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06), (2155350, 0.0685)]
    }
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0:
            tax += amt * rate
            prev = limit
        else: break
    return tax

# --- SIDEBAR: RESIDENCY & WORK ---
st.set_page_config(page_title="2025 NJ/NY Audit Tool", layout="wide")

with st.sidebar:
    st.header("👤 Profile & Residency")
    status_label = st.selectbox("Filing Status", ["Married Filing Jointly", "Single"])
    status = "MFJ" if status_label == "Married Filing Jointly" else "Single"
    
    st.divider()
    st.subheader("Work Locations")
    tp_work_state = st.selectbox("Taxpayer Work State", ["NJ", "NY", "PA (Reciprocal)"])
    sp_work_state = "NJ"
    if status == "MFJ":
        sp_work_state = st.selectbox("Spouse Work State", ["NJ", "NY", "PA (Reciprocal)"])
    
    u_age = st.number_input("Your Age", 18, 100, 35)
    is_homeowner = st.toggle("NJ Homeowner?", value=True)

# --- DATA INPUT TABS ---
t1, t2, t3, t4 = st.tabs(["💼 W-2 & State Withholding", "📈 Investments", "📑 Deductions", "📊 Results"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Taxpayer")
        tp_w2 = st.number_input("Box 1: Fed Wages", 0.0, key="tpw")
        tp_fwh = st.number_input("Box 2: Fed Withheld", 0.0, key="tpf")
        tp_swh = st.number_input("Box 17: NJ Withheld", 0.0, key="tps_nj")
        tp_owh = st.number_input(f"Box 17: {tp_work_state} Withheld", 0.0, key="tps_other") if tp_work_state != "NJ" else 0.0
    with c2:
        if status == "MFJ":
            st.markdown("### Spouse")
            sp_w2 = st.number_input("Box 1: Fed Wages", 0.0, key="spw")
            sp_fwh = st.number_input("Box 2: Fed Withheld", 0.0, key="spf")
            sp_swh = st.number_input("Box 17: NJ Withheld", 0.0, key="sps_nj")
            sp_owh = st.number_input(f"Box 17: {sp_work_state} Withheld", 0.0, key="sps_other") if sp_work_state != "NJ" else 0.0
        else: sp_w2 = sp_fwh = sp_swh = sp_owh = 0.0

with t2:
    net_cap = st.number_input("Net Capital Gain/Loss", min_value=None, value=0.0)
    int_div = st.number_input("Interest & Dividends", 0.0)
    total_inv = net_cap + int_div

with t3:
    hsa = st.number_input("HSA Contributions", 0.0, float(TAX_2025["Fed"][status]["hsa"]))
    prop_tax = st.number_input("Property Tax Paid", 0.0) if is_homeowner else 0.0

# --- CALCULATION LOGIC ---

# 1. Other State Tax (NY Logic)
def get_other_tax(wages, state):
    if state == "NY":
        return calc_tax(wages - TAX_2025["NY"]["std"], TAX_2025["NY"]["brackets"])
    return 0.0

tp_other_tax = get_other_tax(tp_w2, tp_work_state)
sp_other_tax = get_other_tax(sp_w2, sp_work_state)
total_other_tax_owed = tp_other_tax + sp_other_tax

# 2. Federal
fed_inv = max(total_inv, -3000.0) if total_inv < 0 else total_inv
total_gross = tp_w2 + sp_w2 + fed_inv
fed_tax = calc_tax(max(0, total_gross - hsa - TAX_2025["Fed"][status]["std"]), TAX_2025["Fed"][status]["brackets"])
fed_refund = (tp_fwh + sp_fwh) - fed_tax

# 3. NJ Resident Tax (Credit for NY Tax)
nj_gross = (tp_w2 + sp_w2) + max(0, total_inv)
nj_tax_pre_credit = calc_tax(max(0, nj_gross - min(prop_tax, 15000.0)), TAX_2025["NJ"]["brackets"])

# NJ Credit Logic: Credit is the LESSER of (NY Tax Owed) or (NJ Tax on that same income)
# For simplicity in this tool, we assume NY income is the W2 wages from NY
nj_tax_on_ny_income = nj_tax_pre_credit * ((tp_w2 if tp_work_state=="NY" else 0) + (sp_w2 if sp_work_state=="NY" else 0)) / max(1, nj_gross)
nj_credit = min(total_other_tax_owed, nj_tax_on_ny_income)

nj_tax_final = max(0, nj_tax_pre_credit - nj_credit)
nj_refund = (tp_swh + sp_swh) - nj_tax_final

with t4:
    st.header("📊 2025 Audit Results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fed Refund", f"${fed_refund:,.0f}")
    m2.metric("NJ Refund", f"${nj_refund:,.0f}")
    m3.metric("Other State Owed", f"${(tp_owh + sp_owh) - total_other_tax_owed:,.0f}")
    
    rebate = 1500 if is_homeowner and nj_gross <= 150000 else (1000 if is_homeowner and nj_gross <= 250000 else 0)
    m4.metric("NJ ANCHOR", f"${rebate:,.0f}")

    if tp_work_state == "NY" or sp_work_state == "NY":
        st.success(f"✅ Applied ${nj_credit:,.0f} credit to NJ return for taxes paid to NY.")

    # Chart
    df = pd.DataFrame({"Tax Authority": ["Federal", "NJ", "NY/Other"], "Total Owed": [fed_tax, nj_tax_final, total_other_tax_owed]})
    st.plotly_chart(px.bar(df, x="Tax Authority", y="Total Owed", title="Total Tax Liability by Jurisdiction"))
