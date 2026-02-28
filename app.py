import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2026 OFFICIAL DATA (MFJ) ---
FED_STD = 32200
SALT_CAP_2026 = 40400 
NY_STD = 16050
CTC_2026 = 2200

FED_BRACKETS = [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]
NJ_BRACKETS = [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (float('inf'), 0.0897)]
NY_BRACKETS = [(17150, 0.039), (23600, 0.044), (27900, 0.0515), (161550, 0.054), (323200, 0.059), (float('inf'), 0.0685)]

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
    return float(tax)

st.set_page_config(layout="wide", page_title="2026 Global Tax Auditor")
st.title("⚖️ 2026 Federal & Tri-State Strategy Auditor")

# --- ROW 1: W-2 INPUTS ---
col_a, col_b = st.columns(2)
with col_a:
    st.header("👤 Partner A (NJ Resident)")
    a_box1 = st.number_input("Box 1 (Fed Wages)", value=145000.0)
    a_box12 = st.number_input("Box 12 (401k/Shield)", value=18668.0)
    a_box16 = st.number_input("Box 16 (NJ Wages)", value=152000.0)
    a_box2 = st.number_input("Box 2 (Fed Withheld)", value=19000.0)
    a_box17 = st.number_input("Box 17 (NJ Withheld)", value=8500.0)

with col_b:
    st.header("👤 Partner B (NY Worker)")
    b_box1 = st.number_input("Box 1 (Fed Wages) ", value=206500.0)
    b_box12 = st.number_input("Box 12 (401k/Shield) ", value=24500.0)
    b_box16 = st.number_input("Box 16 (NY Wages)", value=212000.0)
    b_box2 = st.number_input("Box 2 (Fed Withheld) ", value=35000.0)
    b_box17 = st.number_input("Box 17 (NY Withheld)", value=18500.0)

# --- ROW 2: HOMEOWNER & FAMILY ---
st.divider()
st.header("🏠 Property, Portfolio & Family")
c1, c2, c3 = st.columns(3)
with c1:
    prop_tax = st.number_input("Annual Property Taxes", value=15000.0)
    m_int = st.number_input("Mortgage Interest (1098)", value=22000.0)
with c2:
    num_kids = st.slider("Number of Qualifying Children", 0, 10, 0)
    charity = st.number_input("Charitable Gifts", value=5000.0)
with c3:
    int_income = st.number_input("Interest (1099-INT)", value=5000.0)
    brokerage = st.number_input("Brokerage Gains / (Losses)", value=2000.0)

# --- CALCULATION ENGINE ---
fed_agi = float(a_box1 + b_box1 + int_income + brokerage)
salt_amt = float(min((a_box17 + b_box17 + prop_tax), SALT_CAP_2026))
fed_itemized = float(salt_amt + m_int + max(0, charity - (fed_agi * 0.005)))
fed_deduct = float(max(fed_itemized, FED_STD))
fed_taxable = float(max(0, fed_agi - fed_deduct))
fed_liability = float(max(0, calc_tax(fed_taxable, FED_BRACKETS) - (num_kids * CTC_2026)))
fed_refund = float((a_box2 + b_box2) - fed_liability)

# NY Non-Resident
ny_agi = float(a_box16 + b_box16 + int_income + brokerage)
ny_taxable = float(max(0, ny_agi - NY_STD))
ny_final_tax = float(calc_tax(ny_taxable, NY_BRACKETS) * (b_box16 / ny_agi if ny_agi > 0 else 0))
ny_refund = float(b_box17 - ny_final_tax)

# NJ Resident
nj_agi = float(a_box16 + b_box16 + int_income + brokerage)
nj_taxable = float(max(0, nj_agi - min(prop_tax, 15000) - 3000))
nj_base_tax = float(calc_tax(nj_taxable, NJ_BRACKETS))
nj_credit = float(min(nj_base_tax * (b_box16 / nj_agi if nj_agi > 0 else 0), ny_final_tax))
nj_final_tax = float(max(0, nj_base_tax - nj_credit))
nj_refund = float(a_box17 - nj_final_tax)

# --- VISUALS ---
st.divider()
v1, v2 = st.columns([1, 1.5])

with v1:
    st.subheader("📍 SALT Dial (2026 Cap)")
    fig_dial = go.Figure(go.Indicator(
        mode = "gauge+number", value = salt_amt,
        gauge = {'axis': {'range': [0, 50000]}, 'bar': {'color': "green"},
                 'threshold': {'line': {'color': "red", 'width': 4}, 'value': SALT_CAP_2026}}
    ))
    st.plotly_chart(fig_dial, use_container_width=True)

with v2:
    st.subheader("🏁 Final Strategy Results")
    summary_df = pd.DataFrame({
        "Agency": ["Federal", "New York", "New Jersey"],
        "Liability": [fed_liability, ny_final_tax, nj_final_tax],
        "Withheld": [(a_box2 + b_box2), b_box17, a_box17],
        "Refund / (Owe)": [fed_refund, ny_refund, nj_refund]
    })
    
    # FIX: Explicitly cast to float and format only numeric columns to avoid the error in your image
    st.table(summary_df.style.format({
        "Liability": "${:,.2f}",
        "Withheld": "${:,.2f}",
        "Refund / (Owe)": "${:,.2f}"
    }))

st.success(f"### **Total Combined Net Refund: ${fed_refund + ny_refund + nj_refund:,.2f}**")
