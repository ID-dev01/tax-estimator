import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="2026 Tax Estimator", page_icon="⚖️", layout="wide")

# --- TAX DATA (2025/2026 Estimates) ---
FEDERAL_DATA = {
    "Single": {"std_deduct": 15750, "brackets": [(11925, 0.10), (48475, 0.12), (103350, 0.22), (197300, 0.24)]},
    "Married Filing Jointly": {"std_deduct": 31500, "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24)]}
}

# Simplified State Brackets (Aggregated for v1)
STATE_RATES = {
    "NJ": 0.055, # Avg effective for mid-earners
    "NY": 0.062, # Avg effective for mid-earners 
    "CT": 0.055,
    "CA": 0.093, # Higher average for CA
}

def calculate_tax(income, brackets):
    tax = 0
    prev_limit = 0
    for limit, rate in brackets:
        if income > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (income - prev_limit) * rate
            break
    return tax

# --- SIDEBAR: RESIDENCY & STATUS ---
with st.sidebar:
    st.header("📍 Location & Status")
    status = st.selectbox("Filing Status", list(FEDERAL_DATA.keys()))
    residence = st.selectbox("State of Residence", ["NJ", "NY", "CT"])
    work_state = st.selectbox("State of Employment", ["NJ", "NY", "CA"])
    dependents = st.number_input("Children (Under 17)", 0, 10)
    if st.button("🗑️ Clear All Data"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- INPUT TABS ---
t_w2, t_inv, t_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments", "🏠 Deductions"])

with t_w2:
    st.info(f"Scenario: Resident of **{residence}** working in **{work_state}**")
    if status == "Married Filing Jointly":
        c1, c2 = st.columns(2)
        with c1:
            tp_w = st.number_input("Taxpayer Box 1 Wages", 0.0, key="tp_w")
            tp_fed_wh = st.number_input("Taxpayer Fed Withheld", 0.0, key="tp_wh")
            tp_st_wh = st.number_input(f"Taxpayer {work_state} Withheld", 0.0, key="tp_s_wh")
        with c2:
            sp_w = st.number_input("Spouse Box 1 Wages", 0.0, key="sp_w")
            sp_fed_wh = st.number_input("Spouse Fed Withheld", 0.0, key="sp_wh")
            sp_st_wh = st.number_input(f"Spouse {work_state} Withheld", 0.0, key="sp_s_wh")
        total_wages = tp_w + sp_w
        total_fed_wh = tp_fed_wh + sp_fed_wh
        total_st_wh = tp_st_wh + sp_st_wh
    else:
        total_wages = st.number_input("W-2 Box 1 Wages", 0.0, key="s_w")
        total_fed_wh = st.number_input("W-2 Box 2 Fed Withheld", 0.0, key="s_wh")
        total_st_wh = st.number_input(f"W-2 Box 17 {work_state} Withheld", 0.0, key="s_s_wh")

with t_inv:
    st.subheader("Dividends & Interest")
    ord_div = st.number_input("Total Ordinary Dividends (inc. JEPI)", 0.0)
    int_inc = st.number_input("Interest Income", 0.0)
    total_income = total_wages + ord_div + int_inc

with t_deduct:
    st.subheader("Itemized vs Standard")
    st.caption("2025 SALT Cap is now $40,000!")
    salt = st.number_input("State/Local Taxes (Property + State Tax)", 0.0, 40000.0)
    mortgage = st.number_input("Mortgage Interest", 0.0)
    charity = st.number_input("Charity", 0.0)
    
    itemized = salt + mortgage + charity
    final_deduct = max(itemized, FEDERAL_DATA[status]["std_deduct"])

# --- CALCULATIONS ---
# 1. Federal
fed_taxable = max(0.0, total_income - final_deduct)
fed_tax_bill = calculate_tax(fed_taxable, FEDERAL_DATA[status]["brackets"]) - (dependents * 2200)

# 2. State Calculation Logic
st_tax_rate = STATE_RATES.get(work_state, 0.05)
work_st_bill = total_wages * st_tax_rate

# Home State Credit Logic
if residence != work_state:
    home_st_rate = STATE_RATES.get(residence, 0.05)
    home_st_liability = total_income * home_st_rate
    # Credit for taxes paid to work state (cannot exceed home state tax)
    credit = min(home_st_liability, work_st_bill)
    final_home_st_tax = max(0.0, home_st_liability - credit)
else:
    final_home_st_tax = total_income * STATE_RATES.get(residence, 0.05)

# --- RESULTS ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.subheader("Federal Result")
    fed_ref = total_fed_wh - fed_tax_bill
    if fed_ref >= 0: st.success(f"Federal Refund: **${fed_ref:,.2f}**")
    else: st.error(f"Federal Owed: **${abs(fed_ref):,.2f}**")

with c2:
    st.subheader(f"{residence} State Result")
    # Simplified state refund: What you paid to the work state vs what you owe home
    state_ref = total_st_wh - work_st_bill - final_home_st_tax
    if state_ref >= 0: st.success(f"State Refund: **${state_ref:,.2f}**")
    else: st.error(f"State Owed: **${abs(state_ref):,.2f}**")

st.info(f"💡 **Note:** Because you work in {work_state}, you'll likely file a **Non-Resident** return there and a **Resident** return in {residence}.")
