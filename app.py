import streamlit as st
import plotly.express as px
import pandas as pd

# --- 2026 OBBBA CONFIGURATION ---
st.set_page_config(page_title="2026 Dual-Income Tax Optimizer", layout="wide")

FED_DATA = {
    "Single": {
        "std_deduct": 16100, 
        "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)],
        "salt_phaseout": 252500,
        "salt_base_cap": 20200,
        "hsa_max": 4400
    },
    "Married Filing Jointly": {
        "std_deduct": 32200, 
        "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)],
        "salt_phaseout": 505000,
        "salt_base_cap": 40400,
        "hsa_max": 8750
    }
}

def calculate_federal_tax(taxable_income, status):
    tax, prev_limit = 0.0, 0.0
    for limit, rate in FED_DATA[status]["brackets"]:
        if taxable_income > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (taxable_income - prev_limit) * rate
            break
    return tax

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    mode = st.radio("Optimization Mode", ["Manual (Binary)", "Auto-Optimize (Max)"])
    st.divider()
    status = st.selectbox("Filing Status", list(FED_DATA.keys()))
    dependents = st.number_input("Children (Under 17)", 0, 10)

# --- INPUT TABS ---
t_w2, t_invest, t_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments", "📑 Deductions"])

with t_w2:
    st.subheader("W-2 Wage Statements")
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
        else:
            sp_wages = sp_fed_wh = sp_st_wh = 0.0

with t_invest:
    st.subheader("Fidelity & HYSA Income")
    c1, c2 = st.columns(2)
    with c1:
        int_inc = st.number_input("1099-INT: Total Interest", 0.0)
        ord_div = st.number_input("1099-DIV: Ordinary Dividends", 0.0)
    with c2:
        stock_gl = st.number_input("Net Capital Gain/Loss", min_value=None, value=0.0)
    
    loss_adj = max(stock_gl, -3000.0) if stock_gl < 0 else stock_gl
    total_income = tp_wages + sp_wages + int_inc + ord_div + loss_adj

with t_deduct:
    st.subheader("Deduction Selection")
    if mode == "Auto-Optimize (Max)":
        st.success("🚀 **Auto-Mode:** Applying max legal deductions for 2026.")
        hsa, student_loan = FED_DATA[status]["hsa_max"], 2500.0
        prop_tax = 15000.0
        mort_int = st.number_input("Enter Mortgage Interest (Form 1098)", 0.0)
    else:
        d1, d2 = st.columns(2)
        with d1:
            hsa = FED_DATA[status]["hsa_max"] if st.checkbox("Take Max HSA") else 0.0
            student_loan = 2500.0 if st.checkbox("Take Max Student Loan Interest") else 0.0
        with d2:
            prop_tax = st.number_input("Property Tax Paid", 0.0)
            mort_int = st.number_input("Mortgage Interest Paid", 0.0)

# --- CALCULATION ENGINE ---
agi = max(0.0, total_income - hsa - student_loan)

# SALT Phase-out
base_cap, threshold = FED_DATA[status]["salt_base_cap"], FED_DATA[status]["salt_phaseout"]
salt_cap = max(10000, base_cap - ((agi - threshold) * 0.30)) if agi > threshold else base_cap
actual_salt = min((prop_tax + tp_st_wh + sp_st_wh), salt_cap)

# Deductions
itemized_total = actual_salt + mort_int
final_deduction = max(itemized_total, FED_DATA[status]["std_deduct"])
taxable_income = max(0.0, agi - final_deduction)

# Taxes
fed_tax_due = calculate_federal_tax(taxable_income, status) - (dependents * 2000)
# Reference tax (with no deductions) to calculate "Tax Savings"
raw_tax = calculate_federal_tax(total_income, status)
tax_savings = raw_tax - fed_tax_due

total_wh = tp_fed_wh + sp_fed_wh
refund_owed = total_wh - fed_tax_due

# --- VISUALIZATION SECTION ---
st.divider()
st.header("📈 Income & Tax Analytics")
viz_col1, viz_col2 = st.columns([1, 2])

with viz_col1:
    if status == "Married Filing Jointly" and (tp_wages > 0 or sp_wages > 0):
        st.write("### **Income Split**")
        df_pie = pd.DataFrame({
            "Person": ["Taxpayer", "Spouse", "Investments"],
            "Amount": [tp_wages, sp_wages, int_inc + ord_div + max(0, stock_gl)]
        })
        fig = px.pie(df_pie, values="Amount", names="Person", hole=0.4, 
                     color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("### **Income Breakdown**")
        st.info("Investments vs Wages chart appears here.")

with viz_col2:
    st.write("### **Efficiency Metrics**")
    m1, m2 = st.columns(2)
    m1.metric("Taxable Income", f"${taxable_income:,.0f}", 
              delta=f"-${(total_income - taxable_income):,.0f} (Deducted)", delta_color="normal")
    m2.metric("Federal Refund", f"${refund_owed:,.0f}", 
              delta=f"${tax_savings:,.0f} saved by deductions", delta_color="normal")
    
    st.write("---")
    st.write(f"**Tax Bracket Insight:** Your effective tax rate is **{((fed_tax_due/agi)*100) if agi > 0 else 0:.1f}%**.")
