import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2026 DATA DEFAULTS ---
FED_STD = 32200
SALT_CAP_2026 = 40400
FED_BRACKETS = [(24800, 0.10), (100800, 0.12), (211400, 0.22), (403550, 0.24), (512450, 0.32), (768700, 0.35), (float('inf'), 0.37)]

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
    return tax

st.set_page_config(layout="wide", page_title="2026 Homeowner Auditor")
st.title("🛡️ 2026 Homeowner & W-2 Strategy Auditor")

# --- ROW 1: THE W-2 INPUTS (SPLIT) ---
st.header("📄 W-2 Income (Partner Split)")
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Partner A")
    a_box1 = st.number_input("W-2 Box 1 (Taxable Wages)", value=145000)
    a_box17 = st.number_input("W-2 Box 17 (State Tax Paid)", value=8000)
    a_box2 = st.number_input("W-2 Box 2 (Fed Withheld)", value=19000)

with col_b:
    st.subheader("Partner B")
    b_box1 = st.number_input("W-2 Box 1 (Taxable Wages)", value=206500)
    b_box17 = st.number_input("W-2 Box 17 (State Tax Paid)", value=18000)
    b_box2 = st.number_input("W-2 Box 2 (Fed Withheld)", value=35000)

# --- ROW 2: HOMEOWNER & PORTFOLIO ---
st.divider()
st.header("🏠 Homeowner, Charity & Brokerage")
c1, c2, c3 = st.columns(3)

with c1:
    prop_tax = st.number_input("Annual Property Taxes", value=15000)
    m_int = st.number_input("Mortgage Interest (1098)", value=22000)
    st.caption("Mortgage limit: Interest on first $750k of debt.")

with c2:
    charity_raw = st.number_input("Charitable Gifts (Total)", value=5000)
    med_oop = st.number_input("Medical Out-of-Pocket", value=0)
    st.caption("Note: 2026 rules apply floors to both of these.")

with c3:
    st_int = st.number_input("Interest Income (1099-INT)", value=5000)
    brokerage_net = st.number_input("Brokerage Gains / (Losses)", value=2000)
    st.caption("Losses up to -$3,000 can offset your salary.")

# --- THE 2026 CALCULATION ENGINE ---
# 1. Calculate AGI
total_agi = a_box1 + b_box1 + st_int + brokerage_net

# 2. SALT Dial Logic
raw_salt = a_box17 + b_box17 + prop_tax
actual_salt_deduction = min(raw_salt, SALT_CAP_2026)

# 3. 2026 Charity & Medical Floors
charity_floor = total_agi * 0.005 # 0.5% Floor
deductible_charity = max(0, charity_raw - charity_floor)

med_floor = total_agi * 0.075 # 7.5% Floor
deductible_med = max(0, med_oop - med_floor)

# 4. Final Deduction Selection
total_itemized = m_int + deductible_charity + deductible_med + actual_salt_deduction
final_deduction = max(total_itemized, FED_STD)

# 5. Final Tax
taxable_income = max(0, total_agi - final_deduction)
fed_liab = calc_tax(taxable_income, FED_BRACKETS) - 4400 # Less 2 Children
refund = (a_box2 + b_box2) - fed_liab

# --- THE VISUALS ---
st.divider()
v1, v2 = st.columns(2)

with v1:
    # SALT DIAL
    fig_dial = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = actual_salt_deduction,
        title = {'text': f"SALT Deduction Used (Cap: ${SALT_CAP_2026:,.0f})"},
        gauge = {
            'axis': {'range': [0, 50000]},
            'bar': {'color': "#2ecc71" if actual_salt_deduction < SALT_CAP_2026 else "#e74c3c"},
            'steps': [{'range': [0, 40400], 'color': "#ebf5fb"}, {'range': [40400, 50000], 'color': "#fadbd8"}],
            'threshold': {'line': {'color': "red", 'width': 4}, 'value': 40400}
        }
    ))
    st.plotly_chart(fig_dial, use_container_width=True)

with v2:
    # ITEMIZED BREAKDOWN
    labels = ['SALT', 'Mortgage', 'Charity', 'Medical']
    values = [actual_salt_deduction, m_int, deductible_charity, deductible_med]
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
    fig_pie.update_layout(title="Your Itemized Deduction Mix")
    st.plotly_chart(fig_pie, use_container_width=True)

# --- AUDIT TABLE ---
st.divider()
st.subheader("📋 Executive Audit Table")
st.table(pd.DataFrame({
    "Category": ["Total AGI", "Standard Deduction", "Your Itemized Total", "2026 Charity Floor (0.5%)", "Taxable Income"],
    "Value": [f"${total_agi:,.0f}", f"${FED_STD:,.0f}", f"${total_itemized:,.0f}", f"-${charity_floor:,.0f}", f"**${taxable_income:,.0f}**"]
}))
