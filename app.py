import streamlit as st

# --- 2026 CONFIGURATION ---
st.set_page_config(page_title="2026 Tax & Savings Tracker", layout="wide")

FED_DATA = {
    "Single": {"std_deduct": 16100, "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)]},
    "Married Filing Jointly": {"std_deduct": 32200, "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)]}
}
STATE_RATES = {"NJ": 0.055, "NY": 0.062, "CT": 0.055, "CA": 0.093}

def calculate_federal_tax(taxable_income, status):
    tax = 0.0
    prev_limit = 0.0
    for limit, rate in FED_DATA[status]["brackets"]:
        if taxable_income > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (taxable_income - prev_limit) * rate
            break
    return tax

def clear_all_data():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Tax Profile")
    status = st.selectbox("Filing Status", list(FED_DATA.keys()))
    residence = st.selectbox("State of Residence", ["NJ", "NY", "CT"])
    dependents = st.number_input("Children (Under 17)", 0, 10)
    st.divider()
    if st.button("🗑️ Reset All Data"): clear_all_data()

# --- INPUT TABS ---
t_w2, t_invest, t_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments & HYSA", "🏠 Deductions"])

with t_w2:
    st.subheader("W-2 Wage Statements")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Partner 1**")
        tp_wages = st.number_input("W-2 Box 1 (Fed Wages)", 0.0, key="tp_w")
        tp_st_wages = st.number_input("W-2 Box 16 (State Wages)", 0.0, key="tp_sw")
        tp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld)", 0.0, key="tp_fw")
        tp_st_wh = st.number_input("W-2 Box 17 (State Withheld)", 0.0, key="tp_swh")
        tp_work_st = st.selectbox("Box 15 (Work State)", ["NJ", "NY", "CA"], key="tp_st")
    
    with col2:
        if status == "Married Filing Jointly":
            st.markdown("**Partner 2**")
            sp_wages = st.number_input("W-2 Box 1 (Fed Wages) ", 0.0, key="sp_w")
            sp_st_wages = st.number_input("W-2 Box 16 (State Wages) ", 0.0, key="sp_sw")
            sp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld) ", 0.0, key="sp_fw")
            sp_st_wh = st.number_input("W-2 Box 17 (State Withheld) ", 0.0, key="sp_swh")
            sp_work_st = st.selectbox("Box 15 (Work State) ", ["NJ", "NY", "CA"], key="sp_st")
        else:
            sp_wages = sp_st_wages = sp_fed_wh = sp_st_wh = 0.0
            sp_work_st = residence

with t_invest:
    st.subheader("Fidelity & Savings Data")
    
    with st.expander("🔍 Where to find these numbers?"):
        st.write("""
        - **1099-INT:** Use 'Year-to-Date' interest from your December HYSA statement.
        - **1099-DIV:** Use 'Total Ordinary Dividends' from your Fidelity YTD Tax Info.
        - **1099-B:** Use 'Total Realized Gain/Loss'. It's okay if this is negative!
        """)

    col_bank, col_broker = st.columns(2)
    with col_bank:
        st.markdown("##### **🏦 Savings & HYSA (1099-INT)**")
        int_inc = st.number_input("Total Interest Income", 0.0, help="Ally, Marcus, Wealthfront, etc.")
        fed_int_wh = st.number_input("Fed Tax Withheld (Bank)", 0.0)

    with col_broker:
        st.markdown("##### **📈 Brokerage (1099-DIV)**")
        ord_div = st.number_input("Ordinary Dividends", 0.0)
        fed_div_wh = st.number_input("Fed Tax Withheld (Broker)", 0.0)

    st.divider()
    st.markdown("##### **📉 Stock Sales (1099-B)**")
    # THE FIX: Added min_value=None to allow negative numbers
    realized_gain_loss = st.number_input("Net Realized Gain/Loss", min_value=None, value=0.0, 
                                        help="Fidelity often shows this as a negative number in red if you have a loss.")
    prior_carryover = st.number_input("Prior Year Carryover Loss", 0.0)

    # UPDATED CALCULATION LOGIC
    total_net_stock_math = realized_gain_loss - prior_carryover
    
    if total_net_stock_math < 0:
        # IRS Limit: You can only deduct up to $3000 against W-2 income
        loss_deduction = max(total_net_stock_math, -3000.0)
        remaining_carryover = total_net_stock_math - loss_deduction
    else:
        loss_deduction = total_net_stock_math
        remaining_carryover = 0.0

with t_deduct:
    st.subheader("Deductions")
    st_local = st.number_input("State & Local Taxes (SALT)", 0.0, 40000.0)
    mortgage = st.number_input("Mortgage Interest", 0.0)
    charity = st.number_input("Charity", 0.0)
    total_itemized = st_local + mortgage + charity
    final_deduct = max(total_itemized, FED_DATA[status]["std_deduct"])

# --- CORE CALCULATIONS ---
total_income = tp_wages + sp_wages + ord_div + int_inc + loss_deduction
fed_taxable = max(0.0, total_income - final_deduct)
fed_tax_bill = calculate_federal_tax(fed_taxable, status) - (dependents * 2000)

# State Calculation
home_tax_raw = total_income * STATE_RATES[residence]
tp_foreign_tax = tp_st_wages * STATE_RATES.get(tp_work_st, 0.05) if tp_work_st != residence else 0
sp_foreign_tax = sp_st_wages * STATE_RATES.get(sp_work_st, 0.05) if sp_work_st != residence else 0
total_credit = min(home_tax_raw, tp_foreign_tax + sp_foreign_tax)
final_home_tax = home_tax_raw - total_credit

# --- RESULTS ---
st.divider()
st.header("📋 Final 2026 Estimate")
r1, r2, r3 = st.columns(3)

with r1:
    st.metric("Adjusted Gross Income", f"${total_income:,.0f}")
    total_wh = tp_fed_wh + sp_fed_wh + fed_int_wh + fed_div_wh
    fed_bal = total_wh - fed_tax_bill
    if fed_bal >= 0: st.success(f"Federal Refund: ${fed_bal:,.0f}")
    else: st.error(f"Federal Owed: ${abs(fed_bal):,.0f}")

with r2:
    st.metric(f"{residence} State Tax", f"${final_home_tax:,.0f}")
    st_bal = (tp_st_wh + sp_st_wh) - (tp_foreign_tax + sp_foreign_tax) - final_home_tax
    if st_bal >= 0: st.success(f"State Refund: ${st_bal:,.0f}")
    else: st.error(f"State Owed: ${abs(st_bal):,.0f}")

with r3:
    st.metric("Loss Carryover to 2027", f"${abs(remaining_carryover):,.0f}")
    st.caption("Unused stock losses that save you money next year.")
