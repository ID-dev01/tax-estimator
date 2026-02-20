import streamlit as st
from datetime import date

st.set_page_config(layout="wide", page_title="2025 CPA-Grade Tax Estimator")

# ============================================================
# 2025 FEDERAL + NJ + NY LAW (Structured Properly)
# ============================================================

LAW = {
    "Federal": {
        "standard_deduction": {
            "Single": 14600,
            "Married Filing Jointly": 29200
        },
        "brackets": {
            "Single": [
                (11600, 0.10),
                (47150, 0.12),
                (100525, 0.22),
                (191950, 0.24),
                (243725, 0.32),
                (609350, 0.35),
                (float("inf"), 0.37)
            ],
            "Married Filing Jointly": [
                (23200, 0.10),
                (94300, 0.12),
                (201050, 0.22),
                (383900, 0.24),
                (487450, 0.32),
                (731200, 0.35),
                (float("inf"), 0.37)
            ]
        },
        "ctc": 2000,
        "ctc_phaseout": {
            "Single": 200000,
            "Married Filing Jointly": 400000
        },
        "salt_cap": 10000
    },

    "NJ": {
        "brackets": [
            (20000, 0.014),
            (50000, 0.0175),
            (70000, 0.0245),
            (80000, 0.035),
            (150000, 0.05525),
            (500000, 0.0637),
            (float("inf"), 0.0897)
        ],
        "personal_exemption": 1000,
        "property_tax_cap": 15000
    },

    "NY": {
        "standard_deduction": {
            "Single": 8000,
            "Married Filing Jointly": 16050
        },
        "brackets": [
            (17150, 0.04),
            (23600, 0.045),
            (27900, 0.0525),
            (161550, 0.055),
            (323200, 0.06),
            (float("inf"), 0.0685)
        ]
    }
}


# ============================================================
# TAX ENGINE FUNCTIONS
# ============================================================

def calc_progressive_tax(income, brackets):
    tax = 0
    prev_limit = 0
    for limit, rate in brackets:
        if income > prev_limit:
            taxable_amount = min(income, limit) - prev_limit
            tax += taxable_amount * rate
            prev_limit = limit
        else:
            break
    return tax


def get_marginal_rate(income, brackets):
    prev_limit = 0
    for limit, rate in brackets:
        if income <= limit:
            return rate
        prev_limit = limit
    return brackets[-1][1]


