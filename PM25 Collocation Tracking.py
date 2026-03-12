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
file_path = r"C:\Users\nlambini\Desktop\Collocation Tracking Python\collocation_tracking_pm25.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")
df.columns = df.columns.astype(str).str.strip()
df['Is This Site Collocated?'] = df['Is This Site Collocated?'].fillna('No')

# -----------------------------
# Collocation Summary
# -----------------------------
def calc_15pct(total):
    value = total * 0.15
    if value >= 0.5:
        return max(1, round(value))
    else:
        return 1

summary = df.groupby('Method Type').agg(
    Method_Description=('Method Description', 'first'),
    Total_Sites=('Site Name', 'count'),
    Collocated_Sites=('Is This Site Collocated?', lambda x: (x=='Yes').sum())
).reset_index()

summary['15% Requirement'] = summary['Total_Sites'].apply(calc_15pct)

def compliance_status(total_sites, collocated_sites):
    required = calc_15pct(total_sites)
    next_threshold = math.ceil(total_sites / 7)
    if collocated_sites >= required:
        status = "Compliant"
    elif collocated_sites >= next_threshold - 1:
        status = "Approaching Threshold"
    else:
        status = "Not Compliant"
    alert = "⚠️ Near Next Threshold" if collocated_sites == next_threshold - 1 else ""
    return status, alert

summary[['Compliance Status', 'Next Threshold Alert']] = summary.apply(
    lambda row: pd.Series(compliance_status(row['Total_Sites'], row['Collocated_Sites'])),
    axis=1
)

# -----------------------------
# Interactive Total Sites Editor
# -----------------------------
st.subheader("Edit Total Sites to Simulate Network Changes")
st.markdown("The table below represents the number of sites for each distinct method in CARB's PQAO.")

editable_summary = summary[['Method Type', 'Total_Sites']].copy()
edited_summary = st.data_editor(editable_summary, key="total_sites_editor", width=400)

if st.button("Reset"):
    st.experimental_rerun()

# Update 15% requirement based on edited values
summary['Total_Sites'] = summary['Method Type'].map(dict(zip(edited_summary['Method Type'], edited_summary['Total_Sites'])))
summary['15% Requirement'] = summary['Total_Sites'].apply(calc_15pct)
summary[['Compliance Status', 'Next Threshold Alert']] = summary.apply(
    lambda row: pd.Series(compliance_status(row['Total_Sites'], row['Collocated_Sites'])),
    axis=1
)

# -----------------------------
# Currently Collocated Sites
# -----------------------------
collocated_sites = df[df['Is This Site Collocated?'] == 'Yes']

# -----------------------------
# Geographic Analysis
# -----------------------------
dv_file = r"C:\Users\nlambini\Desktop\Collocation Tracking Python\dv_data_pm25_2025.xlsx"
dv = pd.read_excel(dv_file, sheet_name="DesignValues")
dv.columns = dv.columns.astype(str).str.strip()

agency = pd.read_excel(dv_file, sheet_name="AgencyName")
agency.columns = agency.columns.astype(str).str.strip()

daily_naaqs = 35
annual_naaQs = 9

dv['Daily % Diff'] = (dv['DAILY_DESIGN_VALUE'] / daily_naaqs) * 100
dv['Annual % Diff'] = (dv['ANNUAL_DESIGN_VALUE'] / annual_naaQs) * 100

dv = dv.merge(agency[['AQS ID','Agency_Name']], on='AQS ID', how='left')
dv['In PQAO'] = dv['Agency_Name'].str.contains("California Air Resources Board", na=False)

dv['Possible Collocated Site'] = dv.apply(
    lambda x: "Yes" if x['In PQAO'] and (x['Daily % Diff'] <= 120 or x['Annual % Diff'] <= 120) else "No",
    axis=1
)

geo_analysis = dv[['AQS ID','Local Site Name','DAILY_DESIGN_VALUE','ANNUAL_DESIGN_VALUE','Daily % Diff','Annual % Diff','In PQAO','Possible Collocated Site']]

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3 = st.tabs(["Collocation Summary", "Currently Collocated Sites", "Geographic Analysis"])

with tab1:
    st.subheader("Collocation Summary Table")
    st.dataframe(summary, width="stretch")

with tab2:
    st.subheader("Currently Collocated Sites Table")
    st.dataframe(collocated_sites, width="stretch")

with tab3:
    st.subheader("Geographic Analysis Table")
    st.dataframe(geo_analysis, width="stretch")