import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import re
import requests

# Page Setup
st.set_page_config(page_title="DHA Personal Property Portal", layout="wide")

# Google Apps Script Webhook URL
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbz4NxFv3LQbpY18JMBcmf4wUAIYikSButRr5C8ODtAVA--m71to_e3_o_nxVGi7GqzYiw/exec"

# DHA Lahore Complete Phases List
DHA_PHASES_LIST = [
    "Phase 1", "Phase 2", "Phase 3", "Phase 4", 
    "Phase 5", "Phase 6", "Phase 7", "Phase 8", 
    "Phase 8 (IVY Green)", "Phase 9 Town", "Phase 9 Prism", 
    "Phase 10", "Phase 11 (Rahbar)", "Phase 12 (EME)", "Phase 13"
]

# --- DATABASE SETUP ---
if "property_db" not in st.session_state:
    st.session_state.property_db = pd.DataFrame(columns=[
        "Date", "Phase", "Block_Zone_CCA", "Prop_Category", "Portion_Type",
        "Plot_Size", "Road_Width", "Features", "Price_Demand",
        "Dealer_Name", "Contact", "Source", "Status", "Notes"
    ])

def sync_to_google_sheet(data_payload):
    """Sync single record or list of records to Google Sheet via Webhook"""
    try:
        response = requests.post(WEBHOOK_URL, json=data_payload, headers={"Content-Type": "application/json"})
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error syncing to Google Sheet: {e}")
        return False

st.title("🏡 DHA Real Estate Workspace")

# --- TOP COLLAPSIBLE INPUT SECTION ---
with st.expander("➕ Add New Property / Input Options (Click to Open)", expanded=False):
    input_type = st.radio("Select Input Method", ["Manual Detail Entry", "Upload Bulk TXT File"], horizontal=True)
    
    if input_type == "Manual Detail Entry":
        source_type = st.radio("Select Source", ["WhatsApp Raw Text", "Newspaper Scan", "Own Field Working"], horizontal=True)
        raw_text = st.text_area("Paste Raw Property Text here...", height=80)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            phase = st.selectbox("Select DHA Phase", DHA_PHASES_LIST)
            category = st.selectbox("Category", ["Residential Plot", "Commercial", "House for Sale", "House for Rent"])
        with col2:
            block_zone = st.text_input("Block / Zone / CCA", value="Block M / Zone 1")
            portion = st.selectbox("Portion Type", ["N/A (Plot)", "Full House", "Upper Portion", "Lower Portion", "Basement"])
        with col3:
            size = st.selectbox("Size", ["5 Marla", "10 Marla", "1 Kanal", "2 Marla Comm", "4 Marla Comm", "Non-Standard (6-40M)"])
            demand = st.text_input("Demand / Rent", value="2.10 Crore")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            features = st.multiselect("Plot Features", ["Facing Park", "Corner", "Main Boulevard", "Excess Land", "Near Mosque"])
            dealer_name = st.text_input("Dealer Name", value="Ali Real Estate")
        with col_f2:
            road_width = st.selectbox("Road Width", ["40ft", "60ft", "80ft", "150ft Blvd", "200ft Blvd"])
            contact_num = st.text_input("Contact Number", value="03001234567")

        notes = st.text_input("Personal Conversation Notes", value="Owner urgent sale")

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
            # Save locally
            st.session_state.property_db = pd.concat([st.session_state.property_db, pd.DataFrame([new_row])], ignore_index=True)
            
            # Sync to Google Sheet
            if sync_to_google_sheet(new_row):
                st.success("Record Added Successfully & Synced to Google Sheet!")
            else:
                st.warning("Record saved locally, but Google Sheet sync failed.")

    else:
        uploaded_file = st.file_uploader("Choose a .txt file", type=["txt"])
        if uploaded_file is not None:
            stringio = uploaded_file.getvalue().decode("utf-8")
            messages = stringio.split("\n\n")
            st.info(f"Detected {len(messages)} potential listing entries.")
            if st.button("Process TXT File & Sync to Google Sheet", type="primary"):
                new_entries = []
                for msg in messages:
                    if len(msg.strip()) > 10:
                        ph = "Phase 9 Prism" if "prism" in msg.lower() or "9" in msg else "Phase 6"
                        sz = "1 Kanal" if "kanal" in msg.lower() else "10 Marla"
                        phones = re.findall(r'03\d{9}', msg.replace('-', ''))
                        phone_no = phones[0] if phones else "N/A"
                        new_entries.append({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Phase": ph,
                            "Block_Zone_CCA": "Auto-Extracted",
                            "Prop_Category": "Residential Plot",
                            "Portion_Type": "N/A (Plot)",
                            "Plot_Size": sz,
                            "Road_Width": "Standard",
                            "Features": "Extracted from File",
                            "Price_Demand": "Check Text",
                            "Dealer_Name": "Bulk Dealer",
                            "Contact": phone_no,
                            "Source": "Bulk TXT File",
                            "Status": "Available",
                            "Notes": msg[:50] + "..."
                        })
                if new_entries:
                    st.session_state.property_db = pd.concat([st.session_state.property_db, pd.DataFrame(new_entries)], ignore_index=True)
                    
                    # Batch Sync to Google Sheet
                    with st.spinner("Syncing all records to Google Sheet..."):
                        if sync_to_google_sheet(new_entries):
                            st.success(f"Added & Synced {len(new_entries)} records to Google Sheet!")
                        else:
                            st.warning("Processed records locally, but Google Sheet sync encountered an issue.")

