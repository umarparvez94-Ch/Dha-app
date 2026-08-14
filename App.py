import streamlit as st
import gspread
import re
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Smart Property Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Custom Stitch CSS — Light Blue & White Theme
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background-color: #F0F7FF;
        font-family: 'Inter', sans-serif;
    }

    /* ── Header Banner ── */
    .header-banner {
        background: linear-gradient(135deg, #1E88E5 0%, #42A5F5 50%, #90CAF9 100%);
        padding: 26px 30px;
        border-radius: 18px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 6px 24px rgba(30, 136, 229, 0.25);
        position: relative;
        overflow: hidden;
    }
    .header-banner::before {
        content: '';
        position: absolute;
        top: -40%;
        right: -10%;
        width: 260px;
        height: 260px;
        background: rgba(255,255,255,0.08);
        border-radius: 50%;
    }
    .header-title {
        font-size: 28px;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
        letter-spacing: -0.3px;
    }
    .office-badge {
        background-color: rgba(255,255,255,0.22);
        backdrop-filter: blur(6px);
        color: white;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        float: right;
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* ── Property Cards ── */
    .property-card {
        background: #FFFFFF;
        border: 1px solid #DBEAFE;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(30, 136, 229, 0.06);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .property-card:hover {
        box-shadow: 0 6px 20px rgba(30, 136, 229, 0.12);
        transform: translateY(-1px);
    }

    /* ── Badges ── */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 6px;
        letter-spacing: 0.2px;
    }
    .badge-selling { background-color: #FEE2E2; color: #DC2626; }
    .badge-buying  { background-color: #DCFCE7; color: #16A34A; }
    .badge-rental  { background-color: #DBEAFE; color: #1E88E5; }
    .badge-feature { background-color: #FFF8E1; color: #F59E0B; }

    /* ── Buttons ── */
    .stButton>button {
        background: linear-gradient(135deg, #1E88E5, #42A5F5) !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 10px 20px !important;
        box-shadow: 0 3px 10px rgba(30, 136, 229, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        box-shadow: 0 6px 18px rgba(30, 136, 229, 0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* ── WhatsApp Button ── */
    .wa-btn {
        display: inline-block;
        background: linear-gradient(135deg, #25D366, #20BD5A);
        color: white !important;
        padding: 10px 16px;
        border-radius: 10px;
        font-weight: 700;
        text-decoration: none;
        font-size: 13px;
        text-align: center;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 3px 10px rgba(37, 211, 102, 0.2);
        transition: all 0.2s ease;
    }
    .wa-btn:hover {
        box-shadow: 0 6px 18px rgba(37, 211, 102, 0.35);
        transform: translateY(-1px);
    }

    /* ── Streamlit Overrides ── */
    .stSelectbox label, .stTextInput label, .stTextArea label {
        color: #1565C0 !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #DBEAFE;
        border-radius: 12px;
        background: #FFFFFF;
    }
    hr {
        border-color: #DBEAFE !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Google Sheets Connection
@st.cache_resource
def get_google_workbook():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url)

try:
    workbook = get_google_workbook()
except Exception as e:
    st.error(f"⚠️ Google Sheet Connection Error: {e}")
    st.stop()

def append_to_block_sheet(workbook, block_name, row_data):
    tab_title = str(block_name).strip() if block_name and block_name != "N/A" else "General_Entries"
    try:
        worksheet = workbook.worksheet(tab_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=tab_title, rows=200, cols=10)
        worksheet.append_row(["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing Text"])
    worksheet.append_row(row_data)

if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# 4. Standardized Parser
def parse_property_text(text):
    text_upper = text.upper()
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"

    phase = "DHA Phase 6"
    p_match = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
    if p_match:
        val = p_match.group(1)
        phase = f"DHA Phase {val}"
    if "PRISM" in text_upper:
        phase = "DHA Phase 9 Prism"

    block = "Block M"
    b_match = re.search(r'(?:BLOCK|BLK)\s*[:.-]?\s*([A-Z]{1,2})', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(BLOCK|BLK|CCA)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    size = "1 Kanal"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    if s_match:
        size = f"{s_match.group(1)} {s_match.group(2)}"

    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Park Facing")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Boulevard")
    if "EXCESS" in text_upper: features.append("Excess Land")
    road_match = re.search(r'(\d{2,3})\s*(FT|FEET|ROAD)', text_upper)
    if road_match: features.append(f"{road_match.group(0)} Road")
    feature_str = ", ".join(features) if features else "Standard Layout"

    return category, phase, block, size, feature_str

def create_wa_link(row_dict):
    msg = f"""🏢 *{st.session_state['office_name']}*
📍 *DHA Property Update*
• *Phase:* {row_dict.get('Phase', 'N/A')}
• *Block:* {row_dict.get('Block', 'N/A')}
• *Size:* {row_dict.get('Size', 'N/A')}
• *Category:* {row_dict.get('Category', 'N/A')}
• *Features:* {row_dict.get('Features', 'Standard')}
📝 *Details:* {row_dict.get('Raw Listing Text', row_dict.get('Raw Listing', ''))}"""
    return f"https://wa.me/?text={urllib.parse.quote(msg)}"

# 5. UI Layout
st.markdown(f"""
    <div class="header-banner">
        <span class="office-badge">📍 {st.session_state['office_name']}</span>
        <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
        <div style="color: rgba(255,255,255,0.75); font-size: 13px; margin-top: 4px;">Standardized DHA Phases &amp; Block-Wise Ingestion Engine</div>
    </div>
""", unsafe_allow_html=True)

with st.expander("⚙️ Settings (Change Agency Name)"):
    new_office = st.text_input("Agency Name", value=st.session_state["office_name"])
    if st.button("Update"):
        st.session_state["office_name"] = new_office
        st.rerun()

st.markdown("### 🔍 Supreme Global Property Search")
search_query = st.text_input("Search anything", placeholder="e.g. DHA Phase 6 Block M Corner 1 Kanal, Main Boulevard...", label_visibility="collapsed")

st.markdown("---")

# Standardized DHA Phases List with DHA added to every phase
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
    selected_block = st.selectbox("🧱 Target Block Sheet", [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA", "Phase 9 Prism"])

st.markdown("---")

# 6. Ingestion Panel
st.subheader("📥 Add Property Listing")
tab_text, tab_camera = st.tabs(["📝 Text & File Entry", "📸 Camera Scanner"])

with tab_text:
    c_in1, c_in2 = st.columns([2, 1])
    with c_in1:
        source = st.selectbox("Source", ["WhatsApp Group", "Newspaper Classified", "Direct Client", "Facebook"])
        raw_text = st.text_area("Paste Listing Text", height=130, placeholder="DHA Phase 6 Block M 1 Kanal Corner for sale...")
        up_file = st.file_uploader("Upload .txt file", type=["txt"])
        if up_file: raw_text = str(up_file.read(), "utf-8")
    with c_in2:
        st.markdown("#### ⚡ Auto Detected")
        if raw_text.strip():
            cat, ph, blk, sz, feat = parse_property_text(raw_text)
            st.write(f"**Category:** `{cat}`")
            st.write(f"**Phase:** `{ph}`")
            st.write(f"**Block:** `{blk}`")
            st.write(f"**Size:** `{sz}`")
            st.write(f"**Features:** `{feat}`")

    if st.button("💾 Save Listing to Block Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, ph, blk, sz, feat = parse_property_text(raw_text)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                target_sheet = blk if blk != "N/A" else selected_block
                append_to_block_sheet(workbook, target_sheet, [now_str, source, cat, ph, target_sheet, sz, feat, raw_text])
                st.success(f"✅ Saved into Google Sheet Tab: [{target_sheet}]!")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")

with tab_camera:
    img = st.camera_input("Scan Ad / Business Card")
    if img: st.success("Photo captured!")

st.markdown("---")

# 7. 3-Sheet Inventory Tabs
st.subheader(f"📊 Live Inventory: [{selected_block}]")
try:
    try:
        data = workbook.worksheet(selected_block).get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        data = []

    if len(data) > 1:
        headers = ["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing Text"]
        df = pd.DataFrame(data[1:], columns=headers[:len(data[1])])
        if search_query:
            df = df[df["Raw Listing Text"].str.contains(search_query, case=False, na=False) |
                    df["Features"].str.contains(search_query, case=False, na=False)]

        ts, tb, tr = st.tabs(["🔴 Selling", "🟢 Buying", "🔵 Rental"])
        def display_listings(filt_df, badge_c):
            if filt_df.empty:
                st.info("No records in this category.")
                return
            for _, r in filt_df.iterrows():
                wa = create_wa_link(r.to_dict())
                c1, c2 = st.columns([4, 1.2])
                with c1:
                    st.markdown(f"""
                        <div class="property-card">
                            <span class="badge {badge_c}">{r.get('Category', '')}</span>
                            <span class="badge badge-feature">{r.get('Features', '')}</span>
                            <b>{r.get('Phase', '')} {r.get('Block', '')} — {r.get('Size', '')}</b>
                            <p style="margin: 6px 0 0 0; color:#475569; font-size:14px;">{r.get('Raw Listing Text', '')}</p>
                            <small style="color:#94A3B8;">{r.get('Timestamp', '')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="{wa}" target="_blank" class="wa-btn">📲 WhatsApp</a>', unsafe_allow_html=True)

        with ts: display_listings(df[df["Category"] == "Selling"] if "Category" in df.columns else df, "badge-selling")
        with tb: display_listings(df[df["Category"] == "Buying"] if "Category" in df.columns else df, "badge-buying")
        with tr: display_listings(df[df["Category"] == "Rental"] if "Category" in df.columns else df, "badge-rental")
    else:
        st.info(f"Tab [{selected_block}] is empty. Add entries above.")
except Exception as e:
    st.error(f"Load Error: {e}")
