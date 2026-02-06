import streamlit as st

# --- CONFIGURATION & SESSION STATE ---
st.set_page_config(
    page_title="2026 Tax Refund Estimator",
    page_icon="💰",
    layout="wide"
)

# Initialize session state for all inputs if not present
if 'wages' not in st.session_state:
    st.session_state.update({
        'wages': 0.0, 'w2_withheld': 0.0, 'int_income': 0.0, 
        'ord_div': 0.0, 'qual_div': 0.0, 'b_proceeds': 0.0, 
        'b_basis': 0.0, 'c_proceeds': 0.0, 'c_basis': 0.0
    })

def clear_all_data():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 2025 TAX DATA (For filing in 2026) ---
# Updated with 2025 Standard Deductions
TAX_DATA = {
    "Single": {"std_deduct": 15750, "brackets": [(11925, 0.10), (48475, 0.12), (103350, 0.22), (197300, 0.24)]},
    "Married Filing Jointly": {"std_deduct": 31500, "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24)]},
    "Head of Household": {"std_deduct": 23650, "brackets": [(17000, 0.10), (64850, 0.12), (103350, 0.22), (197300, 0.24)]}
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

# --- UI: HEADER & DISCLAIMER ---
st.title("🧮 2026 Federal Tax Estimator")
st.caption("Tax Year: 2025 | Filing Season: Jan-April 2026")

with st.expander("⚠️ LEGAL DISCLAIMER & PRIVACY NOTE", expanded=True):
    st.warning("""
    **Not a Tax Filing Service:** This app provides **estimates only**. It is not a substitute for professional 
    advice from a CPA or licensed tax preparer. Tax laws (especially for Crypto/1099-DA) are subject to change.
    
    **Privacy:** We do not store your data. All information stays in your browser's temporary memory. 
    Closing the tab or clicking 'Clear All Data' wipes everything.
    """)

# --- SIDEBAR Controls ---
with st.sidebar:
    st.header("⚙️ Settings")
    status = st.selectbox("Filing Status", list(TAX_DATA.keys()))
    dependents = st.number_input("Children (Under 17)", 0, 10, step=1)
    st.divider()
    if st.button("🗑️ Clear All Personal Data"):
        clear_all_data()
    st.divider()
    st.info("Tracking JEPI? Use the 'Dividends' tab to enter your 1099-DIV totals.")

# --- MAIN INPUT TABS ---
tab1, tab2, tab3 = st.tabs(["💼 Employment (W-2)", "📈 Investments (1099s)", "🪙 Crypto (1099-DA)"])

with tab1:
    st.subheader("Wage Income")
    col1, col2 = st.columns(2)
    with col1:
        wages = st.number_input("W-2 Box 1: Total Wages", min_value=0.0, step=500.0, key="wages")
        st.caption("💡 Found on the paper from your employer.")
    with col2:
        w2_withheld = st.number_input("W-2 Box 2: Fed Tax Withheld", min_value=0.0, step=100.0, key="w2_withheld")

with tab2:
    st.subheader("Standard Investment Forms")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**1099-INT (Interest)**")
        int_inc = st.number_input("Box 1: Interest Income", min_value=0.0, key="int_income")
        
        st.markdown("**1099-DIV (Dividends)**")
        ord_div = st.number_input("Box 1a: Total Ordinary Dividends", min_value=0.0, key="ord_div")
        st.caption("Include JEPI dividends here.")
    
    with col_b:
        st.markdown("**1099-B (Stock Sales)**")
        b_proc = st.number_input("Box 1d: Sales Proceeds", min_value=0.0, key="b_proceeds")
        b_basis = st.number_input("Box 1e: Cost Basis", min_value=0.0, key="b_basis")
        stock_gain = max(0.0, b_proc - b_basis)
        st.write(f"Estimated Stock Gain: **${stock_gain:,.2f}**")

with tab3:
    st.subheader("Digital Assets (New Form 1099-DA)")
    st.info("New for 2026 filing: Crypto exchanges now issue 1099-DA.")
    c_proc = st.number_input("Gross Crypto Proceeds", min_value=0.0, key="c_proceeds")
    c_basis = st.number_input("Calculated Crypto Basis", min_value=0.0, key="c_basis")
    crypto_gain = max(0.0, c_proc - c_basis)

# --- CALCULATION LOGIC ---
total_income = wages + int_inc + ord_div + stock_gain + crypto_gain
std_deduction = TAX_DATA[status]["std_deduct"]
taxable_income = max(0.0, total_income - std_deduction)

# Calculation
est_tax_bill = calculate_tax(taxable_income, status)
child_credit = dependents * 2200  # 2025 Rate
final_tax_owed = max(0.0, est_tax_bill - child_credit)
refund_amount = w2_withheld - final_tax_owed

# --- RESULTS DISPLAY ---
st.divider()
st.header("📊 Your Estimation Summary")

c1, c2, c3 = st.columns(3)
c1.metric("Total Income", f"${total_income:,.2f}")
c2.metric("Taxable Income", f"${taxable_income:,.2f}")
c3.metric("Standard Deduction", f"${std_deduction:,.2f}")

if refund_amount >= 0:
    st.success(f"### Estimated Refund: **${refund_amount:,.2f}**")
    st.balloons()
else:
    st.error(f"### Estimated Additional Tax Owed: **${abs(refund_amount):,.2f}**")

st.markdown("---")
st.subheader("📝 Next Steps for your CPA")
st.write(f"""
1. **Download your 1099s:** Especially your 1099-DIV for your **JEPI** holdings.
2. **Bring this summary:** Tell your CPA your estimated taxable income is **${taxable_income:,.2f}**.
3. **Review Crypto:** Ensure your **1099-DA** basis matches your personal records.
""")
