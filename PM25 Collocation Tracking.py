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
- Click the "Reset" button to restore original values.  
- Expand tabs to view each section.
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
    """Calculate 15% requirement (minimum 1). Values >=0.5 round up."""
    value = total * 0.15
    return max(1, round(value)) if value >= 0.5 else 1

def compliance_status(total_sites, collocated_sites):
    """Return compliance status and next threshold alert."""
    required = calc_15pct(total_sites)
    next_threshold = required + 1
    if collocated_sites >= required:
        status = "Compliant"
    elif collocated_sites == next_threshold - 1:
        status = "Approaching Threshold"
    else:
        status = "Not Compliant"
    alert = "⚠️ Near Next Threshold" if collocated_sites == next_threshold - 1 else ""
    return status, alert

# -----------------------------
# Collocation Summary
# -----------------------------
summary = coll_df.groupby('Method Type').agg(
    Method_Description=('Method Description', 'first'),
    Total_Sites=('Site Name', 'count'),
    Collocated_Sites=('Is This Site Collocated?', lambda x: (x=='Yes').sum())
).reset_index()

summary['15% Requirement'] = summary['Total_Sites'].apply(calc_15pct)
summary[['Compliance Status', 'Next Threshold Alert']] = summary.apply(
    lambda row: pd.Series(compliance_status(row['Total_Sites'], row['Collocated_Sites'])),
    axis=1
)

# -----------------------------
# Interactive Total Sites Editor
# -----------------------------
st.subheader("Edit Total Sites to Simulate Network Changes")

editable_summary = summary[['Method Type', 'Method_Description', 'Total_Sites']].copy()
summary.rename(columns={'Method_Description': 'Method Description'}, inplace=True)

edited_summary = st.data_editor(
    editable_summary,
    key="total_sites_editor",
    use_container_width=True
)

def calculate_after_edit(row):
    collocated = summary.loc[summary['Method Type'] == row['Method Type'], 'Collocated_Sites'].values[0]
    status, alert = compliance_status(row['Total_Sites'], collocated)
    return pd.Series([status, alert])

edited_summary[['Compliance Status After Edit', 'Next Threshold Alert After Edit']] = edited_summary.apply(
    calculate_after_edit, axis=1
)

st.subheader("Updated Compliance Status Table")
st.dataframe(edited_summary, use_container_width=True)

if st.button("Reset"):
    st.experimental_rerun()

# -----------------------------
# Currently Collocated Sites
# -----------------------------
collocated_sites = coll_df[coll_df['Is This Site Collocated?'] == 'Yes']

# -----------------------------
# Geographic Analysis
# -----------------------------
dv_file = os.path.join(os.path.dirname(__file__), "dv_data_pm25_2025.xlsx")
dv = pd.read_excel(dv_file, sheet_name="DesignValues")
dv.columns = dv.columns.astype(str).str.strip()

agency = pd.read_excel(dv_file, sheet_name="AgencyName")
agency.columns = agency.columns.astype(str).str.strip()

daily_naaqs = 35
annual_naaqs = 9

dv['Daily % Diff'] = (dv['DAILY_DESIGN_VALUE'] / daily_naaqs) * 100
dv['Annual % Diff'] = (dv['ANNUAL_DESIGN_VALUE'] / annual_naaqs) * 100

dv = dv.merge(agency[['AQS ID','Agency_Name']], on='AQS ID', how='left')
dv['In PQAO'] = dv['Agency_Name'].str.contains("California Air Resources Board", na=False)

dv['Possible Collocated Site'] = dv.apply(
    lambda x: "Yes" if x['In PQAO'] and (x['Daily % Diff'] <= 120 or x['Annual % Diff'] <= 120) else "No",
    axis=1
)

geo_analysis = dv[['AQS ID','Local Site Name','DAILY_DESIGN_VALUE','ANNUAL_DESIGN_VALUE',
                   'Daily % Diff','Annual % Diff','In PQAO','Possible Collocated Site']]

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Collocation Summary",
    "Currently Collocated Sites",
    "Geographic Analysis",
    "Interactive Total Sites Editor"
])

with tab1:
    st.subheader("Collocation Summary Table")
    st.dataframe(summary, use_container_width=True)

with tab2:
    st.subheader("Currently Collocated Sites Table")
    st.dataframe(collocated_sites, use_container_width=True)

with tab3:
    st.subheader("Geographic Analysis Table")
    st.dataframe(geo_analysis, use_container_width=True)

with tab4:
    st.subheader("Interactive Total Sites Editor")
    st.dataframe(edited_summary, use_container_width=True)