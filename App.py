import streamlit as st
import gspread
import re
import pandas as pd
from datetime import datetime

# 1. Page Configuration (Stitch UI Theme)
st.set_page_config(
    page_title="DHA Smart Property Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    .header-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 20px 24px; border-radius: 16px; color: white; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .header-title { font-size: 26px; font-weight: 700; margin: 0; color: #F8FAFC; }
    .office-badge {
        background-color: #10B981; color: white; padding: 4px 12px;
        border-radius: 20px; font-size: 13px; font-weight: 600; float: right;
    }
    .stButton>button {
        background: #059669 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600 !important; border: none !important;
    }
    .stButton>button:hover { background: #047857 !important; }
    </style>
""", unsafe_allow_html=True)

# 2. Google Workbook Connection
@st.cache_resource
def get_google_workbook():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url)

try:
    workbook = get_google_workbook()
except Exception as e:
    st.error(f"Google Sheet Connection Failed: {e}")
    st.stop()

# Helper function to append row to specific block tab
def append_to_block_sheet(workbook, block_name, row_data):
    # Sanitize sheet title (max 100 chars, clean string)
    tab_title = str(block_name).strip() if block_name and block_name != "N/A" else "General_Entries"
    
    try:
        # Try fetching existing worksheet by block name
        worksheet = workbook.worksheet(tab_title)
    except gspread.exceptions.WorksheetNotFound:
        # Create a new tab for this block if it doesn't exist
        worksheet = workbook.add_worksheet(title=tab_title, rows=100, cols=10)
        # Add Header row to the new sheet
        worksheet.append_row(["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing Text"])
        
    worksheet.append_row(row_data)

# Session State
if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# 3. Smart Extraction Engine
def parse_property_text(text):
    text_upper = text.upper()
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"

    phase = "N/A"
    p_match = re.search(r'(PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
    if p_match:
        phase = f"Phase {p_match.group(2)}"

    block = "N/A"
    b_match = re.search(r'(?:BLOCK|BLK)\s*[:.-]?\s*([A-Z]{1,2})', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(BLOCK|BLK|CCA)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    size = "N/A"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    if s_match:
        size = f"{s_match.group(1)} {s_match.group(2)}"

    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Park Facing")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Road")
    if "EXCESS" in text_upper: features.append("Excess Land")
    feature_str = ", ".join(features) if features else "Standard"

    return category, phase, block, size, feature_str

# 4. Header UI
st.markdown(f"""
    <div class="header-banner">
        <span class="office-badge">📍 {st.session_state['office_name']}</span>
        <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
        <p style="margin: 5px 0 0 0; color: #94A3B8; font-size: 13px;">Auto-Categorized Block-Wise Sheet Engine</p>
    </div>
""", unsafe_allow_html=True)

with st.expander("⚙️ Change Office / Agency Name"):
    new_office = st.text_input("Enter Office Name", value=st.session_state["office_name"])
    if st.button("Update Office Name"):
        st.session_state["office_name"] = new_office
        st.rerun()

# 5. Search Bar
st.subheader("🔍 Search Property Records")
search_query = st.text_input("🔎 Search across all block sheets by keyword, size, or feature")

# 6. Location Navigation Hierarchy
st.markdown("---")
c_col1, c_col2, c_col3 = st.columns([1, 2, 2])
with c_col1:
    selected_city = st.selectbox("🏙️ Select City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])
with c_col2:
    selected_phase = st.selectbox("📍 Select Phase", [f"Phase {i}" for i in range(1, 14)] + ["DHA EME", "DHA Rahwali"])
with c_col3:
    blocks = [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA", "Phase 9 Prism"]
    selected_block = st.selectbox("🧱 Select Target Block Sheet", blocks)

# 7. Input Entry (Block-Wise Save Engine)
st.markdown("---")
st.subheader("📥 Add New Listing (Auto-Saves to Block Tab)")

col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    source = st.selectbox("Data Source", ["WhatsApp Group", "Newspaper Advert", "Direct Client", "Facebook"])
    raw_text = st.text_area("Paste Property Listing Text", height=150, placeholder="Example: DHA Phase 6 Block M 1 Kanal Corner plot for sale demand 4.5 crore...")
    
with col_in2:
    st.markdown("### 🤖 Detected Metadata")
    if raw_text.strip():
        cat, ph, blk, sz, feat = parse_property_text(raw_text)
        
        # Override detected block if user specifically selected a block from dropdown
        target_block = blk if blk != "N/A" else selected_block
        
        st.write(f"**Category:** `{cat}`")
        st.write(f"**Phase:** `{ph}`")
        st.write(f"**Target Sheet/Block:** `{target_block}`")
        st.write(f"**Size:** `{sz}`")
        st.write(f"**Features:** `{feat}`")

if st.button("💾 Save to Block Sheet", use_container_width=True):
    if raw_text.strip():
        try:
            cat, ph, blk, sz, feat = parse_property_text(raw_text)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Determine sheet tab name
            target_sheet_name = blk if blk != "N/A" else selected_block
            
            # Save into dedicated Block Sheet Tab
            row_payload = [now_str, source, cat, ph, target_sheet_name, sz, feat, raw_text]
            append_to_block_sheet(workbook, target_sheet_name, row_payload)
            
            st.success(f"✅ Data saved directly into Google Sheet Tab: **[{target_sheet_name}]**!")
            st.balloons()
        except Exception as e:
            st.error(f"Block Save Error: {e}")

# 8. View Selected Block Sheet Tabs
st.markdown("---")
st.subheader(f"📊 Viewing Sheet Tab: [{selected_block}]")

try:
    # Try fetching selected block sheet
    try:
        current_worksheet = workbook.worksheet(selected_block)
        data = current_worksheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        data = []

    if len(data) > 1:
        cols = ["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing"]
        df = pd.DataFrame(data[1:], columns=cols[:len(data[1])])
        
        if search_query:
            df = df[df["Raw Listing"].str.contains(search_query, case=False, na=False) |
                    df["Features"].str.contains(search_query, case=False, na=False)]

        tab_sell, tab_buy, tab_rent = st.tabs(["🔴 Selling / Inventory", "🟢 Buying / Requirements", "🔵 Rental"])
        
        with tab_sell:
            st.dataframe(df[df["Category"] == "Selling"] if "Category" in df.columns else df, use_container_width=True)
            
        with tab_buy:
            st.dataframe(df[df["Category"] == "Buying"] if "Category" in df.columns else df, use_container_width=True)
            
        with tab_rent:
            st.dataframe(df[df["Category"] == "Rental"] if "Category" in df.columns else df, use_container_width=True)
    else:
        st.info(f"No entries found yet in Google Sheet tab: **{selected_block}**. Add a new listing above to create this sheet automatically!")

except Exception as e:
    st.error(f"Error loading block data: {e}")
