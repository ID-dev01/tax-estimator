import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 2025 TAX RULES ---
RULES = {
    "NJ_Brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)],
    "NY_Brackets": [(17150, 0.04), (23600, 0.045), (27900, 0.0525), (161550, 0.055), (323200, 0.06)],
    "MFS_NJ_Brackets": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637)] 
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        amt = min(income - prev, limit - prev)
        if amt > 0: tax += amt * rate; prev = limit
        else: break
    return tax

st.set_page_config(page_title="NJ Filing Status Comparison", layout="wide")
st.title("⚖️ NJ Filing Status: Joint vs. Separate")

col_in, col_viz = st.columns([1.5, 1], gap="large")

with col_in:
    st.subheader("W-2 Inputs")
    c1, c2 = st.columns(2)
    tp_b1 = c1.number_input("Your Box 1 (NJ Worker)", 0.0, value=85000.0)
    tp_wh = c1.number_input("Your NJ Withholding (Box 17)", 0.0, value=3500.0)
    
    sp_b1 = c2.number_input("Spouse Box 1 (NY Worker)", 0.0, value=95000.0)
    sp_ny_tax = c2.number_input("Spouse NY Tax Paid", 0.0, value=5200.0)

# --- COMPARISON LOGIC ---
# SCENARIO 1: Joint (MFJ)
joint_income = tp_b1 + sp_b1
joint_tax_raw = calc_tax(joint_income, RULES["NJ_Brackets"])
# NY Credit for Joint
joint_credit = min(sp_ny_tax, joint_tax_raw * (sp_b1 / joint_income))
joint_final_tax = max(0, joint_tax_raw - joint_credit)
joint_refund = tp_wh - joint_final_tax

# SCENARIO 2: Separate (MFS)
# You (NJ Only)
tp_tax_sep = calc_tax(tp_b1, RULES["MFS_NJ_Brackets"])
tp_refund_sep = tp_wh - tp_tax_sep

# Spouse (NY Only - effectively $0 NJ tax due to credit)
sp_tax_raw_sep = calc_tax(sp_b1, RULES["MFS_NJ_Brackets"])
sp_credit_sep = min(sp_ny_tax, sp_tax_raw_sep)
sp_refund_sep = 0 - (sp_tax_raw_sep - sp_credit_sep) # Assuming 0 NJ withholding for her

total_sep_refund = tp_refund_sep + sp_refund_sep

with col_viz:
    st.subheader("The Verdict")
    
    fig = go.Figure(data=[
        go.Bar(name='Joint (MFJ)', x=['Refund Amount'], y=[joint_refund], marker_color='#002d72'),
        go.Bar(name='Separate (MFS)', x=['Refund Amount'], y=[total_sep_refund], marker_color='#28a745')
    ])
    fig.update_layout(barmode='group', height=300, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    diff = total_sep_refund - joint_refund
    if diff > 0:
        st.success(f"📈 **Filing Separately** could save you **${diff:,.2f}** in NJ!")
    else:
        st.info(f"📉 **Filing Jointly** is better by **${abs(diff):,.2f}**.")

    with st.expander("Why the difference?"):
        st.write("When you file **Jointly**, your spouse's income pushes your household into a **higher tax bracket** (e.g., jumping from 3.5% to 5.5%). Even with the NY credit, you might end up paying a higher rate on *your* NJ income than you would if you filed alone.")
