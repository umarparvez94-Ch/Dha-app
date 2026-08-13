import streamlit as st
import gspread
import re
import pandas as pd
from datetime import datetime

# 1. Page & UI Configuration (Stitch Design System)
st.set_page_config(
    page_title="DHA Smart Property Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stitch Custom CSS Injection
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
    .card-box {
        background: white; border-radius: 12px; padding: 16px;
        border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stButton>button {
        background: #059669 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600 !important; border: none !important;
    }
    .stButton>button:hover { background: #047857 !important; }
    </style>
""", unsafe_allow_html=True)

# 2. Google Sheet Secure Connection
@st.cache_resource
def get_google_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url).sheet1

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"Google Sheet Connection Failed: {e}")
    st.stop()

# Session State for Office Name
if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# 3. Smart Parsing Engine
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

# 4. Header & Office Name Modal
st.markdown(f"""
    <div class="header-banner">
        <span class="office-badge">📍 {st.session_state['office_name']}</span>
        <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
        <p style="margin: 5px 0 0 0; color: #94A3B8; font-size: 13px;">Advanced AI Property Categorization & Search Dashboard</p>
    </div>
""", unsafe_allow_html=True)

# Office Name Setup Expander
with st.expander("⚙️ Change Office / Agency Name"):
    new_office = st.text_input("Enter Office Name", value=st.session_state["office_name"])
    if st.button("Update Office Name"):
        st.session_state["office_name"] = new_office
        st.rerun()

# 5. Supreme Multi-Feature Search Bar
st.subheader("🔍 Supreme Ultra-Smart Search Engine")
search_query = st.text_input("🔎 Search by Phase, Block, Size, Feature (Corner, Park, Main Road), or Dealer Phone", placeholder="e.g. Phase 6 Block M Corner 1 Kanal")

# 6. Location Navigation Hierarchy
st.markdown("---")
c_col1, c_col2, c_col3 = st.columns([1, 2, 2])
with c_col1:
    selected_city = st.selectbox("🏙️ Select City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])
with c_col2:
    selected_phase = st.selectbox("📍 Select Phase", [f"Phase {i}" for i in range(1, 14)] + ["DHA EME", "DHA Rahwali"])
with c_col3:
    blocks = [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA", "Phase 9 Prism"]
    selected_block = st.selectbox("🧱 Select Block", blocks)

# 7. Data Input Panel (Text, Camera & File Upload)
st.markdown("---")
st.subheader("📥 Add Property Listing (Text / Camera / File OCR)")
tab_text, tab_camera = st.tabs(["📝 Text & File Entry", "📸 Camera Scan"])

with tab_text:
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        source = st.selectbox("Data Source", ["WhatsApp Group", "Newspaper Advert", "Direct Client", "Facebook"])
        raw_text = st.text_area("Paste Property Listing Text", height=150, placeholder="Example: DHA Phase 6 Block M 1 Kanal Corner plot for sale demand 4.5 crore...")
        uploaded_file = st.file_uploader("Or Upload Image / Text File", type=["txt", "jpg", "jpeg", "png"])
        if uploaded_file and uploaded_file.type == "text/plain":
            raw_text = str(uploaded_file.read(), "utf-8")
            
    with col_in2:
        st.markdown("### 🤖 Auto Extraction")
        if raw_text.strip():
            cat, ph, blk, sz, feat = parse_property_text(raw_text)
            st.write(f"**Category:** `{cat}`")
            st.write(f"**Phase:** `{ph}`")
            st.write(f"**Block:** `{blk}`")
            st.write(f"**Size:** `{sz}`")
            st.write(f"**Features:** `{feat}`")

    if st.button("💾 Save Listing to Engine", use_container_width=True):
        if raw_text.strip():
            try:
                cat, ph, blk, sz, feat = parse_property_text(raw_text)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                sheet.append_row([now_str, source, cat, ph, blk, sz, feat, raw_text])
                st.success("✅ Property successfully categorized and saved to Google Sheet!")
                st.balloons()
            except Exception as e:
                st.error(f"Save Error: {e}")

with tab_camera:
    img_capture = st.camera_input("Take Photo of Newspaper Advert / Card")
    if img_capture:
        st.info("📸 Photo captured successfully! Text processing ready.")

# 8. Categorized 3-Sheet Database View
st.markdown("---")
st.subheader(f"📊 Live Inventory: {selected_phase} - {selected_block}")

try:
    data = sheet.get_all_values()
    if len(data) > 0:
        cols = ["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing"]
        df = pd.DataFrame(data[1:], columns=cols[:len(data[1])]) if len(data) > 1 else pd.DataFrame(columns=cols)
        
        # Search Filtering
        if search_query:
            df = df[df["Raw Listing"].str.contains(search_query, case=False, na=False) | 
                    df["Features"].str.contains(search_query, case=False, na=False) |
                    df["Phase"].str.contains(search_query, case=False, na=False)]

        # 3 Sheets Tabs
        sheet_selling, sheet_buying, sheet_rent = st.tabs(["🔴 Selling / Inventory", "🟢 Buying / Requirements", "🔵 Rental / Leases"])
        
        with sheet_selling:
            df_sell = df[df["Category"] == "Selling"] if "Category" in df.columns else df
            st.dataframe(df_sell, use_container_width=True)
            
        with sheet_buying:
            df_buy = df[df["Category"] == "Buying"] if "Category" in df.columns else df
            st.dataframe(df_buy, use_container_width=True)
            
        with sheet_rent:
            df_rent = df[df["Category"] == "Rental"] if "Category" in df.columns else df
            st.dataframe(df_rent, use_container_width=True)

except Exception as e:
    st.info("Awaiting new inventory entries...")
