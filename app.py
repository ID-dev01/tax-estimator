import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="2026 Multi-State Tax Estimator", layout="wide")

# --- 2025/2026 TAX DATA ---
# Brackets are simplified for the app logic
FED_DATA = {"Single": 15750, "Married Filing Jointly": 31500}
STATE_RATES = {"NJ": 0.055, "NY": 0.062, "CT": 0.055, "CA": 0.093}

def clear_all_data():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Filing Profile")
    status = st.selectbox("Filing Status", ["Single", "Married Filing Jointly"])
    residence = st.selectbox("State of Residence", ["NJ", "NY", "CT"])
    dependents = st.number_input("Children", 0, 10)
    st.divider()
    if st.button("🗑️ Clear All Data"): clear_all_data()

# --- INPUT TABS ---
tab_w2, tab_inv, tab_deduct = st.tabs(["💼 W-2 Wages", "📊 Investments", "🏠 Deductions"])

with tab_w2:
    st.subheader("W-2 Income per Spouse")
    if status == "Married Filing Jointly":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Taxpayer (Partner 1)**")
            tp_work_st = st.selectbox("Work State", ["NJ", "NY", "CA"], key="tp_st")
            tp_wages = st.number_input("Box 1 Wages", 0.0, key="tp_w")
            tp_fed_wh = st.number_input("Fed Withheld", 0.0, key="tp_fwh")
            tp_st_wh = st.number_input(f"{tp_work_st} State Withheld", 0.0, key="tp_swh")
        with col2:
            st.markdown("**Spouse (Partner 2)**")
            sp_work_st = st.selectbox("Work State ", ["NJ", "NY", "CA"], key="sp_st")
            sp_wages = st.number_input("Box 1 Wages ", 0.0, key="sp_w")
            sp_fed_wh = st.number_input("Fed Withheld ", 0.0, key="sp_fwh")
            sp_st_wh = st.number_input(f"{sp_work_st} State Withheld ", 0.0, key="sp_swh")
    else:
        # Single Filer
        tp_work_st = st.selectbox("Work State", ["NJ", "NY", "CA"])
        tp_wages = st.number_input("Box 1 Wages", 0.0)
        tp_fed_wh = st.number_input("Fed Withheld", 0.0)
        tp_st_wh = st.number_input(f"{tp_work_st} Withheld", 0.0)
        sp_wages = 0.0; sp_fed_wh = 0.0; sp_st_wh = 0.0; sp_work_st = residence

with tab_inv:
    st.subheader("Dividends & Interest")
    ord_div = st.number_input("Ordinary Dividends (inc. JEPI)", 0.0)
    int_inc = st.number_input("Interest Income", 0.0)

# --- CALCULATIONS ---
total_income = tp_wages + sp_wages + ord_div + int_inc
fed_deduct = FED_DATA[status]
fed_taxable = max(0.0, total_income - fed_deduct)

# 1. Federal Estimate (Simple 15% effective for demo)
fed_tax_bill = fed_taxable * 0.15 - (dependents * 2200)

# 2. State Logic: Credit for Taxes Paid to Other Jurisdictions
# Calculate what was earned in a foreign state
foreign_income = 0
foreign_tax_paid = 0

if tp_work_st != residence:
    foreign_income += tp_wages
    foreign_tax_paid += (tp_wages * STATE_RATES[tp_work_st])
if sp_work_st != residence:
    foreign_income += sp_wages
    foreign_tax_paid += (sp_wages * STATE_RATES[sp_work_st])

# Home State Liability (Before Credit)
home_rate = STATE_RATES[residence]
home_tax_before_credit = total_income * home_rate

# The NJ/CT/NY Credit Rule: 
# Credit = (Foreign Income / Total Income) * Home Tax Liability
if total_income > 0:
    max_allowable_credit = (foreign_income / total_income) * home_tax_before_credit
    actual_credit = min(foreign_tax_paid, max_allowable_credit)
else:
    actual_credit = 0

final_home_tax = max(0.0, home_tax_before_credit - actual_credit)
total_st_withheld = tp_st_wh + sp_st_wh

# --- RESULTS ---
st.divider()
st.header("📋 Summary for 2026")
c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Total Income", f"${total_income:,.0f}")
    fed_ref = (tp_fed_wh + sp_fed_wh) - fed_tax_bill
    if fed_ref >= 0: st.success(f"Fed Refund: ${fed_ref:,.0f}")
    else: st.error(f"Fed Owed: ${abs(fed_ref):,.0f}")

with c2:
    st.metric(f"{residence} Tax (Home)", f"${final_home_tax:,.0f}")
    st_ref = total_st_withheld - foreign_tax_paid - final_home_tax
    if st_ref >= 0: st.success(f"State Refund: ${st_ref:,.0f}")
    else: st.error(f"State Owed: ${abs(st_ref):,.0f}")

with c3:
    st.metric("Credit for Other States", f"${actual_credit:,.0f}")
    st.caption(f"Based on ${foreign_income:,.0f} earned outside {residence}")

if residence == "NJ" and (tp_work_st == "NY" or sp_work_st == "NY"):
    st.info("💡 **NJ-NY Note:** You will file NY Form IT-203 (Non-resident) and NJ-1040 with Schedule NJ-COJ for your credit.")
