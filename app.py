import streamlit as st

# --- 2026 CONFIGURATION (Filing 2025 Taxes) ---
st.set_page_config(page_title="2026 Tax & Investment Tracker", layout="wide")

# Updated 2025/2026 IRS Data (Estimates based on current legislation)
FED_DATA = {
    "Single": {"std_deduct": 16100, "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)]},
    "Married Filing Jointly": {"std_deduct": 32200, "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)]}
}
STATE_RATES = {"NJ": 0.055, "NY": 0.062, "CT": 0.055, "CA": 0.093}

def calculate_federal_tax(taxable_income, status):
    tax = 0
    prev_limit = 0
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
    if st.button("🗑️ Reset App"):
        clear_all_data()

# --- INPUT TABS ---
t_w2, t_invest, t_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments (1099)", "🏠 Deductions"])

with t_w2:
    st.subheader("W-2 Wage Statements")
    st.info("💡 **Box Info:** Use Box 1 for Federal Wages, Box 16 for State Wages, and Box 17 for State Tax.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Partner 1**")
        tp_wages = st.number_input("W-2 Box 1 (Fed Wages)", 0.0, key="tp_w")
        tp_st_wages = st.number_input("W-2 Box 16 (State Wages)", 0.0, key="tp_sw")
        tp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld)", 0.0, key="tp_fw")
        tp_st_wh = st.number_input("W-2 Box 17 (State Withheld)", 0.0, key="tp_swh")
        tp_work_st = st.selectbox("W-2 Box 15 (Work State)", ["NJ", "NY", "CA"], key="tp_st")
    
    with col2:
        if status == "Married Filing Jointly":
            st.markdown("**Partner 2**")
            sp_wages = st.number_input("W-2 Box 1 (Fed Wages) ", 0.0, key="sp_w")
            sp_st_wages = st.number_input("W-2 Box 16 (State Wages) ", 0.0, key="sp_sw")
            sp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld) ", 0.0, key="sp_fw")
            sp_st_wh = st.number_input("W-2 Box 17 (State Withheld) ", 0.0, key="sp_swh")
            sp_work_st = st.selectbox("W-2 Box 15 (Work State) ", ["NJ", "NY", "CA"], key="sp_st")
        else:
            sp_wages = sp_st_wages = sp_fed_wh = sp_st_wh = 0.0
            sp_work_st = residence

with t_invest:
    st.subheader("Brokerage & Investment Info")
    st.caption("Pull these numbers from your 'Tax Info YTD' summary or consolidated 1099.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### **Dividends & Interest**")
        ord_div = st.number_input("1099-DIV Box 1a: Ordinary Dividends", 0.0, help="Total dividends received for the year")
        int_inc = st.number_input("1099-INT Box 1: Interest Income", 0.0)
    
    with c2:
        st.markdown("##### **Capital Gains/Losses (1099-B)**")
        realized_gain_loss = st.number_input("Total Realized Gain/Loss", 0.0, help="Net profit or loss from sales")
        prior_carryover = st.number_input("Prior Year Carryover Loss", 0.0, help="Losses from previous tax years")

    # Capital Loss Carryover Logic
    total_net_loss_gain = realized_gain_loss - prior_carryover
    
    if total_net_loss_gain < 0:
        loss_deduction = max(total_net_loss_gain, -3000.0)
        remaining_carryover = total_net_loss_gain - loss_deduction
    else:
        loss_deduction = total_net_loss_gain
        remaining_carryover = 0

with t_deduct:
    st.subheader("Deductions")
    st.write("Itemized expenses are compared against your Standard Deduction automatically.")
    salt_cap = 40000 # 2025/2026 SALT cap limit
    st_local = st.number_input("State & Local Taxes (SALT)", 0.0, float(salt_cap), help="Property and state taxes paid")
    mortgage = st.number_input("Mortgage Interest (Form 1098)", 0.0)
    charity = st.number_input("Charitable Donations", 0.0)
    
    total_itemized = st_local + mortgage + charity
    final_deduct = max(total_itemized, FED_DATA[status]["std_deduct"])

# --- CALCULATIONS ---
# 1. Federal Adjusted Gross Income (AGI)
total_income = tp_wages + sp_wages + ord_div + int_inc + loss_deduction
fed_taxable = max(0.0, total_income - final_deduct)
fed_tax_bill = calculate_federal_tax(fed_taxable, status) - (dependents * 2000)

# 2. State Credit Logic
def get_state_liability(w_st, w_inc, res_st):
    foreign_tax_paid = w_inc * STATE_RATES.get(w_st, 0.05)
    return foreign_tax_paid if w_st != res_st else 0

tp_foreign_tax = get_state_liability(tp_work_st, tp_st_wages, residence)
sp_foreign_tax = get_state_liability(sp_work_st, sp_st_wages, residence)

home_tax_raw = total_income * STATE_RATES[residence]
total_credit = min(home_tax_raw, tp_foreign_tax + sp_foreign_tax)
final_home_tax = home_tax_raw - total_credit

# --- RESULTS ---
st.divider()
st.header("📋 2026 Tax Estimate Summary")
res1, res2, res3 = st.columns(3)

with res1:
    st.metric("Total Income (AGI)", f"${total_income:,.0f}")
    fed_bal = (tp_fed_wh + sp_fed_wh) - fed_tax_bill
    if fed_bal >= 0: st.success(f"Fed Refund: ${fed_bal:,.0f}")
    else: st.error(f"Fed Owed: ${abs(fed_bal):,.0f}")

with res2:
    st.metric(f"{residence} State Tax", f"${final_home_tax:,.0f}")
    st_bal = (tp_st_wh + sp_st_wh) - (tp_foreign_tax + sp_foreign_tax) - final_home_tax
    if st_bal >= 0: st.success(f"State Refund: ${st_bal:,.0f}")
    else: st.error(f"State Owed: ${abs(st_bal):,.0f}")

with res3:
    st.metric("Next Year Carryover", f"${abs(remaining_carryover):,.0f}")
    st.caption(f"Based on ${abs(total_net_loss_gain):,.0f} net losses")
