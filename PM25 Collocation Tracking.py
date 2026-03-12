import os
import pandas as pd
import math
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
- Edit the "Total Sites" table below to simulate network changes and see how the 15% collocation requirement updates.  
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
# Collocation Summary
# -----------------------------
def calc_15pct(total):
    """Calculate 15% requirement. Values >= 0.5 round up, else minimum 1"""
    value = total * 0.15
    return max(1, round(value)) if value >= 0.5 else 1

summary = coll_df.groupby('Method Type').agg(
    Method_Description=('Method Description', 'first'),
    Total_Sites=('Site Name', 'count'),
    Collocated_Sites=('Is This Site Collocated?', lambda x: (x=='Yes').sum())
).reset_index()

summary['15% Requirement'] = summary['Total_Sites'].apply(calc_15pct)

def compliance_status(total_sites, collocated_sites):
    required = calc_15pct(total_sites)
    
    if collocated_sites >= required:
        status = "Compliant"
        alert = ""
    elif collocated_sites == required - 1:
        status = "Approaching Threshold"
        alert = "⚠️ Near Next Threshold"
    else:
        status = "Not Compliant"
        alert = ""
    
    return status, alert

summary[['Compliance Status', 'Next Threshold Alert']] = summary.apply(
    lambda row: pd.Series(compliance_status(row['Total_Sites'], row['Collocated_Sites'])),
    axis=1
)

# -----------------------------
# Interactive Total Sites Editor with Compliance Status
# -----------------------------
st.subheader("Edit Total Sites to Simulate Network Changes")
st.markdown("Edit the 'Total Sites' column and see updated compliance status.")

# Step 1: start with editable summary
editable_summary = summary[['Method Type', 'Total_Sites']].copy()

# Step 2: let user edit the table
try:
    edited_summary = st.experimental_data_editor(editable_summary, key="total_sites_editor", width=500)
except AttributeError:
    # fallback if experimental_data_editor not available
    edited_summary = editable_summary.copy()

# Step 3: calculate updated 15% requirement for edits
edited_summary['15% Requirement'] = edited_summary['Total_Sites'].apply(calc_15pct)

# Step 4: calculate updated compliance status for each row
def compliance_from_edited(row):
    method = row['Method Type']
    total_sites = row['Total_Sites']
    collocated_sites = summary.loc[summary['Method Type'] == method, 'Collocated_Sites'].values[0]
    status, alert = compliance_status(total_sites, collocated_sites)
    return f"{status} {alert}".strip()

edited_summary['Compliance Status After Edit'] = edited_summary.apply(compliance_from_edited, axis=1)

# Step 5: display table with updated compliance
st.dataframe(edited_summary, use_container_width=True)

# Step 6: optional reset button
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
tab1, tab2, tab3 = st.tabs(["Collocation Summary", "Currently Collocated Sites", "Geographic Analysis"])

with tab1:
    st.subheader("Collocation Summary Table")
    st.dataframe(summary, use_container_width=True)

with tab2:
    st.subheader("Currently Collocated Sites Table")
    st.dataframe(collocated_sites, use_container_width=True)

with tab3:
    st.subheader("Geographic Analysis Table")
    st.dataframe(geo_analysis, use_container_width=True)