import os
import pandas as pd
import streamlit as st

# -----------------------------
# Page layout
# -----------------------------
st.set_page_config(
    page_title="PM2.5 Collocation Dashboard",
    layout="wide"
)

st.title("PM2.5 Collocation Tracking Dashboard")
st.markdown("""
**Instructions:**  
- Edit the "Total Sites" table below to simulate network changes and see the 15% collocation requirement update.  
- Click the "Reset Network Simulation" button to restore original values.  
- Tabs below show static tables only.
""")

# -----------------------------
# Load collocation data
# -----------------------------
collocation_file = os.path.join(os.path.dirname(__file__), "collocation_tracking_pm25.xlsx")
coll_df = pd.read_excel(collocation_file, sheet_name="Sheet1")
coll_df.columns = coll_df.columns.astype(str).str.strip()
coll_df['Is This Site Collocated?'] = coll_df['Is This Site Collocated?'].fillna('No')

# -----------------------------
# Helper functions
# -----------------------------
def calc_15pct(total):
    value = total * 0.15
    return max(1, round(value)) if value >= 0.5 else 1

def compliance_status(total_sites, collocated_sites):
    required = calc_15pct(total_sites)
    if collocated_sites >= required:
        status, alert = "Compliant", ""
    elif collocated_sites == required - 1:
        status, alert = "Approaching Threshold", "⚠️ Near Next Threshold"
    else:
        status, alert = "Not Compliant", ""
    return status, alert

# -----------------------------
# Collocation Summary
# -----------------------------
summary = coll_df.groupby('Method Type').agg(
    Method_Description=('Method Description', 'first'),
    Total_Sites=('Site Name', 'count'),
    Collocated_Sites=('Is This Site Collocated?', lambda x: (x=='Yes').sum())
).reset_index()

summary.rename(columns={'Method_Description': 'Method Description'}, inplace=True)

summary[['Compliance Status', 'Next Threshold Alert']] = summary.apply(
    lambda row: pd.Series(compliance_status(row['Total_Sites'], row['Collocated_Sites'])),
    axis=1
)

# -----------------------------
# Interactive Total Sites Editor
# -----------------------------
st.markdown("## Network Simulation: Adjust Total Sites by Method")
st.markdown("Modify the total number of monitoring sites to see how the 15% collocation requirement changes.")
st.markdown("---")

# Initialize session state
if "editable_summary" not in st.session_state:
    st.session_state.editable_summary = summary[['Method Type', 'Method Description', 'Total_Sites']].copy()

def calculate_after_edit(row):
    collocated = summary.loc[summary['Method Type'] == row['Method Type'], 'Collocated_Sites'].values[0]
    status, alert = compliance_status(row['Total_Sites'], collocated)
    return pd.Series([status, alert])

edited_summary = st.data_editor(
    st.session_state.editable_summary,
    key="total_sites_editor",
    width='stretch'
)

edited_summary[['Compliance Status After Edit', 'Next Threshold Alert After Edit']] = edited_summary.apply(
    calculate_after_edit, axis=1
)

st.markdown("### Updated Compliance Status Table")
st.dataframe(edited_summary, width='stretch')

# Reset interactive table
if st.button("Reset Network Simulation"):
    st.session_state.editable_summary = summary[['Method Type', 'Method Description', 'Total_Sites']].copy()
    st.experimental_rerun()

# -----------------------------
# Currently Collocated Sites
# -----------------------------
collocated_sites = coll_df[coll_df['Is This Site Collocated?'] == 'Yes']

# -----------------------------
# Geographic Analysis
# -----------------------------
dv_file = os.path.join(os.path.dirname(__file__), "dv_data_pm25_2025.xlsx")

# Read DesignValues
dv = pd.read_excel(dv_file, sheet_name="DesignValues")
dv.columns = dv.columns.astype(str).str.strip()

# Read AgencyName to assign agency to AQS ID
agency = pd.read_excel(dv_file, sheet_name="AgencyName")
agency.columns = agency.columns.astype(str).str.strip()  # ensure clean names

# Read AgencyPQAO to check if agency is in CARB's PQAO
agency_pqao = pd.read_excel(dv_file, sheet_name="AgencyPQAO")
agency_pqao.columns = agency_pqao.columns.astype(str).str.strip()

# NAAQS values
daily_naaqs = 35
annual_naaqs = 9

# Calculate percent differences relative to NAAQS
dv['Daily % Diff'] = ((dv['DAILY_DESIGN_VALUE'] / daily_naaqs) - 1) * 100
dv['Annual % Diff'] = ((dv['ANNUAL_DESIGN_VALUE'] / annual_naaqs) - 1) * 100

# Merge to assign agency name to each AQS ID
dv = dv.merge(
    agency[['AQS ID', 'Agency_Name']],
    left_on='AQS ID',
    right_on='AQS ID',
    how='left'
)

# Merge to get PQAO info for that agency
dv = dv.merge(
    agency_pqao[['Agency', 'PQAO']],
    left_on='Agency_Name',
    right_on='Agency',
    how='left'
)

# Identify if site is in CARB PQAO
dv['In CARB PQAO'] = dv['PQAO'].apply(lambda x: 'Yes' if str(x).upper() == 'CARB' else 'No')

# Determine if within 20% of NAAQS
dv['Daily Within 20%'] = dv['Daily % Diff'].apply(lambda x: 'Yes' if 80 <= x <= 120 else 'No')
dv['Annual Within 20%'] = dv['Annual % Diff'].apply(lambda x: 'Yes' if 80 <= x <= 120 else 'No')

# Possible geographic site: CARB and within 20% of either daily or annual
dv['Possible Geographic Site'] = dv.apply(
    lambda x: 'Yes' if (x['In CARB PQAO'] == 'Yes') and (x['Daily Within 20%'] == 'Yes' or x['Annual Within 20%'] == 'Yes') else 'No',
    axis=1
)

# Select columns to display
geo_analysis = dv[['AQS ID','Local Site Name','DAILY_DESIGN_VALUE','ANNUAL_DESIGN_VALUE',
                   'Daily % Diff','Annual % Diff','Daily Within 20%','Annual Within 20%',
                   'Agency_Name','In CARB PQAO','Possible Geographic Site']]
# -----------------------------
# Tabs for static tables only
# -----------------------------
tab1, tab2, tab3 = st.tabs([
    "Collocation Summary",
    "Currently Collocated Sites",
    "Geographic Analysis"
])

with tab1:
    st.subheader("Collocation Summary Table")
    st.dataframe(summary, width='stretch')

with tab2:
    st.subheader("Currently Collocated Sites Table")
    st.dataframe(collocated_sites, width='stretch')

with tab3:
    st.subheader("Geographic Analysis Table")
    st.dataframe(geo_analysis, width='stretch')