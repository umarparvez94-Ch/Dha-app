import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

# Page Setup
st.set_page_config(page_title="DHA Personal Property Portal", layout="wide")

# --- DATABASE SETUP ---
if "property_db" not in st.session_state:
    st.session_state.property_db = pd.DataFrame(columns=[
        "Date", "Phase", "Block_Zone_CCA", "Prop_Category", "Portion_Type",
        "Plot_Size", "Road_Width", "Features", "Price_Demand",
        "Dealer_Name", "Contact", "Source", "Status", "Notes"
    ])

st.title("🏡 DHA Personal Real Estate Workspace")
st.caption("Personal Testing Edition | Free Single-User Setup")

# Navigation Tabs
tab_input, tab_search, tab_dealer_history = st.tabs([
    "📥 Quick Input (WhatsApp / Raw Text)", 
    "🔍 Filter & Search Properties", 
    "📞 Dealers & History Logs"
])

# --- TAB 1: INPUT CENTER ---
with tab_input:
    st.subheader("Add Property Entry")
    
    source_type = st.radio("Select Source", ["WhatsApp Raw Text", "Newspaper Scan", "Own Field Working"], horizontal=True)
    raw_text = st.text_area("Paste Raw Property Text here...", height=100)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        phase = st.selectbox("Phase", ["Phase 9 Prism", "Phase 6", "Phase 5", "Phase 8", "Phase 7", "Phase 1 to 4"])
        category = st.selectbox("Category", ["Residential Plot", "Commercial", "House for Sale", "House for Rent"])
    with col2:
        block_zone = st.text_input("Block / Zone / CCA", value="Zone 1 / CCA 1")
        portion = st.selectbox("Portion Type", ["N/A (Plot)", "Full House", "Upper Portion", "Lower Portion", "Basement"])
    with col3:
        size = st.selectbox("Size", ["5 Marla", "10 Marla", "1 Kanal", "2 Marla Comm", "4 Marla Comm", "Non-Standard (6-40M)"])
        demand = st.text_input("Demand / Rent", value="1.25 Crore / 1.5 Lac")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        features = st.multiselect("Plot Features", ["Facing Park", "Corner", "Main Boulevard", "Excess Land", "Near Mosque"])
        dealer_name = st.text_input("Dealer Name", value="Ali Real Estate")
    with col_f2:
        road_width = st.selectbox("Road Width", ["40ft", "60ft", "80ft", "150ft Blvd", "200ft Blvd"])
        contact_num = st.text_input("Contact Number", value="03001234567")

    notes = st.text_input("Personal Conversation Notes", value="Owner final on 1.20 Cr")

    if st.button("Save Property Record", type="primary"):
        new_row = {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Phase": phase,
            "Block_Zone_CCA": block_zone,
            "Prop_Category": category,
            "Portion_Type": portion,
            "Plot_Size": size,
            "Road_Width": road_width,
            "Features": ", ".join(features),
            "Price_Demand": demand,
            "Dealer_Name": dealer_name,
            "Contact": contact_num,
            "Source": source_type,
            "Status": "Available",
            "Notes": notes
        }
        st.session_state.property_db = pd.concat([st.session_state.property_db, pd.DataFrame([new_row])], ignore_index=True)
        st.success("Record Added Successfully!")

# --- TAB 2: SEARCH & ACTION BUTTONS ---
with tab_search:
    st.subheader("Filter Properties")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        filter_cat = st.multiselect("Category", ["Residential Plot", "Commercial", "House for Sale", "House for Rent"])
    with col_s2:
        filter_portion = st.multiselect("Portion Filter", ["Full House", "Upper Portion", "Lower Portion"])
    with col_s3:
        filter_phase = st.multiselect("Phase Filter", ["Phase 9 Prism", "Phase 6", "Phase 5"])

    df = st.session_state.property_db.copy()
    
    if not df.empty:
        for idx, row in df.iterrows():
            with st.expander(f"📍 {row['Phase']} - {row['Block_Zone_CCA']} | {row['Plot_Size']} ({row['Prop_Category']}) - {row['Price_Demand']}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Portion:** {row['Portion_Type']}")
                    st.write(f"**Features:** {row['Features']}")
                    st.write(f"**Road:** {row['Road_Width']}")
                with c2:
                    st.write(f"**Dealer:** {row['Dealer_Name']}")
                    st.write(f"**Source:** {row['Source']}")
                    st.write(f"**Notes:** {row['Notes']}")
                with c3:
                    encoded_msg = urllib.parse.quote(f"AoA, inquiring about {row['Phase']} {row['Block_Zone_CCA']} {row['Plot_Size']} demand {row['Price_Demand']}")
                    wa_url = f"https://wa.me/{row['Contact'].replace('-', '')}?text={encoded_msg}"
                    st.markdown(f"[💬 Chat on WhatsApp]({wa_url})", unsafe_allow_html=True)
                    st.write(f"📞 **Call:** {row['Contact']}")
    else:
        st.info("No records added yet. Add entries in the Quick Input tab.")

# --- TAB 3: DEALER LOGS ---
with tab_dealer_history:
    st.subheader("Dealer Activity Tracking")
    st.dataframe(st.session_state.property_db[["Date", "Dealer_Name", "Contact", "Phase", "Price_Demand", "Notes"]])