st.divider()

# --- MAIN DASHBOARD FRONT END ---
tab_voice_search, tab_sheet_view = st.tabs([
    "🎙️ Voice / Text Smart Search & WA Export", 
    "📊 Master Sheet Table View"
])

# --- TAB 1: VOICE COMMAND SEARCH & WHATSAPP GENERATOR ---
with tab_voice_search:
    st.subheader("🎙️ Voice Command & Smart Property Filter")
    st.caption("موبائل کی بورڈ کے مائیک (Mic) بٹن پر کلک کر کے بولیں (e.g. 'Prism M block 1 kanal')")
    
    voice_query = st.text_input("🗣️ Spoken Search Command / Keyword:", placeholder="Click mic on your mobile keyboard & speak e.g. 'Prism M Block'")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_phase = st.multiselect("Filter Phase", DHA_PHASES_LIST)
    with col_f2:
        selected_size = st.multiselect("Filter Size", ["5 Marla", "10 Marla", "1 Kanal", "2 Marla Comm", "4 Marla Comm"])

    # Filtering Logic
    df_filtered = st.session_state.property_db.copy()

    if voice_query:
        keywords = voice_query.lower().split()
        for kw in keywords:
            df_filtered = df_filtered[
                df_filtered['Phase'].str.lower().str.contains(kw, na=False) |
                df_filtered['Block_Zone_CCA'].str.lower().str.contains(kw, na=False) |
                df_filtered['Plot_Size'].str.lower().str.contains(kw, na=False) |
                df_filtered['Features'].str.lower().str.contains(kw, na=False) |
                df_filtered['Notes'].str.lower().str.contains(kw, na=False)
            ]

    if selected_phase:
        df_filtered = df_filtered[df_filtered["Phase"].isin(selected_phase)]
    if selected_size:
        df_filtered = df_filtered[df_filtered["Plot_Size"].isin(selected_size)]

    st.markdown("---")
    
    if not df_filtered.empty:
        st.success(f"Found {len(df_filtered)} matching properties!")
        
        # Prepare WhatsApp Bulk List Text Format
        wa_text = "📋 *DHA LAHORE PROPERTY LISTING*\n"
        wa_text += f"🗓️ Date: {datetime.now().strftime('%d-%b-%Y')}\n"
        wa_text += "-----------------------------------\n\n"
        
        for idx, row in df_filtered.iterrows():
            wa_text += f"📍 *{row['Phase']} - {row['Block_Zone_CCA']}*\n"
            wa_text += f"📐 Size: {row['Plot_Size']} ({row['Prop_Category']})\n"
            wa_text += f"💰 Demand: {row['Price_Demand']}\n"
            if row['Features']: wa_text += f"⭐ Features: {row['Features']}\n"
            wa_text += f"📞 Contact: {row['Contact']} ({row['Dealer_Name']})\n"
            wa_text += "-----------------------------------\n"
            
            # Display Cards on UI
            with st.expander(f"📍 {row['Phase']} - {row['Block_Zone_CCA']} | {row['Plot_Size']} - {row['Price_Demand']}"):
                st.write(f"**Features:** {row['Features']} | **Road:** {row['Road_Width']}")
                st.write(f"**Dealer:** {row['Dealer_Name']} ({row['Contact']})")
                st.write(f"**Notes:** {row['Notes']}")
        
        # Direct WhatsApp Share Button
        encoded_wa_list = urllib.parse.quote(wa_text)
        wa_direct_url = f"https://api.whatsapp.com/send?text={encoded_wa_list}"
        
        st.markdown("### 🚀 Send Generated List to WhatsApp")
        st.markdown(f'''
            <a href="{wa_direct_url}" target="_blank">
                <button style="background-color:#25D366; color:white; border:none; padding:12px 24px; font-size:16px; border-radius:8px; cursor:pointer; font-weight:bold;">
                    📲 Open WhatsApp & Send Full List
                </button>
            </a>
        ''', unsafe_allow_html=True)
        
    else:
        st.info("No matching records found. Speak another query or add new listings.")

