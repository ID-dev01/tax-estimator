import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(
    page_title="2026 Tax Estimator",
    page_icon="⚖️",
    layout="wide"
)

# --- 2025 TAX DATA (For filing in 2026) ---
TAX_DATA = {
    "Single": {
        "std_deduct": 15750,
        "brackets": [(11925, 0.10), (48475, 0.12), (103350, 0.22), (197300, 0.24), (250525, 0.32), (626350, 0.35), (float('inf'), 0.37)]
    },
    "Married Filing Jointly": {
        "std_deduct": 31500,
        "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24), (501050, 0.32), (751600, 0.35), (float('inf'), 0.37)]
    },
    "Head of Household": {
        "std_deduct": 23625,
        "brackets": [(17000, 0.10), (64850, 0.12), (103350, 0.22), (197300, 0.24), (250525, 0.32), (626350, 0.35), (float('inf'), 0.37)]
    }
}

def calculate_tax(taxable_income, status):
    brackets = TAX_DATA[status]["brackets"]
    tax = 0
    prev_limit = 0
    for limit, rate in brackets:
        if taxable_income > limit:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
        else:
            tax += (taxable_income - prev_limit) * rate
            break
    return tax

def clear_all_data():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- UI: HEADER ---
st.title("🧮 2026 Federal Tax Refund Estimator")
st.caption("Updated for 2025 Tax Year (Filing in 2026)")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    status = st.selectbox("Filing Status", list(TAX_DATA.keys()))
    dependents = st.number_input("Qualifying Children (Under 17)", 0, 15, step=1)
    st.divider()
    if st.button("🗑️ Clear All Personal Data"):
        clear_all_data()

# --- TABS FOR INPUT ---
tab_w2, tab_inv, tab_crypto, tab_deduct = st.tabs([
    "💼 W-2 Income", "📊 1099 Investments", "🪙 1099-DA Crypto", "🏠 Deductions"
])

# 1. W-2 Tab (DYNAMIC FOR SPOUSES)
with tab_w2:
    st.subheader("W-2 Wage Statements")
    
    if status == "Married Filing Jointly":
        st.info("Input both W-2s separately below. We will total them for you.")
        col_tp, col_sp = st.columns(2)
        
        with col_tp:
            st.markdown("**Taxpayer (Partner 1)**")
            tp_wages = st.number_input("Box 1: Wages", min_value=0.0, step=1000.0, key="tp_wages")
            tp_withheld = st.number_input("Box 2: Fed Withheld", min_value=0.0, step=100.0, key="tp_wh")
            
        with col_sp:
            st.markdown("**Spouse (Partner 2)**")
            sp_wages = st.number_input("Box 1: Wages ", min_value=0.0, step=1000.0, key="sp_wages")
            sp_withheld = st.number_input("Box 2: Fed Withheld ", min_value=0.0, step=100.0, key="sp_wh")
            
        total_w2_wages = tp_wages + sp_wages
        total_w2_withheld = tp_withheld + sp_withheld
    else:
        col1, col2 = st.columns(2)
        with col1:
            total_w2_wages = st.number_input("Box 1: Wages & Tips", min_value=0.0, step=1000.0, key="s_wages")
        with col2:
            total_w2_withheld = st.number_input("Box 2: Federal Withheld", min_value=0.0, step=100.0, key="s_wh")

# 2. Investments Tab (For your JEPI holdings)
with tab_inv:
    st.subheader("Standard Brokerage Income")
    c_int, c_div, c_stk = st.columns(3)
    with c_int:
        st.markdown("**1099-INT**")
        int_inc = st.number_input("Interest Income", min_value=0.0, key="int_inc")
    with c_div:
        st.markdown("**1099-DIV**")
        ord_div = st.number_input("Ordinary Dividends", min_value=0.0, key="ord_div", help="Enter JEPI dividends here.")
    with c_stk:
        st.markdown("**1099-B (Stocks)**")
        b_proc = st.number_input("Sales Proceeds", min_value=0.0, key="b_proc")
        b_basis = st.number_input("Cost Basis", min_value=0.0, key="b_basis")
    stock_gain = max(0.0, b_proc - b_basis)

# 3. Crypto Tab
with tab_crypto:
    st.subheader("Digital Assets (New Form 1099-DA)")
    c_proc = st.number_input("Crypto Proceeds", min_value=0.0, key="c_proc")
    c_basis = st.number_input("Crypto Cost Basis", min_value=0.0, key="c_basis")
    crypto_gain = max(0.0, c_proc - c_basis)

# 4. Deductions Tab
with tab_deduct:
    st.subheader("Itemized Deductions (Schedule A)")
    agi_estimate = total_w2_wages + int_inc + ord_div + stock_gain + crypto_gain
    
    cd1, cd2 = st.columns(2)
    with cd1:
        med_total = st.number_input("Medical/Dental Expenses", min_value=0.0)
        salt_tax = st.number_input("State/Local Taxes (SALT)", min_value=0.0, max_value=40000.0, help="2025 cap is $40k")
    with cd2:
        mortgage_int = st.number_input("Mortgage Interest", min_value=0.0)
        charity = st.number_input("Charitable Gifts", min_value=0.0)
    
    med_deduction = max(0.0, med_total - (agi_estimate * 0.075))
    total_itemized = med_deduction + salt_tax + mortgage_int + charity

# --- FINAL CALCULATIONS ---
standard_deduct = TAX_DATA[status]["std_deduct"]
final_deduction = max(standard_deduct, total_itemized)
taxable_income = max(0.0, agi_estimate - final_deduction)

raw_tax = calculate_tax(taxable_income, status)
child_credit = dependents * 2200
tax_liability = max(0.0, raw_tax - child_credit)
refund_owe = total_w2_withheld - tax_liability

# --- RESULTS DISPLAY ---
st.divider()
st.header("📋 Summary Estimate")
res1, res2, res3 = st.columns(3)
res1.metric("Total Wages", f"${total_w2_wages:,.2f}")
res2.metric("Final Deduction", f"${final_deduction:,.2f}")
res3.metric("Tax Liability", f"${tax_liability:,.2f}")

if refund_owe >= 0:
    st.success(f"### Estimated Refund: **${refund_owe:,.2f}**")
else:
    st.error(f"### Estimated Tax Owed: **${abs(refund_owe):,.2f}**")

with st.expander("📝 Details for CPA"):
    st.write(f"**Status:** {status}")
    st.write(f"**Gross Income:** ${agi_estimate:,.2f}")
    st.write(f"**Total Withheld:** ${total_w2_withheld:,.2f}")
    if total_itemized > standard_deduct:
        st.write("👉 Recommend Itemizing (expenses exceed standard deduction).")
    st.info("Since you own 10 shares of JEPI, ensure your CPA reviews your 1099-DIV for 'Qualified' vs 'Ordinary' dividends.")