def calculate_ctc(agi, filing_status, num_children):
    base_credit = num_children * LAW["Federal"]["ctc"]
    phaseout_threshold = LAW["Federal"]["ctc_phaseout"][filing_status]

    if agi <= phaseout_threshold:
        return base_credit

    excess = agi - phaseout_threshold
    reduction = (excess // 1000) * 50
    return max(0, base_credit - reduction)


# ============================================================
# UI
# ============================================================

st.title("🧾 CPA-Grade 2025 Tax Estimator")
st.markdown("Professional Federal + NJ + NY calculation engine")
st.markdown("---")

filing_status = st.selectbox(
    "Filing Status",
    ["Married Filing Jointly", "Single"]
)

st.markdown("### Income Inputs")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Spouse / Taxpayer 1")
    y_wages = st.number_input("W-2 Federal Wages", 0.0)
    y_fed_wh = st.number_input("Federal Withholding", 0.0)
    y_nj_wages = st.number_input("NJ Wages (if applicable)", 0.0)
    y_nj_wh = st.number_input("NJ Withholding", 0.0)

with col2:
    if filing_status == "Married Filing Jointly":
        st.markdown("#### Spouse 2")
        s_wages = st.number_input("Spouse W-2 Federal Wages", 0.0)
        s_fed_wh = st.number_input("Spouse Federal Withholding", 0.0)
        s_ny_wages = st.number_input("NY Wages (if applicable)", 0.0)
        s_ny_wh = st.number_input("NY Withholding", 0.0)
    else:
        s_wages = s_fed_wh = s_ny_wages = s_ny_wh = 0

st.markdown("### Additional Income")
interest_income = st.number_input("Interest Income", 0.0)
capital_gains = st.number_input("Net Capital Gains", 0.0)

st.markdown("### Deductions")
mortgage_interest = st.number_input("Mortgage Interest", 0.0)
property_tax = st.number_input("Property Tax Paid", 0.0)

num_children = st.number_input("Children Under 17", 0, 10, 0)

# ============================================================
# FEDERAL CALCULATION
# ============================================================

total_income = y_wages + s_wages + interest_income + capital_gains
agi = total_income

salt_uncapped = property_tax + y_nj_wh + s_ny_wh
salt_deduction = min(salt_uncapped, LAW["Federal"]["salt_cap"])

itemized = mortgage_interest + salt_deduction
standard = LAW["Federal"]["standard_deduction"][filing_status]

deduction_used = max(itemized, standard)
taxable_income = max(0, agi - deduction_used)

fed_brackets = LAW["Federal"]["brackets"][filing_status]
fed_tax = calc_progressive_tax(taxable_income, fed_brackets)

ctc = calculate_ctc(agi, filing_status, num_children)
fed_final_tax = max(0, fed_tax - ctc)

total_fed_withholding = y_fed_wh + s_fed_wh
fed_result = total_fed_withholding - fed_final_tax

fed_marginal_rate = get_marginal_rate(taxable_income, fed_brackets)

# ============================================================
# NJ CALCULATION
# ============================================================

nj_gross_income = y_nj_wages + s_wages + interest_income + capital_gains
nj_deductions = (
    2000 +
    (num_children * LAW["NJ"]["personal_exemption"]) +
    min(property_tax, LAW["NJ"]["property_tax_cap"])
)

nj_taxable = max(0, nj_gross_income - nj_deductions)
nj_tax_raw = calc_progressive_tax(nj_taxable, LAW["NJ"]["brackets"])

# NY Tax (for resident credit calculation)
ny_taxable = max(
    0,
    s_ny_wages - LAW["NY"]["standard_deduction"][filing_status]
)
ny_tax = calc_progressive_tax(ny_taxable, LAW["NY"]["brackets"])

# Proper Resident Credit Structure
if nj_gross_income > 0:
    credit_ratio = s_ny_wages / nj_gross_income
else:
    credit_ratio = 0

nj_resident_credit = min(ny_tax, nj_tax_raw * credit_ratio)
nj_final_tax = max(0, nj_tax_raw - nj_resident_credit)

nj_result = y_nj_wh - nj_final_tax
ny_result = s_ny_wh - ny_tax

# ============================================================
# RESULTS DASHBOARD
# ============================================================

st.markdown("---")
st.header("📊 Final Tax Summary")

colA, colB, colC = st.columns(3)

with colA:
    st.subheader("Federal")
    st.write(f"AGI: ${agi:,.2f}")
    st.write(f"Deduction Used: ${deduction_used:,.2f}")
    st.write(f"Taxable Income: ${taxable_income:,.2f}")
    st.write(f"Federal Tax: ${fed_tax:,.2f}")
    st.write(f"Child Tax Credit: ${ctc:,.2f}")
    st.metric("Federal Refund / Owed", f"${fed_result:,.2f}")

with colB:
    st.subheader("New Jersey")
    st.write(f"Taxable Income: ${nj_taxable:,.2f}")
    st.write(f"NJ Tax Before Credit: ${nj_tax_raw:,.2f}")
    st.write(f"NJ Resident Credit: ${nj_resident_credit:,.2f}")
    st.metric("NJ Refund / Owed", f"${nj_result:,.2f}")

with colC:
    st.subheader("New York")
    st.write(f"Taxable Income: ${ny_taxable:,.2f}")
    st.write(f"NY Tax: ${ny_tax:,.2f}")
    st.metric("NY Refund / Owed", f"${ny_result:,.2f}")

st.markdown("---")
st.success("This estimate is for informational purposes only and does not constitute tax advice.")
