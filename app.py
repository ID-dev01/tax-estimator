import streamlit as st

# --- 2026 CONFIGURATION (Filing 2025 Taxes) ---
st.set_page_config(page_title="2026 Federal & NJ Tax Tracker", layout="wide")

# Updated 2026 IRS Data (OBBBA 2025/2026 Rules)
FED_DATA = {
    "Single": {
        "std_deduct": 16100, 
        "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)],
        "salt_phaseout": 252500,
        "salt_base_cap": 20200
    },
    "Married Filing Jointly": {
        "std_deduct": 32200, 
        "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)],
        "salt_phaseout": 505000,
        "salt_base_cap": 40400
    }
}
STATE_RATES = {"NJ": 0.055, "NY": 0.062, "CT": 0.055}

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

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Tax Profile")
    status = st.selectbox("Filing Status", list(FED_DATA.keys()))
    residence = st.selectbox("State of Residence", ["NJ", "NY", "CT"])
    dependents = st.number_input("Children (Under 17)", 0, 10)
    st.divider()
    if st.button("🗑️ Reset All Data"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- INPUT TABS ---
t_w2, t_invest, t_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments & HYSA", "🏠 Deductions"])

with t_w2:
    st.subheader("W-2 Wage Statements")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Taxpayer**")
        tp_wages = st.number_input("W-2 Box 1 (Fed Wages)", 0.0, key="tp_w")
        tp_st_wages = st.number_input("W-2 Box 16 (State Wages)", 0.0, key="tp_sw")
        tp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld)", 0.0, key="tp_fw")
        tp_st_wh = st.number_input("W-2 Box 17 (State Withheld)", 0.0, key="tp_swh")
        tp_work_st = st.selectbox("Work State", ["NJ", "NY", "CA"], key="tp_st")
    
    with col2:
        if status == "Married Filing Jointly":
            st.markdown("**Spouse**")
            sp_wages = st.number_input("W-2 Box 1 (Fed Wages) ", 0.0, key="sp_w")
            sp_st_wages = st.number_input("W-2 Box 16 (State Wages) ", 0.0, key="sp_sw")
            sp_fed_wh = st.number_input("W-2 Box 2 (Fed Withheld) ", 0.0, key="sp_fw")
            sp_st_wh = st.number_input("W-2 Box 17 (State Withheld) ", 0.0, key="sp_swh")
            sp_work_st = st.selectbox("Work State ", ["NJ", "NY", "CA"], key="sp_st")
        else:
            sp_wages = sp_st_wages = sp_fed_wh = sp_st_wh = 0.0
            sp_work_st = residence

with t_invest:
    st.subheader("1099 Income & Fidelity Data")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### **Interest & Dividends**")
        int_inc = st.number_input("1099-INT: Total Interest (HYSA)", 0.0)
        ord_div = st.number_input("1099-DIV: Ordinary Dividends", 0.0)
    with c2:
        st.markdown("##### **Capital Gains/Losses**")
        real_gl = st.number_input("Net Realized Gain/Loss", min_value=None, value=0.0)
        carryover = st.number_input("Prior Year Loss Carryover", 0.0)

    # Stock Loss Logic
    net_stock = real_gl - carryover
    loss_deduction = max(net_stock, -3000.0) if net_stock < 0 else net_stock
    remaining_loss = net_stock - loss_deduction if net_stock < 0 else 0

with t_deduct:
    st.subheader("Itemized Deductions")
    st.info(f"The 2026 SALT cap is **${FED_DATA[status]['salt_base_cap']:,}** for your status.")
    
    col_salt, col_mort = st.columns(2)
    with col_salt:
        prop_tax = st.number_input("Property Taxes Paid", 0.0)
        st_inc_tax = tp_st_wh + sp_st_wh # Auto-pulling from W-2 inputs
        st.caption
