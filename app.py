import streamlit as st

# --- 2026 OBBBA CONFIGURATION ---
st.set_page_config(page_title="2026 Tax Optimizer", layout="wide")

# Official 2026 IRS Data (OBBBA Adjusted)
FED_DATA = {
    "Single": {
        "std_deduct": 16100, 
        "brackets": [(12400, 0.10), (50400, 0.12), (105700, 0.22), (201775, 0.24)],
        "salt_phaseout": 252500,
        "salt_base_cap": 20200,
        "hsa_max": 4400,
        "educator_max": 350
    },
    "Married Filing Jointly": {
        "std_deduct": 32200, 
        "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24)],
        "salt_phaseout": 505000,
        "salt_base_cap": 40400,
        "hsa_max": 8750,
        "educator_max": 700
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

# --- SIDEBAR & MODE SELECTOR ---
with st.sidebar:
    st.header("⚙️ App Settings")
    mode = st.radio("Optimization Mode", ["Manual (Binary)", "Auto-Optimize (Max)"])
    st.divider()
    status = st.selectbox("Filing Status", list(FED_DATA.keys()))
    is_senior = st.checkbox("Age 65 or older?")
    dependents = st.number_input("Children (Under 17)", 0, 10)

# --- INPUT TABS ---
t_inc, t_deduct = st.tabs(["💰 Income & Investments", "📑 Deductions"])

with t_inc:
    c1, c2 = st.columns(2)
    with c1:
        wages = st.number_input("W-2 Fed Wages (Box 1)", 0.0)
        st_wh = st.number_input("State Withholding (Box 17)", 0.0)
        fed_wh = st.number_input("Fed Withholding (Box 2)", 0.0)
    with c2:
        inv_inc = st.number_input("Interest & Dividends", 0.0)
        # Fix for negative capital losses
        stock_gl = st.number_input("Net Realized Gain/Loss", min_value=None, value=0.0)
    
    # Stock Loss Logic ($3k limit)
    loss_adj = max(stock_gl, -3000.0) if stock_gl < 0 else stock_gl
    total_gross = wages + inv_inc + loss_adj

with t_deduct:
    st.subheader("Potential 2026 Deductions")
    
    if mode == "Auto-Optimize (Max)":
        st.success("🚀 **Auto-Mode Active:** Legal maximums will be applied automatically.")
        # Logic: Set values to the legal caps
        hsa = FED_DATA[status]["hsa_max"]
        student_loan = 2500.0
        educator = FED_DATA[status]["educator_max"]
        prop_tax = 15000.0 # Example high property tax
        mort_int = st.number_input("Enter Mortgage Interest", 0.0)
    else:
        st.info("💡 **Manual Mode:** Check the boxes for the deductions you want to take.")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            hsa = FED_DATA[status]["hsa_max"] if st.checkbox("Apply Max HSA") else 0.0
            student_loan = 2500.0 if st.checkbox("Apply Student Loan Interest") else 0.0
            educator = FED_DATA[status]["educator_max"] if st.checkbox("Apply Educator Expense") else 0.0
        with col_b2:
            prop_tax = st.number_input("Property Tax Paid", 0.0)
            mort_int = st.number_input("Mortgage Interest", 0.0)

# --- THE CALCULATION ENGINE ---

# 1. Above-the-Line Deductions (Reducing AGI)
# New OBBBA Senior Deduction ($6,000)
senior_deduct = 6000.0 if is_senior else 0.0
agi = max(0.0, total_gross - hsa - student_loan - educator - senior_deduct)

# 2. SALT Calculation with Phase-out
threshold = FED_DATA[status]['salt_phaseout']
base_cap = FED_DATA[status]['salt_base_cap']
# OBBBA Phase-out: Reduces cap by 30% of income over threshold, floor of $10k
if agi > threshold:
    current_salt_cap = max(10000.0, base_cap - ((agi - threshold) * 0.30))
else:
    current_salt_cap = base_cap

actual_salt = min((prop_tax + st_wh), current_salt_cap)

# 3. Itemize vs Standard
itemized_total = actual_salt + mort_int
final_deduction = max(itemized_total, FED_DATA[status]["std_deduct"])

# 4. Final Tax Math
taxable_inc = max(0.0, agi - final_deduction)
fed_tax_due = calculate_federal_tax(taxable_inc, status) - (dependents * 2000)
refund_owed = fed_wh - fed_tax_due

# --- DISPLAY RESULTS ---
st.divider()
st.header("📊 2026 Tax Summary")
m1, m2, m3 = st.columns(3)

with m1:
    st.metric("Adjusted Gross Income", f"${agi:,.0f}")
    st.caption(f"Method: {'Itemized' if itemized_total > FED_DATA[status]['std_deduct'] else 'Standard'}")

with m2:
    if refund_owed >= 0:
        st.success(f"Federal Refund: ${refund_owed:,.0f}")
    else:
        st.error(f"Federal Owed: ${abs(refund_owed):,.0f}")

with m3:
    st.metric("Active SALT Cap", f"${current_salt_cap:,.0f}")
    st.caption("Includes OBBBA phase-out if applicable.")
