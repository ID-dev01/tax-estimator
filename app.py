import streamlit as st

# --- 2025-2026 CAPS ---
NJ_CAPS = {"UI": 184.02, "FLI": 545.82, "DI": 380.42}
NY_CAPS = {"PFL": 354.53, "SDI": 31.20}

st.set_page_config(page_title="NJ/NY Final Auditor", layout="wide")
st.title("🛡️ Final Household Tax Auditor")

col_in, col_res = st.columns([1.5, 1])

with col_in:
    st.subheader("W-2 Audit (Box 14 & 17)")
    
    # TAXPAYER
    st.info("👤 **Taxpayer (NJ Worker)**")
    t_fwh = st.number_input("Fed Withholding (Box 2)", 0.0, key="t2")
    t_swh = st.number_input("NJ Withholding (Box 17)", 0.0, key="t17")
    st.caption(f"Your Box 14: UI ${NJ_CAPS['UI']} | FLI $545.78 (At Cap)")

    # SPOUSE
    st.warning("🗽 **Spouse (NY Worker)**")
    s_fwh = st.number_input("Spouse Fed Wh (Box 2)", 0.0, key="s2")
    s_swh_ny = st.number_input("NY State Tax (Box 17)", 0.0, key="s17ny")
    st.caption(f"Her Box 14: NY PFL ${NY_CAPS['PFL']} | SDI ${NY_CAPS['SDI']} (At Cap)")

    # TOTAL HOUSEHOLD INCOME
    total_income = st.number_input("Total Household Income (Box 1 Sum)", 0.0)

# --- THE AUDIT LOGIC ---
# 1. Calculate Estimated NJ Tax (Simplified)
# For a typical NJ/NY family, the NY credit often makes the "Effective NJ Tax Rate" very low.
est_nj_tax_before_credit = total_income * 0.04 # Rough 4% bracket
ny_credit = s_swh_ny # Often the credit is the full amount paid to NY

# 2. Final Liability
final_nj_liability = max(0, est_nj_tax_before_credit - ny_credit)
nj_refund = t_swh - final_nj_liability

with col_res:
    st.subheader("The Refund Verdict")
    if nj_refund > (t_swh * 0.8):
        st.success(f"**Massive NJ Refund Estimated:** ~${nj_refund:,.2f}")
        st.write("### Why?")
        st.write(f"1. Your spouse paid **${s_swh_ny:,.2f}** to NY.")
        st.write("2. NJ credits almost all of that against your joint bill.")
        st.write(f"3. Your NJ withholding of **${t_swh:,.2f}** is now 'excess' money.")
    else:
        st.metric("Estimated NJ Refund", f"${nj_refund:,.2f}")

    st.divider()
    st.info("📝 **CPA Note:** Tell your CPA: 'My spouse's NY tax credit is wiping out our NJ liability. I want to ensure my NJ-1040 Schedule G is maximizing the credit for taxes paid to NY.'")
