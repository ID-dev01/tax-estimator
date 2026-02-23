import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2026 MASTER DATA ---
LAW_2026 = {
    "Fed": {"std": 32200, "brackets": [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]},
    "SALT_CAP": 40400, # Updated for OBBB 2026
    "CTC": 2200,       # Child Tax Credit 2026
    "NJ_PROP_DEDUCT_MAX": 15000
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
    return tax

st.set_page_config(layout="wide", page_title="2026 Global Auditor")
st.title("⚖️ 2026 Granular Tax & NJ Relief Auditor")

# --- SIDEBAR: NJ RELIEF (ANCHOR / STAY NJ) ---
st.sidebar.header("🛡️ NJ Property Relief (2026)")
is_senior = st.sidebar.checkbox("Is a Homeowner 65+?", value=False)
nj_income = st.sidebar.number_input("NJ Gross Income (for eligibility)", value=388000)

# ANCHOR 2026 Logic
anchor_rebate = 0
if nj_income <= 150000: anchor_rebate = 1500
elif nj_income <= 250000: anchor_rebate = 1000

# STAY NJ 2026 Logic (Seniors < $500k)
stay_nj_rebate = 0
prop_tax_input = st.sidebar.number_input("Annual NJ Property Tax Bill", value=15000)
if is_senior and nj_income < 500000:
    stay_nj_rebate = min(6500, (prop_tax_input * 0.50) - anchor_rebate)

st.sidebar.success(f"Est. NJ Rebates: ${anchor_rebate + stay_nj_rebate:,.0f}")

# --- SECTION 1: GRANULAR W-2 INPUTS ---
st.header("📄 W-2 Wages & Pre-Tax (Box by Box)")
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Partner A (NJ Resident)")
    a_box1 = st.number_input("Box 1 (Taxable Wages)", value=145000)
    a_box12 = st.number_input("Box 12 (401k/403b Paid)", value=18668)
    a_box10 = st.number_input("Box 10 (Dependent Care FSA)", value=5000)
    a_box2 = st.number_input("Box 2 (Federal Tax Withheld)", value=19000)
    a_box17 = st.number_input("Box 17 (NJ State Tax Paid)", value=8000)

with col_b:
    st.subheader("Partner B (NY Worker)")
    b_box1 = st.number_input("Box 1 (Taxable Wages)", value=206500)
    b_box12 = st.number_input("Box 12 (401k/403b Paid)", value=24500)
    b_box2 = st.number_input("Box 2 (Federal Tax Withheld)", value=35000)
    b_box17 = st.number_input("Box 17 (NY State Tax Paid)", value=18000)

# --- SECTION 2: ITEMIZATION & PORTFOLIO ---
st.divider()
st.header("🏠 Deductions, Charity & Portfolio")
col_1098, col_1099, col_credits = st.columns(3)

with col_1098:
    st.subheader("Itemized (Schedule A)")
    m_int = st.number_input("1098 Box 1 (Mortgage Interest)", value=22000)
    charity = st.number_input("Charity / Gifts", value=5000)
    med_oop = st.number_input("Medical Out-of-Pocket", value=0)

with col_1099:
    st.subheader("Investment Income")
    int_1099 = st.number_input("1099-INT/DIV (Interest)", value=8000)
    gain_1099 = st.number_input("1099-B (ST Cap Gains)", value=5000)

with col_credits:
    st.subheader("Family & Credits")
    kids = st.number_input("Qualifying Children", value=2)

# --- THE CALCULATIONS ---
total_agi = a_box1 + b_box1 + int_1099 + gain_1099

# Medical Deduction (7.5% Floor)
med_deduct = max(0, med_oop - (total_agi * 0.075))

# SALT Deduction (Property Tax + State Income Tax)
total_salt = a_box17 + b_box17 + prop_tax_input
salt_deduct = min(total_salt, LAW_2026["SALT_CAP"])

# Itemized vs Standard
total_itemized = m_int + charity + salt_deduct + med_deduct
final_deduction = max(total_itemized, LAW_2026["Fed"]["std"])

# Final Federal Bill
taxable_inc = max(0, total_agi - final_deduction)
fed_liab = calc_tax(taxable_inc, LAW_2026["Fed"]["brackets"])
total_credits = kids * LAW_2026["CTC"]
final_fed_tax = max(0, fed_liab - total_credits)

# Refund Calculation
total_wh = a_box2 + b_box2
balance = total_wh - final_fed_tax

# --- VISUALS ---
st.divider()
st.header("📊 Final Strategy Visuals")
v1, v2 = st.columns([1, 1.5])

with v1:
    st.metric("Adjusted Gross Income", f"${total_agi:,.0f}")
    st.metric("Total Federal Deduction", f"${final_deduction:,.0f}", 
              delta="Itemizing is better" if final_deduction > 32200 else "Standard is better")
    st.metric("Projected Refund/(Owe)", f"${balance:,.0f}", 
              delta="Target: $0" if balance > 0 else "Increase withholding", delta_color="normal")

with v2:
    # Waterfall Chart of Income Reduction
    fig = go.Figure(go.Waterfall(
        name = "Tax Shield", orientation = "v",
        measure = ["relative", "relative", "relative", "relative", "total"],
        x = ["Gross Wages", "401k/FSA Shield", "Portfolio Income", "Itemized Deductions", "Taxable Income"],
        textposition = "outside",
        text = [f"+{a_box1+b_box1}", f"-{a_box12+b_box12+a_box10}", f"+{int_1099+gain_1099}", f"-{final_deduction}", "Final"],
        y = [a_box1+b_box1, -(a_box12+b_box12+a_box10), (int_1099+gain_1099), -final_deduction, 0],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    ))
    fig.update_layout(title = "Income Shielding Waterfall", showlegend = False, height=450)
    st.plotly_chart(fig, use_container_width=True)

# --- AUDIT TABLE ---
st.table(pd.DataFrame({
    "W-2 / 1098 / 1099 Source": ["Taxable Wages", "Pre-Tax Shield", "Investment Income", "SALT Deduction", "Mortgage/Charity/Med", "Total Credits"],
    "Amount": [f"${a_box1 + b_box1:,.0f}", f"-${a_box12 + b_box12 + a_box10:,.0f}", f"+${int_1099 + gain_1099:,.0f}", f"-${salt_deduct:,.0f}", f"-${m_int + charity + med_deduct:,.0f}", f"-${total_credits:,.0f}"]
}))
