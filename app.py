import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2026 OFFICIAL DATA (MFJ) ---
FED_STD = 32200
SALT_CAP_2026 = 40400 
NY_STD = 16050
CTC_2026 = 2200  # Child Tax Credit per qualifying child

# Federal Brackets 2026 (OBBB Adjusted)
FED_BRACKETS = [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]

# NJ Brackets (Resident)
NJ_BRACKETS = [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (float('inf'), 0.0897)]

# NY Brackets (Non-Resident)
NY_BRACKETS = [(17150, 0.039), (23600, 0.044), (27900, 0.0515), (161550, 0.054), (323200, 0.059), (float('inf'), 0.0685)]

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
    return tax

st.set_page_config(layout="wide", page_title="2026 Global Tax Auditor")
st.title("⚖️ 2026 Federal & Tri-State Strategy Auditor")

# --- INPUTS ---
col_a, col_b = st.columns(2)
with col_a:
    st.header("👤 Partner A (NJ Resident)")
    a_box1 = st.number_input("W-2 Box 1 (Fed Wages)", value=145000)
    a_box16 = st.number_input("W-2 Box 16 (NJ Wages)", value=152000)
    a_box2 = st.number_input("W-2 Box 2 (Fed Withheld)", value=19000)
    a_box17 = st.number_input("W-2 Box 17 (NJ Withheld)", value=8500)

with col_b:
    st.header("👤 Partner B (NY Worker)")
    b_box1 = st.number_input("W-2 Box 1 (Fed Wages) ", value=206500)
    b_box16 = st.number_input("W-2 Box 16 (NY Wages)", value=212000)
    b_box2 = st.number_input("W-2 Box 2 (Fed Withheld) ", value=35000)
    b_box17 = st.number_input("W-2 Box 17 (NY Withheld)", value=18500)

st.divider()
st.header("🏠 Property, Portfolio & Family")
c1, c2, c3 = st.columns(3)
with c1:
    prop_tax = st.number_input("Annual Property Taxes", value=15000)
    m_int = st.number_input("Mortgage Interest (1098)", value=22000)
with c2:
    # UPDATED: Dynamic Child Input
    num_kids = st.slider("Number of Qualifying Children (under 17)", 0, 10, 0)
    charity = st.number_input("Charitable Gifts", value=5000)
with c3:
    int_income = st.number_input("Interest (1099-INT)", value=5000)
    brokerage = st.number_input("Brokerage Gains / (Losses)", value=2000)

# --- 1. FEDERAL RETURN ---
fed_agi = a_box1 + b_box1 + int_income + brokerage
salt_amt = min((a_box17 + b_box17 + prop_tax), SALT_CAP_2026)
fed_itemized = salt_amt + m_int + max(0, charity - (fed_agi * 0.005)) # 0.5% Floor
fed_deduct = max(fed_itemized, FED_STD)
fed_taxable = max(0, fed_agi - fed_deduct)
# Apply Brackets + Child Tax Credit
fed_liability = max(0, calc_tax(fed_taxable, FED_BRACKETS) - (num_kids * CTC_2026))
fed_refund = (a_box2 + b_box2) - fed_liability

# --- 2. NEW YORK RETURN (Non-Resident) ---
ny_agi = a_box16 + b_box16 + int_income + brokerage
ny_taxable = max(0, ny_agi - NY_STD)
ny_base_tax = calc_tax(ny_taxable, NY_BRACKETS)
ny_ratio = b_box16 / ny_agi # Proration for non-resident
ny_final_tax = ny_base_tax * ny_ratio
ny_refund = b_box17 - ny_final_tax

# --- 3. NEW JERSEY RETURN (Resident) ---
nj_agi = a_box16 + b_box16 + int_income + brokerage
# NJ allows up to $15k prop tax deduction
nj_taxable = max(0, nj_agi - min(prop_tax, 15000) - 3000)
nj_base_tax = calc_tax(nj_taxable, NJ_BRACKETS)
# Credit for taxes paid to NY (Resident Credit)
nj_credit = min(nj_base_tax * (b_box16 / nj_agi), ny_final_tax)
nj_final_tax = max(0, nj_base_tax - nj_credit)
nj_refund = a_box17 - nj_final_tax

# --- VISUALS ---
st.divider()
v1, v2 = st.columns([1, 1.5])

with v1:
    st.subheader("📍 SALT Dial (2026 Cap)")
    fig_dial = go.Figure(go.Indicator(
        mode = "gauge+number", value = salt_amt,
        gauge = {'axis': {'range': [0, 50000]}, 'bar': {'color': "#2ecc71" if salt_amt < SALT_CAP_2026 else "#e74c3c"},
                 'threshold': {'line': {'color': "red", 'width': 4}, 'value': SALT_CAP_2026}}
    ))
    st.plotly_chart(fig_dial, use_container_width=True)

with v2:
    st.subheader("🏁 Final Refunds / (Owed)")
    summary_df = pd.DataFrame({
        "Agency": ["Federal Return", "New York State", "New Jersey State"],
        "Liability": [fed_liability, ny_final_tax, nj_final_tax],
        "Withheld": [a_box2+b_box2, b_box17, a_box17],
        "Refund/(Owe)": [fed_refund, ny_refund, nj_refund]
    })
    st.table(summary_df.style.format("${:,.2f}"))

# Total Check
total_cash = fed_refund + ny_refund + nj_refund
st.success(f"### **Total Estimated Net Refund: ${total_cash:,.2f}**")
