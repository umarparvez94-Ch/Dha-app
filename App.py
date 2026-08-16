import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import json
from datetime import datetime
import urllib.parse

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DHA Enterprise CRM & Ingestion Center",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GOOGLE STITCH ROYAL BLUE STYLING ---
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background: #161b22; padding: 15px; border-radius: 8px; border-left: 4px solid #1f6feb; }
    .badge-card { background: #161b22; padding: 10px 15px; border-radius: 6px; border: 1px solid #30360d; font-size: 13px; margin: 4px; display: inline-block; }
    .listing-box { background: #161b22; padding: 15px; border-radius: 8px; border-left: 5px solid #238636; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 15-COLUMN CRM SCHEMA ---
CRM_COLUMNS = [
    "Date / Timestamp", "Category", "Phase", "Block", "Plot No",
    "Size", "Plot Features", "Demand / Price", "Seller Type",
    "Seller / Dealer Name", "Contact No", "Office / Agency",
    "Deal Status", "Last Conversation / Notes", "Raw Listing"
]

# --- DHA WORKBOOK DATABASE DICTIONARY ---
DHA_PHASE_SHEETS = {
    "DHA Phase 1": "DHA Phase 1 Database",
    "DHA Phase 2": "DHA Phase 2 Database",
    "DHA Phase 3": "DHA Phase 3 Database",
    "DHA Phase 4": "DHA Phase 4 Database",
    "DHA Phase 5": "DHA Phase 5 Database",
    "DHA Phase 6": "DHA Phase 6 Database",
    "DHA Phase 7": "DHA Phase 7 Database",
    "DHA Phase 8 (Proper)": "DHA Phase 8 (Proper) Database",
    "DHA Phase 8 (Ivy Green / Sector Z)": "DHA Phase 8 (Ivy Green / Sector Z) Database",
    "DHA Phase 8 (Park View)": "DHA Phase 8 (Park View) Database",
    "DHA Phase 8 (Air Avenue / Sector AA)": "DHA Phase 8 (Air Avenue / Sector AA) Database",
    "DHA Phase 9 Prism": "DHA Phase 9 Prism Database",
    "DHA Phase 9 Town": "DHA Phase 9 Town Database",
    "DHA Phase 11 (Rahbar)": "DHA Phase 11 (Rahbar) Database",
    "DHA Phase 12 (EME Sector)": "DHA Phase 12 (EME) Database"
}

# --- NLP & REGEX PARSING ENGINE ---
def parse_raw_text(text):
    data = {}
    
    # 1. Timestamp
    data["Date / Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 2. Category
    if re.search(r'\b(rent|rental|to let|available for rent)\b', text, re.I):
        data["Category"] = "Rental"
    elif re.search(r'\b(req|required|need|wanted|buying|demand buy)\b', text, re.I):
        data["Category"] = "Buying"
    else:
        data["Category"] = "Selling"
        
    # 3. Phase Detection
    phase_match = None
    for phase_name in DHA_PHASE_SHEETS.keys():
        simple_name = phase_name.replace("DHA ", "").replace(" (Proper)", "").replace(" (EME Sector)", "")
        if re.search(r'\b' + re.escape(simple_name) + r'\b', text, re.I):
            phase_match = phase_name
            break
    data["Phase"] = phase_match if phase_match else "DHA Phase 6"
    
    # 4. Block Detection
    block_match = re.search(r'\b(?:block|sector)?\s*([a-z]{1,2}(?:-\d)?|cca\s*\d?|civic\s*centre|mb)\b', text, re.I)
    if block_match:
        data["Block"] = f"Block {block_match.group(1).upper().strip()}"
    else:
        data["Block"] = "Block A"
        
    # 5. Plot No
    plot_match = re.search(r'\b(?:plot|no|#)?\s*(\d{1,5})\b', text, re.I)
    data["Plot No"] = plot_match.group(1) if plot_match else "N/A"
    
    # 6. Size
    size_match = re.search(r'(\d+\s*(?:marla|kanal|sq\s*ft|sqft|sq\s*yards))', text, re.I)
    data["Size"] = size_match.group(1).title() if size_match else "1 Kanal"
    
    # 7. Features
    features = []
    if re.search(r'\bcorner\b', text, re.I): features.append("Corner")
    if re.search(r'\bpark\s*facing\b|\bfacing\s*park\b', text, re.I): features.append("Facing Park")
    if re.search(r'\bmain\s*boulevard\b|\bmb\b', text, re.I): features.append("Main Boulevard")
    if re.search(r'\b\d{2,3}\s*ft\s*road\b', text, re.I): features.append("Wide Road")
    data["Plot Features"] = ", ".join(features) if features else "General / Direct Approach"
    
    # 8. Demand / Price
    price_match = re.search(r'(\d+(?:\.\d+)?\s*(?:crore|cr|lac|lacs|lakh|k))\b', text, re.I)
    data["Demand / Price"] = price_match.group(1).upper() if price_match else "Demand on Call"
    
    # 9 & 10. Seller Type & Name
    data["Seller Type"] = "Direct Owner" if re.search(r'\b(direct|owner|self)\b', text, re.I) else "Authorized Dealer"
    data["Seller / Dealer Name"] = "Wali Muhammad Associates"
    
    # 11. Contact No
    contact_match = re.search(r'((?:\+92|0092|0)?\s*3\d{2}[\s-]?\d{7})', text)
    data["Contact No"] = contact_match.group(1).replace(" ", "").replace("-", "") if contact_match else "0300-0000000"
    
    # 12-15. Metadata
    data["Office / Agency"] = "Wali Muhammad Associates"
    data["Deal Status"] = "Available"
    data["Last Conversation / Notes"] = "Ingested from WhatsApp listing text"
    data["Raw Listing"] = text.strip()
    
    return data

# --- GOOGLE SHEETS CONNECTOR FUNCTION ---
def push_to_sheets(record):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        
        sheet_title = DHA_PHASE_SHEETS.get(record["Phase"], "DHA Phase 6 Database")
        workbook = client.open(sheet_title)
        
        tab_name = record["Block"]
        try:
            worksheet = workbook.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = workbook.add_worksheet(title=tab_name, rows="500", cols="20")
            worksheet.append_row(CRM_COLUMNS)
            
        row_data = [record.get(col, "") for col in CRM_COLUMNS]
        worksheet.append_row(row_data)
        return True, f"Successfully added to {sheet_title} ➔ {tab_name}"
    except Exception as e:
        return False, str(e)

# --- UI WORKFLOW ---
st.title("⚡ DHA Real Estate Smart Ingestion Dashboard")

tab1, tab2 = st.tabs(["📥 Single/Bulk Text Ingestion", "📊 Filter & Search Inventory"])

with tab1:
    st.subheader("WhatsApp / Dealer Listing Ingestion")
    raw_input = st.text_area("Paste Raw Listing / WhatsApp Message Here:", height=150, placeholder="Example: DHA Phase 6 Block C 1 Kanal Corner Plot 450 Demand 5.80 Cr Contact 03001234567")
    
    col_btn, col_info = st.columns([2, 4])
    with col_btn:
        process_btn = st.button("🚀 Process & Parse Listing", type="primary", use_container_width=True)
        
    if process_btn and raw_input:
        parsed_record = parse_raw_text(raw_input)
        st.session_state["last_parsed"] = parsed_record
        st.success("✅ Extracted 15 Standard CRM Fields Successfully!")
        
    if "last_parsed" in st.session_state:
        p = st.session_state["last_parsed"]
        st.markdown("### Extracted Preview")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Phase", value=p["Phase"], key="p_phase")
        c2.text_input("Block", value=p["Block"], key="p_block")
        c3.text_input("Plot No", value=p["Plot No"], key="p_plot")
        c4.text_input("Size", value=p["Size"], key="p_size")
        
        c5, c6, c7, c8 = st.columns(4)
        c5.text_input("Demand / Price", value=p["Demand / Price"], key="p_price")
        c6.text_input("Category", value=p["Category"], key="p_cat")
        c7.text_input("Contact", value=p["Contact No"], key="p_contact")
        c8.text_input("Deal Status", value=p["Deal Status"], key="p_status")
        
        col_push, col_wa = st.columns(2)
        with col_push:
            if st.button("💾 Push to Phase Google Sheet", use_container_width=True):
                with st.spinner("Connecting to Google Cloud Service Account..."):
                    success, msg = push_to_sheets(p)
                    if success:
                        st.success(msg)
                    else:
                        st.error(f"Sync failed: {msg}")
                        
        with col_wa:
            wa_text = f"*DHA Listing Update*\n*Phase:* {p['Phase']}\n*Block:* {p['Block']}\n*Plot:* {p['Plot No']} ({p['Size']})\n*Features:* {p['Plot Features']}\n*Price:* {p['Demand / Price']}\n*Contact:* {p['Contact No']}"
            encoded_url = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"
            st.markdown(f'<a href="{encoded_url}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">📲 Open in WhatsApp</button></a>', unsafe_allow_html=True)

with tab2:
    st.subheader("Cloud Sheet Database Explorer")
    selected_p = st.selectbox("Select DHA Phase:", list(DHA_PHASE_SHEETS.keys()))
    st.info(f"Target Sheet: **{DHA_PHASE_SHEETS[selected_p]}**")
