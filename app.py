import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# --- 2026 OBBBA CONFIGURATION ---
st.set_page_config(page_title="2026 Tax Waterfall & Optimizer", layout="wide")

FED_DATA = {
    "Single": {
        "std_deduct": 16100, 
        "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24), (256225, 0.32), (640600, 0.35), (float('inf'), 0.37)],
        "salt_phaseout": 252500,
        "salt_base_cap": 20200,
        "hsa_max": 4400
    },
    "Married Filing Jointly": {
        "std_deduct": 32200, 
        "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)],
        "salt_phaseout": 505000,
        "salt_base_cap": 40400,
        "hsa_max": 8750
    }
}

def get_tax_buckets(taxable_income, status):
    buckets = []
    prev_limit = 0.0
    remaining = taxable_income
    for limit, rate in FED_DATA[status]["brackets"]:
        bracket_size = limit - prev_limit
        amount_in_bracket = min(remaining, bracket_size)
        if amount_in_bracket > 0:
            buckets.append({"Bracket": f"{int(rate*100)}%", "Amount": amount_in_bracket, "Tax": amount_in_bracket * rate})
            remaining -= amount_in_bracket
            prev_limit = limit
        else: break
    return buckets

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Optimization Mode", ["Manual (Binary)", "Auto-Optimize (Max)"])
    status = st.selectbox("Filing Status", list(FED_DATA.keys()))
    dependents = st.number_input("Children (Under 17)", 0, 10)

# --- INPUT TABS ---
t_w2, t_invest, t_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments", "📑 Deductions"])

with t_w2:
    col_tp, col_sp = st.columns(2)
    with col_tp:
        st.markdown("### **Taxpayer**")
        tp_wages = st.number_input("W-2 Box 1 (Fed Wages)", 0.0, key="tp_w1")
        tp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld)", 0.0, key="tp_w2")
        tp_st_wh = st.number_input("W-2 Box 17 (State Withheld)", 0.0, key="tp_w17")
    with col_sp:
        if status == "Married Filing Jointly":
            st.markdown("### **Spouse**")
            sp_wages = st.number_input("W-2 Box 1 (Fed Wages)", 0.0, key="sp_w1")
            sp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld)", 0.0, key="sp_w2")
            sp_st_wh = st.number_input("W-2 Box 17 (State Withheld)", 0.0, key="sp_w17")
        else: sp_wages = sp_fed_wh = sp_st_wh = 0.0

with t_invest:
    c1, c2 = st.columns(2)
    with c1:
        int_inc = st.number_input("Total Interest", 0.0)
        ord_div = st.number_input("Ordinary Dividends", 0.0)
    with c2:
        stock_gl = st.number_input("Net Capital Gain/Loss", min_value=None, value=0.0)
    loss_adj = max(stock_gl, -3000.0) if stock_gl < 0 else stock_gl
    total_income = tp_wages + sp_wages + int_inc + ord_div + loss_adj

with t_deduct:
    if mode == "Auto-Optimize (Max)":
        hsa, student_loan = FED_DATA[status]["hsa_max"], 2500.0
        prop_tax, mort_int = 20000.0, st.number_input("Enter Mortgage Interest", 0.0)
        ot_tips = 12500.0 # OBBBA Max for single taxpayer
    else:
        d1, d2 = st.columns(2)
        with d1:
            hsa = FED_DATA[status]["hsa_max"] if st.checkbox("Max HSA") else 0.0
            student_loan = 2500.0 if st.checkbox("Max Student Loan Int") else 0.0
            ot_tips = st.number_input("Overtime/Tips Deduction (OBBBA)", 0.0, 25000.0)
        with d2:
            prop_tax = st.number_input("Property Tax", 0.0)
            mort_int = st.number_input("Mortgage Interest", 0.0)

# --- CALC ENGINE ---
agi = max(0.0, total_income - hsa - student_loan - ot_tips)
base_cap, threshold = FED_DATA[status]["salt_base_cap"], FED_DATA[status]["salt_phaseout"]
salt_cap = max(10000, base_cap - ((agi - threshold) * 0.30)) if agi > threshold else base_cap
actual_salt = min((prop_tax + tp_st_wh + sp_st_wh), salt_cap)
final_deduction = max(actual_salt + mort_int, FED_DATA[status]["std_deduct"])
taxable_income = max(0.0, agi - final_deduction)

buckets = get_tax_buckets(taxable_income, status)
total_tax = sum(b['Tax'] for b in buckets) - (dependents * 2200) # OBBBA $2,200 Credit
refund = (tp_fed_wh + sp_fed_wh) - total_tax

# --- ANALYTICS ---
st.divider()
col_res, col_chart = st.columns([1, 2])

with col_res:
    st.metric("Final Refund/Owed", f"${refund:,.0f}")
    st.metric("Taxable Income", f"${taxable_income:,.0f}")
    st.write(f"Effective Rate: **{(total_tax/agi*100 if agi > 0 else 0):.1f}%**")

with col_chart:
    st.subheader("Tax Bracket Waterfall")
    df_tax = pd.DataFrame(buckets)
    fig_tax = px.bar(df_tax, x="Bracket", y="Amount", text=df_tax['Tax'].apply(lambda x: f"${x:,.0f} tax"),
                     title="Income Distribution Across Brackets", color="Bracket", color_discrete_sequence=px.colors.qualitative.Prism)
    st.plotly_chart(fig_tax, use_container_width=True)

if status == "Married Filing Jointly":
    st.write("### **Household Income Split**")
    fig_pie = px.pie(values=[tp_wages, sp_wages, total_income - (tp_wages+sp_wages)], 
                     names=["Taxpayer", "Spouse", "Other"], hole=0.4)
    st.plotly_chart(fig_pie)