# --- TAB 2: MASTER SHEET TABLE ---
with tab_sheet_view:
    st.subheader("Master Sheet View")
    st.dataframe(st.session_state.property_db, use_container_width=True)
                        })
                if new_entries:
                    st.session_state.property_db = pd.concat([st.session_state.property_db, pd.DataFrame(new_entries)], ignore_index=True)
                    st.success(f"Added {len(new_entries)} records!")

st.divider()

# --- MAIN DASHBOARD FRONT END ---
tab_voice_search, tab_sheet_view = st.tabs([
    "🎙️ Voice / Text Smart Search & WA Export", 
    "📊 Master Sheet Table View"
])

# --- TAB 1: VOICE COMMAND SEARCH & WHATSAPP GENERATOR ---
with tab_voice_search:
    st.subheader("🎙️ Voice Command & Smart Property Filter")
    st.caption("موبائل کی بورڈ کے مائیک (Mic) بٹن پر کلک کر کے بولیں (e.g. 'Prism M block 1 kanal')")
    
    # Text input that works seamlessly with Phone Keyboard Mic / Voice-to-Text
    voice_query = st.text_input("🗣️ Spoken Search Command / Keyword:", placeholder="Click mic on your mobile keyboard & speak e.g. 'Prism M Block'")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_phase = st.multiselect("Filter Phase", DHA_PHASES_LIST)
    with col_f2:
        selected_size = st.multiselect("Filter Size", ["5 Marla", "10 Marla", "1 Kanal", "2 Marla Comm", "4 Marla Comm"])

    # Filtering Logic
    df_filtered = st.session_state.property_db.copy()

    if voice_query:
        # Search query matching across Phase, Block, Size, Notes
        keywords = voice_query.lower().split()
        for kw in keywords:
            df_filtered = df_filtered[
                df_filtered['Phase'].str.lower().str.contains(kw, na=False) |
                df_filtered['Block_Zone_CCA'].str.lower().str.contains(kw, na=False) |
                df_filtered['Plot_Size'].str.lower().str.contains(kw, na=False) |
                df_filtered['Features'].str.lower().str.contains(kw, na=False) |
                df_filtered['Notes'].str.lower().str.contains(kw, na=False)
            ]

    if selected_phase:
        df_filtered = df_filtered[df_filtered["Phase"].isin(selected_phase)]
    if selected_size:
        df_filtered = df_filtered[df_filtered["Plot_Size"].isin(selected_size)]

    st.markdown("---")
    
    if not df_filtered.empty:
        st.success(f"Found {len(df_filtered)} matching properties!")
        
        # Prepare WhatsApp Bulk List Text Format
        wa_text = "📋 *DHA LAHORE PROPERTY LISTING*\n"
        wa_text += f"🗓️ Date: {datetime.now().strftime('%d-%b-%Y')}\n"
        wa_text += "-----------------------------------\n\n"
        
        for idx, row in df_filtered.iterrows():
            wa_text += f"📍 *{row['Phase']} - {row['Block_Zone_CCA']}*\n"
            wa_text += f"📐 Size: {row['Plot_Size']} ({row['Prop_Category']})\n"
            wa_text += f"💰 Demand: {row['Price_Demand']}\n"
            if row['Features']: wa_text += f"⭐ Features: {row['Features']}\n"
            wa_text += f"📞 Contact: {row['Contact']} ({row['Dealer_Name']})\n"
            wa_text += "-----------------------------------\n"
            
            # Display Cards on UI
            with st.expander(f"📍 {row['Phase']} - {row['Block_Zone_CCA']} | {row['Plot_Size']} - {row['Price_Demand']}"):
                st.write(f"**Features:** {row['Features']} | **Road:** {row['Road_Width']}")
                st.write(f"**Dealer:** {row['Dealer_Name']} ({row['Contact']})")
                st.write(f"**Notes:** {row['Notes']}")
        
        # Direct WhatsApp Share Button for Full Formatted List
        encoded_wa_list = urllib.parse.quote(wa_text)
        wa_direct_url = f"https://api.whatsapp.com/send?text={encoded_wa_list}"
        
        st.markdown("### 🚀 Send Generated List to WhatsApp")
        st.markdown(f'''
            <a href="{wa_direct_url}" target="_blank">
                <button style="background-color:#25D366; color:white; border:none; padding:12px 24px; font-size:16px; border-radius:8px; cursor:pointer; font-weight:bold;">
                    📲 Open WhatsApp & Send Full List
                </button>
            </a>
        ''', unsafe_allow_html=True)
        
    else:
        st.info("No matching records found. Speak another query or add new listings.")

# --- TAB 2: MASTER SHEET TABLE ---
with tab_sheet_view:
    st.subheader("Master Sheet View")
    st.dataframe(st.session_state.property_db, use_container_width=True)
