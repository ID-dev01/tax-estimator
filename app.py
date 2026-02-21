import streamlit as st
import plotly.graph_objects as go

# --- 2026 AUDITOR DATA ---
LAW_2026 = {
    "Fed": {
        "MFJ": {"std": 32200, "salt_cap": 40000, "salt_phase": 500000, "ctc": 2200, "ctc_phase": 400000,
                "brackets": [(23850, 0.10), (96950, 0.12), (206700, 0.22), (394600, 0.24), (501050, 0.32), (751600, 0.35), (float('inf'), 0.37)]}
    },
    "NJ": {
        "MFJ": [(20000, 0.014), (50000, 0.0175), (70000, 0.0245), (80000, 0.035), (150000, 0.05525), (500000, 0.0637), (1000000, 0.0897), (float('inf'), 0.1075)],
        "prop_cap": 15000, "exemption": 1000
    }
}

def calc_tax(income, brackets):
    tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if income > prev:
            amt = min(income, limit) - prev
            tax += amt * rate
            prev = limit
        else: break
    return tax

st.set_page_config(layout="wide", page_title="2026 Spouse Tax & W-4 Fixer")
st.title("⚖️ 2026 MFJ Spouse Auditor & Paycheck Fixer")

# --- INCOME INPUTS ---
col_u, col_s = st.columns(2)
with col_u:
    st.header("👤 Your Income (NJ)")
    y_wages = st.number_input("Your W-2 Wages", value=145000.0)
    y_fwh = st.number_input("Your Fed Withheld To-Date", value=19000.0)
    y_swh = st.number_input("Your NJ Withheld To-Date", value=7000.0)
    y_k = st.number_input("Your Pre-Tax Contribs", value=10000.0)

with col_s:
    st.header("👤 Spouse Income (NY)")
    s_wages = st.number_input("Spouse W-2 Wages", value=135000.0)
    s_fwh = st.number_input("Spouse Fed Withheld To-Date", value=17000.0)
    s_ny_tax = st.number_input("Spouse ACTUAL NY Tax Liability", value=9500.0)
    s_k = st.number_input("Spouse Pre-Tax Contribs", value=10000.0)

# --- ENGINE ---
agi = (y_wages + s_wages) - (y_k + s_k)
conf = LAW_2026["Fed"]["MFJ"]
salt_cap = max(10000, conf["salt_cap"] - (max(0, agi - conf["salt_phase"]) * 0.30))
prop_tax = st.sidebar.number_input("Household Property Taxes", value=16000.0)
mrtg_int = st.sidebar.number_input("Mortgage Interest", value=22000.0)
kids = st.sidebar.number_input("Qualifying Children", value=2)

# Federal Calc
allowed_salt = min(prop_tax + y_swh + s_ny_tax, salt_cap)
fed_deduct = max(conf["std"], mrtg_int + allowed_salt)
fed_taxable = max(0, agi - fed_deduct)
final_ctc = max(0, (kids * conf["ctc"]) - ((max(0, agi - conf["ctc_phase"]) // 1000) * 50))
fed_liab = max(0, calc_tax(fed_taxable, conf["brackets"]) - final_ctc)
fed_diff = (y_fwh + s_fwh) - fed_liab

# NJ Calc
nj_taxable = max(0, agi - min(prop_tax, 15000) - (kids * 1000) - 2000)
nj_tax_pre_credit = calc_tax(nj_taxable, LAW_2026["NJ"]["MFJ"])
nj_credit = min(s_ny_tax, nj_tax_pre_credit * ((s_wages - s_k) / max(1, agi)))
nj_liab = nj_tax_pre_credit - nj_credit
nj_diff = y_swh - nj_liab

# --- THE PAYCHECK FIXER MOD ---
st.divider()
st.header("🛠️ The Paycheck Fixer")

if fed_diff < -1000 or nj_diff < -500:
    st.warning("⚠️ **Underpayment Detected:** You are currently on track to owe money. Avoid the 'Safe Harbor' penalty by adjusting your withholding now.")
    
    pay_periods = st.number_input("Remaining paychecks in 2026", min_value=1, max_value=26, value=20)
    
    f_col, n_col = st.columns(2)
    with f_col:
        fed_fix = abs(fed_diff) / pay_periods if fed_diff < 0 else 0
        st.subheader("Federal W-4")
        st.write(f"Add this to **Step 4(c)**:")
        st.code(f"${fed_fix:,.2f} per check")
        
    with n_col:
        nj_fix = abs(nj_diff) / pay_periods if nj_diff < 0 else 0
        st.subheader("NJ-W4")
        st.write(f"Add this to **Line 5**:")
        st.code(f"${nj_fix:,.2f} per check")
else:
    st.success("✅ **Withholding is Healthy:** You are currently within the $1,000 'Safe Harbor' or due for a refund.")

# --- VISUAL RESULTS ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    fig = go.Figure(go.Indicator(
        mode = "delta+number",
        value = (y_fwh + s_fwh),
        delta = {'reference': fed_liab, 'relative': False},
        title = {"text": "Federal Balance (Targeting Refund)"}
    ))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.info(f"**SALT Status:** Your personalized 2026 cap is **${salt_cap:,.0f}**. You have used **${allowed_salt:,.0f}** of it.")
