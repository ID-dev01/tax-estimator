import streamlit as st
import pandas as pd

# --- 2026 CALCULATOR ENGINE ---
def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
    return tax

# 2026 MFJ Data
FED_BRACKETS = [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]
STD_DEDUCTION = 32200

st.set_page_config(layout="wide", page_title="2026 Full Audit")
st.title("🏛️ 2026 Full Household Tax & Wealth Auditor")

# --- INPUT SECTION ---
col_w2, col_1099, col_itemized = st.columns(3)

with col_w2:
    st.header("📄 W-2 & Pre-Tax")
    gross = st.number_input("Total Household Gross (W-2)", value=388000)
    k_shield = st.number_input("401k/FSA Shield (Slider Target)", value=49000)
    # Box 1 Logic
    box1_wages = gross - k_shield

with col_1099:
    st.header("📈 1099 & Gains")
    interest = st.number_input("Interest/Dividends (1099-INT)", value=8000)
    st_gains = st.number_input("Short-Term Gains (1099-B)", value=5000)
    lt_gains = st.number_input("Long-Term Gains (1099-B)", value=0)
    # AGI Calculation
    agi = box1_wages + interest + st_gains

with col_itemized:
    st.header("📝 Deductions (Sch A)")
    mortgage_int = st.number_input("Mortgage Interest (1098)", value=22000)
    charity = st.number_input("Charity/Gifts", value=5000)
    medical_raw = st.number_input("Unreimbursed Medical", value=0)
    
    # Medical 7.5% Floor Logic
    med_deductible = max(0, medical_raw - (agi * 0.075))
    # SALT Cap (Increased for 2026 to $40,400 for MFJ under $500k)
    salt_deduction = 40400 if agi < 500000 else 10000
    
    total_itemized = mortgage_int + charity + med_deductible + salt_deduction

# --- THE AUDIT LOGIC ---
use_itemized = total_itemized > STD_DEDUCTION
final_deduction = total_itemized if use_itemized else STD_DEDUCTION
taxable_income = max(0, agi - final_deduction)

# Federal Tax (Ordinary)
fed_tax = calc_tax(taxable_income, FED_BRACKETS)
# Add LT Gains Tax (Simplified 15% for this bracket)
lt_tax = lt_gains * 0.15
total_bill = fed_tax + lt_tax

# --- RESULTS DISPLAY ---
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Adjusted Gross Income (AGI)", f"${agi:,.0f}")
c2.metric("Best Deduction Strategy", "Itemized" if use_itemized else "Standard", f"${final_deduction:,.0f}")
c3.metric("Est. Federal Bill", f"${total_bill:,.0f}")

st.info(f"""
💡 **Advisor Strategy:** * **1098 (Mortgage):** Because your mortgage interest + SALT (${salt_deduction:,.0f}) is already over the standard deduction, **every dollar you give to charity is now 100% tax-deductible.** * **1099 (Gains):** Your short-term gains are being taxed at ~24-32%. If you held those assets for 1 year and 1 day, that tax would drop to 15%.
* **Medical:** Since your AGI is high, your medical expenses must exceed **${agi * 0.075:,.0f}** before they save you a single penny in taxes.
""")

# --- AUDIT TABLE ---
st.table(pd.DataFrame({
    "Step": ["Gross Income", "Less Pre-Tax Shield", "Plus 1099 Income", "Less Deductions", "Taxable Income"],
    "Amount": [f"${gross:,.0f}", f"-${k_shield:,.0f}", f"+${interest + st_gains:,.0f}", f"-${final_deduction:,.0f}", f"**${taxable_income:,.0f}**"]
}))
