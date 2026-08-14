import streamlit as st
import gspread
import re
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. Page Configuration (Google Stitch UI Standard)
st.set_page_config(
    page_title="DHA Smart Property Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Custom Stitch CSS Styling
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    /* Top Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 22px 26px;
        border-radius: 16px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
    }
    .header-title { font-size: 26px; font-weight: 800; margin: 0; color: #F8FAFC; letter-spacing: -0.5px; }
    .header-subtitle { color: #94A3B8; font-size: 13px; margin-top: 4px; }
    .office-badge {
        background-color: #10B981; color: white; padding: 5px 14px;
        border-radius: 20px; font-size: 13px; font-weight: 600; float: right;
    }
    
    /* Listing Cards */
    .property-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Custom Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 6px;
    }
    .badge-selling { background-color: #FEE2E2; color: #DC2626; }
    .badge-buying { background-color: #DCFCE7; color: #16A34A; }
    .badge-rental { background-color: #E0F2FE; color: #0284C7; }
    .badge-feature { background-color: #FEF3C7; color: #D97706; }
    
    /* Buttons */
    .stButton>button {
        background: #059669 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600 !important; border: none !important;
        height: 2.8rem !important;
    }
    .stButton>button:hover { background: #047857 !important; }
    .wa-btn {
        display: inline-block; background-color: #25D366; color: white !important;
        padding: 8px 14px; border-radius: 8px; font-weight: 700; text-decoration: none;
        font-size: 13px; text-align: center; width: 100%; box-sizing: border-box;
    }
    .wa-btn:hover { background-color: #1EBE5D; text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

# 3. Google Sheets Backend Connection
@st.cache_resource
def get_google_workbook():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url)

try:
    workbook = get_google_workbook()
except Exception as e:
    st.error(f"⚠️ Google Sheet Connection Failed: {e}")
    st.stop()

# Helper to save directly into dedicated block sheet tabs
def append_to_block_sheet(workbook, block_name, row_data):
    tab_title = str(block_name).strip() if block_name and block_name != "N/A" else "General_Entries"
    try:
        worksheet = workbook.worksheet(tab_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=tab_title, rows=200, cols=10)
        worksheet.append_row(["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing Text"])
    worksheet.append_row(row_data)

# Session State for Office Details
if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# 4. Standardized Parser Engine
def parse_property_text(text):
    text_upper = text.upper()
    
    # Category
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"

    # Standardized DHA Phase Detection
    phase = "DHA Phase 6"
    p_match = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
    if p_match:
        val = p_match.group(1)
        phase = f"DHA Phase {val}"
    if "PRISM" in text_upper:
        phase = "DHA Phase 9 Prism"

    # Block Detection
    block = "Block M"
    b_match = re.search(r'(?:BLOCK|BLK)\s*[:.-]?\s*([A-Z]{1,2})', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(BLOCK|BLK|CCA)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    # Size Detection
    size = "1 Kanal"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    if s_match:
        size = f"{s_match.group(1)} {s_match.group(2)}"

    # Attributes & Features
    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Park Facing")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Boulevard")
    if "EXCESS" in text_upper: features.append("Excess Land")
    road_match = re.search(r'(\d{2,3})\s*(FT|FEET|ROAD)', text_upper)
    if road_match: features.append(f"{road_match.group(0)} Road")
    feature_str = ", ".join(features) if features else "Standard Layout"

    return category, phase, block, size, feature_str

# WhatsApp Formatted Link Generator
def create_wa_link(row_dict):
    msg = f"""🏢 *{st.session_state['office_name']}*
📍 *DHA Property Update*
• *Phase:* {row_dict.get('Phase', 'N/A')}
• *Block:* {row_dict.get('Block', 'N/A')}
• *Size:* {row_dict.get('Size', 'N/A')}
• *Category:* {row_dict.get('Category', 'N/A')}
• *Features:* {row_dict.get('Features', 'Standard')}
📝 *Details:* {row_dict.get('Raw Listing Text', row_dict.get('Raw Listing', ''))}
---
Direct Deal Inquiry"""
    return f"https://wa.me/?text={urllib.parse.quote(msg)}"

# -------------------------------------------------------------
# 5. UI LAYOUT & NAVIGATION
# -------------------------------------------------------------

# Top Header
st.markdown(f"""
    <div class="header-banner">
        <span class="office-badge">📍 {st.session_state['office_name']}</span>
        <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
        <div class="header-subtitle">Standardized DHA Phases & Block-Wise Ingestion Engine</div>
    </div>
""", unsafe_allow_html=True)

# Agency Settings Expander
with st.expander("⚙️ Customize Agency Name & Settings"):
    new_office = st.text_input("Agency / Office Name", value=st.session_state["office_name"])
    if st.button("Update Agency Name"):
        st.session_state["office_name"] = new_office
        st.rerun()

# Supreme Multi-Feature Search Bar
st.markdown("### 🔍 Supreme Global Property Search")
search_query = st.text_input(
    "Search anything",
    placeholder="🔎 e.g. DHA Phase 6 Block M Corner 1 Kanal, Main Boulevard, Facing Park...",
    label_visibility="collapsed"
)

st.markdown("---")

# Standardized DHA Phase Dropdown List
dha_phases_list = [
    "DHA Phase 1", "DHA Phase 2", "DHA Phase 3", "DHA Phase 4",
    "DHA Phase 5", "DHA Phase 6", "DHA Phase 7", "DHA Phase 8",
    "DHA Phase 9 Prism", "DHA Phase 9 Town", "DHA Phase 10",
    "DHA Phase 11 (Rahwali)", "DHA Phase 12 (EME)", "DHA Phase 13"
]

col_city, col_phase, col_block = st.columns([1.2, 1.8, 1.8])
with col_city:
    selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])
with col_phase:
    selected_phase = st.selectbox("📍 DHA Phase", dha_phases_list)
with col_block:
    block_options = [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA", "Phase 9 Prism"]
    selected_block = st.selectbox("🧱 Target Block Sheet", block_options)

st.markdown("---")

# 6. DATA INGESTION PANEL (TEXT, FILE & LIVE CAMERA)
st.subheader("📥 Add Property Listing (Text / Camera / File OCR)")
tab_text, tab_camera = st.tabs(["📝 Text & File Ingestion", "📸 Live Camera Scanner"])

with tab_text:
    col_input, col_preview = st.columns([2, 1])
    with col_input:
        source = st.selectbox("📌 Data Source", ["WhatsApp Group", "Newspaper Classified", "Direct Client", "Facebook"])
        raw_text = st.text_area("📋 Paste Raw Property Text", height=140, placeholder="Example: DHA Phase 6 Block M 1 Kanal Corner Facing Park plot for sale demand 4.50 crore...")
        uploaded_file = st.file_uploader("Or Upload .txt File", type=["txt"])
        if uploaded_file and uploaded_file.type == "text/plain":
            raw_text = str(uploaded_file.read(), "utf-8")

    with col_preview:
        st.markdown("#### ⚡ Real-Time Auto Extraction")
        if raw_text.strip():
            cat, ph, blk, sz, feat = parse_property_text(raw_text)
            target_tab = blk if blk != "N/A" else selected_block
            
            st.write(f"**Category:** `{cat}`")
            st.write(f"**Phase:** `{ph}`")
            st.write(f"**Target Sheet/Block:** `{target_tab}`")
            st.write(f"**Size:** `{sz}`")
            st.write(f"**Features:** `{feat}`")
        else:
            st.info("Paste or scan any listing to preview auto-extracted details...")

    if st.button("💾 Save Listing to Block Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, ph, blk, sz, feat = parse_property_text(raw_text)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                target_sheet = blk if blk != "N/A" else selected_block
                
                # Append row directly to dedicated block tab
                row_payload = [now_str, source, cat, ph, target_sheet, sz, feat, raw_text]
                append_to_block_sheet(workbook, target_sheet, row_payload)
                
                st.success(f"✅ Record saved into Google Sheet Tab: **[{target_sheet}]**!")
                st.balloons()
            except Exception as e:
                st.error(f"Error saving entry: {e}")
        else:
            st.warning("Please enter listing text first.")

with tab_camera:
    img_captured = st.camera_input("Take Photo of Newspaper / Visiting Card")
    if img_captured:
        st.success("📸 Photo captured! Ready for OCR parsing.")

st.markdown("---")

# 7. LIVE CATEGORIZED 3-SHEET VIEW & WHATSAPP ACTIONS
st.subheader(f"📊 Live Inventory for [{selected_block}]")

try:
    try:
        current_sheet = workbook.worksheet(selected_block)
        data = current_sheet.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        data = []

    if len(data) > 1:
        headers = ["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing Text"]
        df = pd.DataFrame(data[1:], columns=headers[:len(data[1])])
        
        # Apply Search Filter
        if search_query:
            df = df[df["Raw Listing Text"].str.contains(search_query, case=False, na=False) |
                    df["Features"].str.contains(search_query, case=False, na=False) |
                    df["Size"].str.contains(search_query, case=False, na=False)]

        tab_sell, tab_buy, tab_rent = st.tabs(["🔴 Available Inventory (Selling)", "🟢 Buyer Requirements (Buying)", "🔵 Rental & Leases"])

        def render_cards(filtered_df, cat_badge_class):
            if filtered_df.empty:
                st.info("No matching records found in this category.")
                return
            for _, r in filtered_df.iterrows():
                wa_url = create_wa_link(r.to_dict())
                c1, c2 = st.columns([4, 1.2])
                with c1:
                    st.markdown(f"""
                        <div class="property-card">
                            <span class="badge {cat_badge_class}">{r.get('Category', 'N/A')}</span>
                            <span class="badge badge-feature">{r.get('Features', 'Standard')}</span>
                            <span style="font-weight:700; color:#0F172A; margin-left:8px;">{r.get('Phase', '')} {r.get('Block', '')} — {r.get('Size', '')}</span>
                            <p style="margin: 8px 0 0 0; color: #475569; font-size: 14px;">{r.get('Raw Listing Text', '')}</p>
                            <small style="color:#94A3B8;">Source: {r.get('Source', '')} | Added: {r.get('Timestamp', '')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="{wa_url}" target="_blank" class="wa-btn">📲 Share to WhatsApp</a>', unsafe_allow_html=True)

        with tab_sell:
            render_cards(df[df["Category"] == "Selling"] if "Category" in df.columns else df, "badge-selling")
            
        with tab_buy:
            render_cards(df[df["Category"] == "Buying"] if "Category" in df.columns else df, "badge-buying")
            
        with tab_rent:
            render_cards(df[df["Category"] == "Rental"] if "Category" in df.columns else df, "badge-rental")
    else:
        st.info(f"Worksheet tab **[{selected_block}]** is ready. Add a new listing above to create/populate data!")

except Exception as e:
    st.error(f"Data Load Error: {e}")
