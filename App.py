import streamlit as st
import gspread
import re
import urllib.parse
import pandas as pd
from datetime import datetime

<<<<<<< HEAD
# ═══════════════════════════════════════════════════════════════
# 1. PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════
=======
# 1. Page Configuration (Google Stitch UI Standard)
>>>>>>> a52e46999e0e7f6f00280fa44aeb732073571e70
st.set_page_config(
    page_title="DHA Smart Property Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

<<<<<<< HEAD
# ═══════════════════════════════════════════════════════════════
# 2. STITCH CSS — LIGHT BLUE & WHITE THEME
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Global ── */
.stApp {
    background-color: #F0F7FF;
    font-family: 'Inter', sans-serif;
}

/* ── Header Banner ── */
.header-banner {
    background: linear-gradient(135deg, #1565C0 0%, #1E88E5 40%, #42A5F5 70%, #90CAF9 100%);
    padding: 28px 32px;
    border-radius: 20px;
    color: white;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(21, 101, 192, 0.3);
    position: relative;
    overflow: hidden;
}
.header-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -8%;
    width: 300px;
    height: 300px;
    background: rgba(255,255,255,0.07);
    border-radius: 50%;
}
.header-banner::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: 10%;
    width: 180px;
    height: 180px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
}
.header-title {
    font-size: 30px;
    font-weight: 800;
    margin: 0;
    color: #FFFFFF;
    letter-spacing: -0.4px;
}
.header-sub {
    color: rgba(255,255,255,0.8);
    font-size: 14px;
    margin-top: 6px;
    font-weight: 500;
}
.office-badge {
    background: rgba(255,255,255,0.2);
    backdrop-filter: blur(8px);
    color: white;
    padding: 7px 18px;
    border-radius: 24px;
    font-size: 13px;
    font-weight: 600;
    float: right;
    border: 1px solid rgba(255,255,255,0.25);
}

/* ── Section Headers ── */
.section-header {
    background: #FFFFFF;
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    padding: 14px 20px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 2px 8px rgba(30, 136, 229, 0.05);
}
.section-header h3 {
    margin: 0;
    font-size: 17px;
    font-weight: 700;
    color: #1565C0;
}

/* ── Active Tab Indicator ── */
.active-tab-indicator {
    background: linear-gradient(135deg, #E3F2FD, #BBDEFB);
    border: 1px solid #90CAF9;
    border-radius: 12px;
    padding: 12px 18px;
    margin-bottom: 14px;
    font-size: 14px;
    font-weight: 600;
    color: #1565C0;
}

/* ── Property Cards ── */
.property-card {
    background: #FFFFFF;
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 2px 10px rgba(30, 136, 229, 0.06);
    transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.property-card:hover {
    box-shadow: 0 8px 28px rgba(30, 136, 229, 0.14);
    transform: translateY(-2px);
}

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    margin-right: 6px;
    letter-spacing: 0.3px;
}
.badge-selling { background-color: #FEE2E2; color: #DC2626; }
.badge-buying  { background-color: #DCFCE7; color: #16A34A; }
.badge-rental  { background-color: #DBEAFE; color: #1E88E5; }
.badge-feature { background-color: #FFF8E1; color: #F59E0B; }
.badge-phase   { background-color: #E8EAF6; color: #3949AB; }

/* ── Buttons ── */
.stButton>button {
    background: linear-gradient(135deg, #1565C0, #1E88E5, #42A5F5) !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 10px 22px !important;
    box-shadow: 0 4px 14px rgba(21, 101, 192, 0.25) !important;
    transition: all 0.25s ease !important;
    letter-spacing: 0.3px !important;
}
.stButton>button:hover {
    box-shadow: 0 8px 24px rgba(21, 101, 192, 0.4) !important;
    transform: translateY(-2px) !important;
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
    box-shadow: 0 4px 12px rgba(37, 211, 102, 0.2);
    transition: all 0.25s ease;
}
.wa-btn:hover {
    box-shadow: 0 8px 24px rgba(37, 211, 102, 0.4);
    transform: translateY(-2px);
}

/* ── Stats Cards ── */
.stat-card {
    background: #FFFFFF;
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    padding: 16px 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(30, 136, 229, 0.06);
}
.stat-card .stat-num {
    font-size: 28px;
    font-weight: 800;
    color: #1565C0;
}
.stat-card .stat-label {
    font-size: 12px;
    font-weight: 600;
    color: #64B5F6;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-top: 4px;
}

/* ── Streamlit Overrides ── */
.stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label {
    color: #1565C0 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #FFFFFF;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #DBEAFE;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}
div[data-testid="stExpander"] {
    border: 1px solid #DBEAFE;
    border-radius: 14px;
    background: #FFFFFF;
    box-shadow: 0 2px 8px rgba(30, 136, 229, 0.04);
}
hr {
    border-color: #DBEAFE !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 3. STANDARDIZED DHA PHASES & BLOCK DEFINITIONS
# ═══════════════════════════════════════════════════════════════
DHA_PHASES = [
    "DHA Phase 1", "DHA Phase 2", "DHA Phase 3", "DHA Phase 4",
    "DHA Phase 5", "DHA Phase 6", "DHA Phase 7", "DHA Phase 8",
    "DHA Phase 9 Prism", "DHA Phase 9 Town", "DHA Phase 10",
    "DHA Phase 11 (Rahwali)", "DHA Phase 12 (EME)", "DHA Phase 13"
]

# Each phase has its own block list
PHASE_BLOCKS = {
    "DHA Phase 1":  [f"Block {chr(i)}" for i in range(65, 75)] + ["Block CCA"],     # A-J + CCA
    "DHA Phase 2":  [f"Block {chr(i)}" for i in range(65, 82)] + ["Block CCA"],     # A-Q + CCA
    "DHA Phase 3":  [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA", "Block XX"], # A-Z
    "DHA Phase 4":  [f"Block {chr(i)}" for i in range(65, 73)] + ["Block CCA", "Block EE"], # A-H
    "DHA Phase 5":  [f"Block {chr(i)}" for i in range(65, 77)] + ["Block CCA"],     # A-L
    "DHA Phase 6":  [f"Block {chr(i)}" for i in range(65, 82)] + ["Block CCA"],     # A-Q
    "DHA Phase 7":  [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA"],     # A-Z
    "DHA Phase 8":  [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA", "Block Air Avenue"],
    "DHA Phase 9 Prism":  [f"Block {chr(i)}" for i in range(65, 75)],               # A-J
    "DHA Phase 9 Town":   [f"Block {chr(i)}" for i in range(65, 70)],               # A-E
    "DHA Phase 10": [f"Block {chr(i)}" for i in range(65, 75)],                     # A-J
    "DHA Phase 11 (Rahwali)": [f"Sector {i}" for i in range(1, 6)] + [f"Block {chr(i)}" for i in range(65, 70)],
    "DHA Phase 12 (EME)": [f"Block {chr(i)}" for i in range(65, 77)],              # A-L
    "DHA Phase 13": [f"Block {chr(i)}" for i in range(65, 70)],                     # A-E
}

# Default blocks for unknown phases
DEFAULT_BLOCKS = [f"Block {chr(i)}" for i in range(65, 91)] + ["Block CCA"]

def get_phase_short(phase_name):
    """Create a short phase label for Google Sheet tab names (max 30 chars)."""
    short = phase_name.replace("DHA Phase ", "Ph").replace(" (Rahwali)", "-R").replace(" (EME)", "-E")
    return short

def get_sheet_tab_name(phase, block):
    """Create a unique Google Sheet tab name: 'Ph6 - Block M' (max 100 chars for Sheets API)."""
    short_phase = get_phase_short(phase)
    tab_name = f"{short_phase} - {block}"
    return tab_name[:100]

# ═══════════════════════════════════════════════════════════════
# 4. GOOGLE SHEETS CONNECTION
# ═══════════════════════════════════════════════════════════════
SHEET_HEADERS = ["Timestamp", "Source", "Category", "Phase", "Block", "Size", "Features", "Raw Listing Text"]

=======
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
    
    /* Badges */
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
    .badge-type { background-color: #EDE9FE; color: #6D28D9; }
    .badge-price { background-color: #ECFDF5; color: #059669; font-weight: 800; }
    
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
>>>>>>> a52e46999e0e7f6f00280fa44aeb732073571e70
@st.cache_resource
def get_google_workbook():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url)

try:
    workbook = get_google_workbook()
except Exception as e:
<<<<<<< HEAD
    st.error(f"Google Sheet Connection Error: {e}")
    st.stop()

def save_to_phase_block_sheet(workbook, phase, block, row_data):
    """Route data to a Phase+Block specific tab in Google Sheets."""
    tab_title = get_sheet_tab_name(phase, block)
    try:
        worksheet = workbook.worksheet(tab_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=tab_title, rows=500, cols=10)
        worksheet.append_row(SHEET_HEADERS)
    worksheet.append_row(row_data)
    return tab_title

def load_phase_block_data(workbook, phase, block):
    """Load data from a Phase+Block specific tab."""
    tab_title = get_sheet_tab_name(phase, block)
    try:
        data = workbook.worksheet(tab_title).get_all_values()
        return data, tab_title
    except gspread.exceptions.WorksheetNotFound:
        return [], tab_title

# ═══════════════════════════════════════════════════════════════
# 5. SESSION STATE
# ═══════════════════════════════════════════════════════════════
if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# ═══════════════════════════════════════════════════════════════
# 6. STANDARDIZED PARSER
# ═══════════════════════════════════════════════════════════════
def parse_property_text(text):
    text_upper = text.upper()

    # Category Detection
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"

    # Phase Detection
    phase = "DHA Phase 6"
    if "TOWN" in text_upper and "9" in text_upper:
        phase = "DHA Phase 9 Town"
    elif "PRISM" in text_upper:
        phase = "DHA Phase 9 Prism"
    elif "RAHWALI" in text_upper or ("11" in text_upper and "RAHWALI" in text_upper):
        phase = "DHA Phase 11 (Rahwali)"
    elif "EME" in text_upper:
        phase = "DHA Phase 12 (EME)"
    else:
        p_match = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2})', text_upper)
        if p_match:
            phase = f"DHA Phase {p_match.group(1)}"

    # Block Detection
    block = "Block M"
    b_match = re.search(r'(?:BLOCK|BLK)\s*[:.-]?\s*([A-Z]{1,3})', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    else:
        sector_match = re.search(r'SECTOR\s*(\d{1,2})', text_upper)
        if sector_match:
            block = f"Sector {sector_match.group(1)}"

    # Size Detection
    size = "1 Kanal"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    if s_match:
        size = f"{s_match.group(1)} {s_match.group(2).title()}"

    # Feature Detection
    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Park Facing")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Boulevard")
    if "EXCESS" in text_upper: features.append("Excess Land")
    if "POSSESSION" in text_upper: features.append("Possession")
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
📝 *Details:* {row_dict.get('Raw Listing Text', '')}"""
    return f"https://wa.me/?text={urllib.parse.quote(msg)}"

# ═══════════════════════════════════════════════════════════════
# 7. UI — HEADER BANNER
# ═══════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="header-banner">
    <span class="office-badge">📍 {st.session_state['office_name']}</span>
    <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
    <div class="header-sub">Phase-wise &amp; Block-wise Google Sheets Routing | Light Blue Stitch UI</div>
</div>
""", unsafe_allow_html=True)

# ── Settings Expander ──
with st.expander("⚙️ Agency Settings"):
    new_office = st.text_input("Agency Name", value=st.session_state["office_name"])
    if st.button("💾 Update Agency Name"):
        st.session_state["office_name"] = new_office
        st.rerun()

# ── Search Bar ──
st.markdown("### 🔍 Supreme Global Property Search")
search_query = st.text_input("Search properties...", placeholder="e.g. DHA Phase 6 Block M Corner 1 Kanal, Main Boulevard...", label_visibility="collapsed")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# 8. PHASE + BLOCK SELECTORS (DYNAMIC)
# ═══════════════════════════════════════════════════════════════
col_city, col_phase, col_block, col_size = st.columns([1, 1.5, 1.5, 1])

with col_city:
    selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])

with col_phase:
    selected_phase = st.selectbox("📍 DHA Phase", DHA_PHASES, index=5)

with col_block:
    # Dynamic block list based on selected phase
    blocks_for_phase = PHASE_BLOCKS.get(selected_phase, DEFAULT_BLOCKS)
    selected_block = st.selectbox(f"🧱 Block List ({selected_phase})", blocks_for_phase)

with col_size:
    selected_size_filter = st.selectbox("📏 Size Filter", ["All Sizes", "5 Marla", "7 Marla", "8 Marla", "10 Marla", "1 Kanal", "2 Kanal"])

# Show active routing target
tab_name = get_sheet_tab_name(selected_phase, selected_block)
st.markdown(f"""
<div class="active-tab-indicator">
    📊 Active Google Sheet Tab: <strong>{tab_name}</strong> &nbsp;|&nbsp; 🏙️ {selected_city}
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# 9. INGESTION PANEL
# ═══════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="section-header">
    <h3>📥 Add Property Listing ({selected_phase} — {selected_block})</h3>
</div>
""", unsafe_allow_html=True)

=======
    st.error(f"⚠️ Google Sheet Connection Failed: {e}")
    st.stop()

# Helper to save into Phase-specific Worksheet Tab
def append_to_phase_sheet(workbook, phase_tab_name, row_data):
    clean_tab_title = str(phase_tab_name).strip() if phase_tab_name else "DHA Phase 1"
    try:
        worksheet = workbook.worksheet(clean_tab_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=clean_tab_title, rows=300, cols=12)
        worksheet.append_row(["Timestamp", "Source", "Category", "Phase", "Block", "Property Type", "Size", "Demand / Price", "Phone Number", "Features", "Raw Listing Text"])
    worksheet.append_row(row_data)

# Session State for Office Details
if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# -------------------------------------------------------------
# 4. MASTER DHA LAHORE PHASE & BLOCK MAP CATALOG (OFFICIAL MAPS)
# -------------------------------------------------------------
DHA_PHASE_BLOCK_CATALOG = {
    "DHA Phase 1": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal"],
            "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["1 Kanal"],
            "Block J": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block K": ["1 Kanal", "2 Kanal"],
            "Block L": ["1 Kanal"],
            "Block M": ["1 Kanal"],
            "Block N": ["1 Kanal"],
            "Block P": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Block F (Commercial Market)": ["4 Marla", "7 Marla", "8 Marla"],
            "Block G (Main Commercial)": ["4 Marla", "8 Marla"],
            "Block H (Commercial & Stadium)": ["4 Marla", "8 Marla"],
            "Block J (Club Commercial)": ["4 Marla", "6 Marla"],
            "Block M (Commercial)": ["4 Marla", "8 Marla"],
            "Sector Shops (Local Commercial)": ["2 Marla", "3 Marla"]
        }
    },
    "DHA Phase 2": {
        "residential": {
            "Block Q": ["1 Kanal", "2 Kanal"],
            "Block R": ["1 Kanal", "2 Kanal"],
            "Block S": ["1 Kanal"],
            "Block T": ["10 Marla", "1 Kanal"],
            "Block U": ["10 Marla", "1 Kanal"],
            "Block V": ["1 Kanal", "2 Kanal"]
        },
        "commercial": {
            "Commercial CCA (Central Commercial)": ["4 Marla", "8 Marla"],
            "Block R Commercial Market": ["4 Marla", "6 Marla"],
            "Block T Commercial Market": ["4 Marla", "5 Marla"],
            "Sector Shops Phase 2": ["2 Marla"]
        }
    },
    "DHA Phase 3": {
        "residential": {
            "Block W": ["1 Kanal", "2 Kanal"],
            "Block X": ["1 Kanal", "2 Kanal"],
            "Block Y": ["10 Marla", "1 Kanal", "2 Kanal"],
            "Block Z": ["1 Kanal", "2 Kanal"],
            "Block XX": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Y Block Main Commercial (Central Hub)": ["4 Marla", "8 Marla", "16 Marla"],
            "Z Block Commercial Market": ["4 Marla", "8 Marla"],
            "W Block Commercial": ["4 Marla", "6 Marla"],
            "Sector Shops Phase 3": ["2 Marla"]
        }
    },
    "DHA Phase 4": {
        "residential": {
            "Block AA": ["1 Kanal", "2 Kanal"],
            "Block BB": ["1 Kanal", "2 Kanal"],
            "Block CC": ["10 Marla", "1 Kanal"],
            "Block DD": ["1 Kanal"],
            "Block EE": ["10 Marla", "1 Kanal"],
            "Block FF": ["10 Marla", "1 Kanal"],
            "Block GG": ["10 Marla", "1 Kanal"],
            "Block JJ": ["10 Marla", "1 Kanal"],
            "Block KK": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "CCA 1 Commercial": ["4 Marla", "8 Marla"],
            "CCA 2 Commercial": ["4 Marla", "8 Marla"],
            "Block DD Commercial": ["4 Marla", "6 Marla"],
            "Sector Shops Phase 4": ["2 Marla"]
        }
    },
    "DHA Phase 5": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["10 Marla", "1 Kanal", "2 Kanal"],
            "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["10 Marla", "1 Kanal"],
            "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"],
            "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"],
            "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"],
            "Block M": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "CCA 1 Commercial (Main Market)": ["4 Marla", "8 Marla"],
            "CCA 2 Commercial (Civic Zone)": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 5": ["2 Marla"]
        }
    },
    "DHA Phase 6": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal", "2 Kanal"],
            "Block D": ["10 Marla", "1 Kanal", "2 Kanal"],
            "Block E": ["1 Kanal"],
            "Block F": ["1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"],
            "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"],
            "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"],
            "Block M": ["1 Kanal", "2 Kanal"],
            "Block N": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Main Boulevard (MB) Commercial": ["4 Marla", "8 Marla", "16 Marla"],
            "CCA 1 Commercial Hub": ["4 Marla", "8 Marla"],
            "CCA 2 Commercial Hub": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 6": ["2 Marla"]
        }
    },
    "DHA Phase 7": {
        "residential": {
            "Block P": ["1 Kanal"],
            "Block Q": ["1 Kanal"],
            "Block R": ["1 Kanal"],
            "Block S": ["1 Kanal"],
            "Block T": ["10 Marla", "1 Kanal"],
            "Block U": ["10 Marla", "1 Kanal"],
            "Block V": ["1 Kanal"],
            "Block W": ["1 Kanal"],
            "Block X": ["10 Marla", "1 Kanal"],
            "Block Y": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Z": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Z-1": ["5 Marla", "10 Marla"],
            "Block Z-2": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "CCA 1 Commercial": ["4 Marla", "8 Marla"],
            "CCA 2 Commercial": ["4 Marla", "8 Marla"],
            "CCA 3 Commercial": ["4 Marla", "8 Marla"],
            "CCA 4 Commercial": ["4 Marla", "8 Marla"],
            "Sector Y Commercial": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 7": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Proper)": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal", "2 Kanal"],
            "Block D": ["1 Kanal", "2 Kanal"],
            "Block E": ["1 Kanal", "2 Kanal"],
            "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"],
            "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"],
            "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"],
            "Block M": ["10 Marla", "1 Kanal"],
            "Block N": ["10 Marla", "1 Kanal"],
            "Block P": ["10 Marla", "1 Kanal"],
            "Block Q": ["10 Marla", "1 Kanal"],
            "Block R": ["10 Marla", "1 Kanal"],
            "Block S": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block T": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block U": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block V": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block W": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block X": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Y": ["5 Marla", "10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Broadway Commercial": ["4 Marla", "8 Marla"],
            "Commercial Broadway Sector 1": ["4 Marla", "8 Marla"],
            "Commercial Broadway Sector 2": ["4 Marla", "8 Marla"],
            "Commercial CCA 1": ["4 Marla", "8 Marla"],
            "Commercial CCA 2": ["4 Marla", "8 Marla"],
            "Commercial CCA 3": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 8": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Ivy Green / Sector Z)": {
        "residential": {
            "Block Z-1": ["5 Marla", "10 Marla", "1 Kanal", "2 Kanal"],
            "Block Z-2": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Z-3": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Z-4": ["5 Marla", "10 Marla"],
            "Block Z-5": ["5 Marla", "10 Marla"],
            "Block Z-6": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "Commercial CCA Sector Z": ["4 Marla", "8 Marla"],
            "Sector Shops Sector Z": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Park View)": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["10 Marla", "1 Kanal"],
            "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["10 Marla", "1 Kanal"],
            "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"],
            "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"],
            "Block K": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Commercial Zone Park View": ["4 Marla", "8 Marla"],
            "Sector Shops Park View": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Air Avenue / Sector AA)": {
        "residential": {
            "Block L": ["10 Marla", "1 Kanal"],
            "Block M": ["10 Marla", "1 Kanal"],
            "Block N": ["10 Marla", "1 Kanal"],
            "Block P": ["10 Marla", "1 Kanal"],
            "Block Q": ["10 Marla", "1 Kanal"],
            "Block R": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Commercial CCA Air Avenue": ["4 Marla", "8 Marla"]
        }
    },
    "DHA Phase 9 Prism": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal", "2 Kanal"],
            "Block D": ["1 Kanal", "2 Kanal"],
            "Block E": ["1 Kanal"],
            "Block F": ["1 Kanal"],
            "Block G": ["1 Kanal"],
            "Block H": ["1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"],
            "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"],
            "Block M": ["10 Marla"],
            "Block N": ["10 Marla"],
            "Block P": ["5 Marla"],
            "Block Q": ["5 Marla"],
            "Block R": ["5 Marla"]
        },
        "commercial": {
            "Zone 1 Commercial (Civic Zone)": ["4 Marla", "8 Marla"],
            "Zone 2 Commercial": ["4 Marla", "8 Marla"],
            "Zone 3 Commercial": ["4 Marla", "8 Marla"],
            "Main Oval Commercial": ["4 Marla", "8 Marla", "16 Marla"],
            "Prism Direct MB Commercial": ["4 Marla", "8 Marla"]
        }
    },
    "DHA Phase 9 Town": {
        "residential": {
            "Block A": ["5 Marla", "8 Marla"],
            "Block B": ["5 Marla", "8 Marla"],
            "Block C": ["5 Marla", "8 Marla", "10 Marla"],
            "Block D": ["5 Marla", "8 Marla", "10 Marla"],
            "Block E": ["5 Marla", "8 Marla"]
        },
        "commercial": {
            "Commercial CCA Phase 9 Town": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 9 Town": ["2 Marla"]
        }
    },
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": {
        "residential": {
            "Sector 1 (Rahbar Phase 1)": ["5 Marla", "8 Marla", "10 Marla", "1 Kanal"],
            "Sector 2 (Rahbar Phase 2)": ["5 Marla", "8 Marla", "10 Marla", "1 Kanal"],
            "Sector 2 Extension": ["5 Marla"],
            "Sector 3 (Rahbar Phase 3)": ["5 Marla"],
            "Sector 4 (Rahbar Phase 4)": ["5 Marla"],
            "Sector 5 (Haloki / Defense Road)": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "Rahbar Main Commercial CCA 1": ["4 Marla", "8 Marla"],
            "Rahbar Main Commercial CCA 2": ["4 Marla", "8 Marla"],
            "Rahbar Sector 5 Commercial": ["4 Marla", "8 Marla"],
            "Rahbar Local Sector Shops": ["2 Marla"]
        }
    },
    "DHA Phase 12 (EME Sector)": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"],
            "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["10 Marla", "1 Kanal"],
            "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["10 Marla", "1 Kanal"],
            "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block H": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block J": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "Commercial Civic Centre EME": ["4 Marla", "8 Marla"],
            "Block D Commercial Market": ["4 Marla", "8 Marla"],
            "Block H Commercial Market": ["4 Marla", "6 Marla"],
            "Sector Shops EME": ["2 Marla"]
        }
    }
}

# -------------------------------------------------------------
# 5. ADVANCED MULTIMODAL EXTRACTION ENGINE (WITH MAP KEYWORDS)
# -------------------------------------------------------------
def parse_property_text(text, current_selected_phase, current_selected_block):
    text_upper = text.upper()
    
    # 1. Category Classification
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED", "DEMANDING"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT", "LEASE"]):
        category = "Rental"

    # 2. Property Type Classification
    prop_type = "Residential"
    if any(w in text_upper for w in ["COMMERCIAL", "COMM", "SHOP", "PLAZA", "OFFICE", "CCA", "BROADWAY", "OVAL", "BOUTIQUE", "CIVIC", "MARKET"]):
        prop_type = "Commercial"
    elif "COMMERCIAL" in str(current_selected_block).upper() or "BROADWAY" in str(current_selected_block).upper() or "CCA" in str(current_selected_block).upper():
        prop_type = "Commercial"

    # 3. Phase Normalization
    phase = current_selected_phase
    if "PRISM" in text_upper or "PHASE 9 PRISM" in text_upper or "9 PRISM" in text_upper:
        phase = "DHA Phase 9 Prism"
    elif "TOWN" in text_upper or "PHASE 9 TOWN" in text_upper:
        phase = "DHA Phase 9 Town"
    elif "RAHBAR" in text_upper or "PHASE 11" in text_upper:
        phase = "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)"
    elif "EME" in text_upper or "PHASE 12" in text_upper:
        phase = "DHA Phase 12 (EME Sector)"
    elif "IVY GREEN" in text_upper or "PHASE 8 Z" in text_upper or "SECTOR Z" in text_upper:
        phase = "DHA Phase 8 (Ivy Green / Sector Z)"
    elif "PARK VIEW" in text_upper:
        phase = "DHA Phase 8 (Park View)"
    elif "AIR AVENUE" in text_upper or "SECTOR AA" in text_upper:
        phase = "DHA Phase 8 (Air Avenue / Sector AA)"
    else:
        p_match = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
        if p_match:
            num = p_match.group(1)
            roman_dict = {"1":"1","2":"2","3":"3","4":"4","5":"5","6":"6","7":"7","8":"8","9":"9","10":"10","I":"1","II":"2","III":"3","IV":"4","V":"5","VI":"6","VII":"7","VIII":"8","IX":"9","X":"10"}
            norm_num = roman_dict.get(num, num)
            phase = f"DHA Phase {norm_num}"

    # 4. Block Detection
    block = current_selected_block if (current_selected_block != "All Blocks" and not current_selected_block.startswith("---")) else "Block A"
    b_match = re.search(r'(?:BLOCK|BLK|SECTOR|SEC)\s*[:.-]?\s*([A-Z0-9-]{1,5})', text_upper)
    if b_match:
        found_b = b_match.group(1)
        block = f"Block {found_b}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2}|CCA|BROADWAY)\s*(BLOCK|BLK|CCA|SECTOR)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    # 5. Size Detection
    size = "1 Kanal"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|M|K|SQFT|YARD|SQYD)', text_upper)
    if s_match:
        val = s_match.group(1)
        unit = s_match.group(2)
        if unit in ["K", "KANAL"]:
            size = f"{val} Kanal"
        elif unit in ["M", "MARLA"]:
            size = f"{val} Marla"
        else:
            size = f"{val} {unit}"

    # 6. Price / Demand Extraction
    demand = "N/A"
    price_match = re.search(r'(?:DEMAND|PRICE|OFFER|BUDGET|RATE)?\s*[:.-]?\s*(\d+\.?\d*)\s*(CRORE|CR|LAC|LACS|LAKH|LAKHS|MILLION|PKR)', text_upper)
    if price_match:
        demand = f"{price_match.group(1)} {price_match.group(2)}"
    else:
        direct_num = re.search(r'(\d+\.?\d*)\s*(CRORE|CR|LACS|LAKH)', text_upper)
        if direct_num:
            demand = f"{direct_num.group(1)} {direct_num.group(2)}"

    # 7. Contact / Phone Number Extraction
    phone = "N/A"
    phone_match = re.search(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', text)
    if phone_match:
        phone = re.sub(r'[^0-9+]', '', phone_match.group(0))

    # 8. Feature Attributes (Corner, Park Facing, Road Width)
    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Park Facing")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Boulevard")
    if "EXCESS" in text_upper: features.append("Excess Land")
    if "POSSESSION" in text_upper: features.append("Possession")
    if "DIRECT" in text_upper: features.append("Direct Deal")
    road_match = re.search(r'(\d{2,3})\s*(FT|FEET|ROAD|WIDE)', text_upper)
    if road_match: features.append(f"{road_match.group(0)} Road")
    feature_str = ", ".join(features) if features else "Standard Layout"

    return category, phase, block, prop_type, size, demand, phone, feature_str

# WhatsApp Share Link Formatter
def create_wa_link(row_dict):
    phone_to_target = row_dict.get('Phone Number', '')
    clean_target = re.sub(r'\D', '', str(phone_to_target)) if phone_to_target != 'N/A' else ''
    if clean_target.startswith('03'): clean_target = '92' + clean_target[1:]
    
    msg = f"""🏢 *{st.session_state['office_name']}*
📍 *DHA Lahore Verified Listing*
• *Phase:* {row_dict.get('Phase', 'N/A')}
• *Block:* {row_dict.get('Block', 'N/A')}
• *Type:* {row_dict.get('Property Type', 'Residential')}
• *Size:* {row_dict.get('Size', 'N/A')}
• *Category:* {row_dict.get('Category', 'N/A')}
• *Demand / Price:* {row_dict.get('Demand / Price', 'N/A')}
• *Features:* {row_dict.get('Features', 'Standard')}
📝 *Details:* {row_dict.get('Raw Listing Text', row_dict.get('Raw Listing', ''))}
---
📞 Direct Contact: {phone_to_target if phone_to_target != 'N/A' else 'Wali Muhammad Associates'}"""
    
    base_url = f"https://wa.me/{clean_target}" if clean_target else "https://wa.me/"
    return f"{base_url}?text={urllib.parse.quote(msg)}"

# -------------------------------------------------------------
# 6. UI LAYOUT & LOCATION CONTROLS
# -------------------------------------------------------------

# Top Header Banner
st.markdown(f"""
    <div class="header-banner">
        <span class="office-badge">📍 {st.session_state['office_name']}</span>
        <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
        <div class="header-subtitle">Official Map Segregation: Residential & Commercial Master Ingestion Portal</div>
    </div>
""", unsafe_allow_html=True)

# Agency Settings Modal
with st.expander("⚙️ Customize Agency Name & Settings"):
    new_office = st.text_input("Agency / Office Name", value=st.session_state["office_name"])
    if st.button("Update Agency Name"):
        st.session_state["office_name"] = new_office
        st.rerun()

# Supreme Multi-Feature Global Search Bar
st.markdown("### 🔍 Supreme Global Property Search")
search_query = st.text_input(
    "Search anything",
    placeholder="🔎 e.g. 1 Kanal Block M Facing Park, 4 Marla Broadway Commercial, 5 Marla Rahbar 1, 10 Marla Prism...",
    label_visibility="collapsed"
)

st.markdown("---")

# Cascading Phase, Sector & Size Selection Controls
col_city, col_phase, col_block, col_size = st.columns([1.1, 1.8, 1.8, 1.3])
with col_city:
    selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])
with col_phase:
    phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
    selected_phase = st.selectbox("📍 DHA Phase", phase_options, index=0)

# Build block options dynamically for this Phase from Catalog
phase_data = DHA_PHASE_BLOCK_CATALOG.get(selected_phase, {})
res_blocks = list(phase_data.get("residential", {}).keys())
comm_blocks = list(phase_data.get("commercial", {}).keys())

dynamic_block_list = ["All Blocks"]
if res_blocks:
    dynamic_block_list.append("--- 🏡 Residential Sectors ---")
    dynamic_block_list.extend([f"{b} (Residential)" for b in res_blocks])
if comm_blocks:
    dynamic_block_list.append("--- 🏢 Commercial Hubs ---")
    dynamic_block_list.extend(comm_blocks)

with col_block:
    selected_block = st.selectbox(f"🧱 Block List ({selected_phase})", dynamic_block_list)

clean_filter_block = selected_block.replace("---", "").strip()

# Dynamic sizes available for selected phase/block
with col_size:
    selected_size_filter = st.selectbox("📐 Size Filter", ["All Sizes", "5 Marla", "8 Marla", "10 Marla", "1 Kanal", "2 Kanal", "4 Marla", "8 Marla", "16 Marla"])

st.markdown("---")

# 7. MULTIMODAL DATA INGESTION PANEL (TEXT / CAMERA / OCR)
st.subheader(f"📥 Add Property Listing ({selected_phase})")
>>>>>>> a52e46999e0e7f6f00280fa44aeb732073571e70
tab_text, tab_camera = st.tabs(["📝 Text & File Ingestion", "📸 Live Camera Scanner"])

with tab_text:
    c_in1, c_in2 = st.columns([2, 1])
    with c_in1:
<<<<<<< HEAD
        source = st.selectbox("🔖 Data Source", ["WhatsApp Group", "Newspaper Classified", "Direct Client", "Facebook", "OLX", "Zameen.com"])
        raw_text = st.text_area(
            "📋 Paste Raw Property Text / Image OCR Output",
            height=140,
            placeholder=f"Example: {selected_phase} {selected_block} 1 Kanal Corner Facing Park plot for sale demand 4.50 crore direct dealer 03209498044..."
        )
        up_file = st.file_uploader("📎 Upload .txt file", type=["txt"])
        if up_file:
            raw_text = str(up_file.read(), "utf-8")

    with c_in2:
        st.markdown("""
        <div class="section-header">
            <h3>⚡ Real-Time Auto Extraction</h3>
        </div>
        """, unsafe_allow_html=True)
        if raw_text.strip():
            cat, ph, blk, sz, feat = parse_property_text(raw_text)
            st.markdown(f"""
            <div class="property-card">
                <span class="badge badge-phase">{ph}</span>
                <span class="badge {'badge-selling' if cat=='Selling' else 'badge-buying' if cat=='Buying' else 'badge-rental'}">{cat}</span>
                <br/><br/>
                <b>📍 Block:</b> {blk}<br/>
                <b>📐 Size:</b> {sz}<br/>
                <b>✨ Features:</b> {feat}<br/>
                <b>📊 Sheet Tab:</b> <code>{get_sheet_tab_name(ph, blk)}</code>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Paste or scan any listing to preview auto-extracted details...")

    if st.button("💾 Save to Phase+Block Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, ph, blk, sz, feat = parse_property_text(raw_text)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                saved_tab = save_to_phase_block_sheet(
                    workbook, ph, blk,
                    [now_str, source, cat, ph, blk, sz, feat, raw_text]
                )
                st.success(f"✅ Saved to Google Sheet Tab: [{saved_tab}]")
=======
        source = st.selectbox("📌 Data Source", ["WhatsApp Group", "Newspaper Classified", "Direct Client", "Facebook", "Call Log"])
        placeholder_blk = clean_filter_block if clean_filter_block != "All Blocks" else "Block A"
        raw_text = st.text_area(
            "📋 Paste Raw Property Text / Image OCR Output",
            height=140,
            placeholder=f"Example: {selected_phase} {placeholder_blk} 1 Kanal Corner Facing Park plot for sale demand 4.50 crore direct dealer 03209498044..."
        )
        up_file = st.file_uploader("Or Upload .txt / Picture OCR File", type=["txt"])
        if up_file: raw_text = str(up_file.read(), "utf-8")
        
    with c_in2:
        st.markdown("#### ⚡ Real-Time Auto Extraction")
        if raw_text.strip():
            cat, ph, blk, p_type, sz, dem, phn, feat = parse_property_text(raw_text, selected_phase, clean_filter_block)
            st.write(f"**Target Sheet:** `{ph}`")
            st.write(f"**Category:** `{cat}`")
            st.write(f"**Block & Type:** `{blk}` ({p_type})")
            st.write(f"**Size:** `{sz}`")
            st.write(f"**Demand / Price:** `{dem}`")
            st.write(f"**Phone Number:** `{phn}`")
            st.write(f"**Features:** `{feat}`")
        else:
            st.info(f"Paste or scan any listing to preview auto-extracted details...")

    if st.button(f"💾 Save Listing to [{selected_phase}] Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, ph, blk, p_type, sz, dem, phn, feat = parse_property_text(raw_text, selected_phase, clean_filter_block)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # Append full payload to phase sheet
                row_payload = [now_str, source, cat, ph, blk, p_type, sz, dem, phn, feat, raw_text]
                append_to_phase_sheet(workbook, ph, row_payload)
                
                st.success(f"✅ Saved into Google Sheet Tab: **[{ph}]** under **[{blk}]** ({p_type}) | Demand: {dem}!")
>>>>>>> a52e46999e0e7f6f00280fa44aeb732073571e70
                st.balloons()
            except Exception as e:
                st.error(f"Save Error: {e}")
        else:
<<<<<<< HEAD
            st.warning("Please paste a listing text first.")

with tab_camera:
    img = st.camera_input("📷 Scan Property Ad / Business Card")
    if img:
        st.success("Photo captured! (OCR integration coming soon)")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# 10. LIVE INVENTORY — PHASE+BLOCK SPECIFIC
# ═══════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="section-header">
    <h3>📊 Live Inventory: {selected_phase} — {selected_block}</h3>
</div>
""", unsafe_allow_html=True)

try:
    data, active_tab = load_phase_block_data(workbook, selected_phase, selected_block)

    if len(data) > 1:
        df = pd.DataFrame(data[1:], columns=SHEET_HEADERS[:len(data[1])])

        # Apply search filter
        if search_query:
            mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
            df = df[mask]

        # Apply size filter
        if selected_size_filter != "All Sizes":
            df = df[df["Size"].str.contains(selected_size_filter, case=False, na=False)]

        # Stats Row
        c1, c2, c3, c4 = st.columns(4)
        sell_count = len(df[df["Category"] == "Selling"]) if "Category" in df.columns else 0
        buy_count = len(df[df["Category"] == "Buying"]) if "Category" in df.columns else 0
        rent_count = len(df[df["Category"] == "Rental"]) if "Category" in df.columns else 0
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{len(df)}</div><div class="stat-label">Total Listings</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{sell_count}</div><div class="stat-label">For Sale</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{buy_count}</div><div class="stat-label">Buyers</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{rent_count}</div><div class="stat-label">Rentals</div></div>', unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # 3-Category Tabs
        ts, tb, tr = st.tabs(["🔴 Selling", "🟢 Buying", "🔵 Rental"])

        def display_listings(filt_df, badge_class):
            if filt_df.empty:
                st.info("No records in this category yet.")
=======
            st.warning("Please enter or paste listing text first.")

with tab_camera:
    img = st.camera_input("Take Photo of Classified Ad / Business Card")
    if img: st.success("Photo captured successfully! Ready for OCR.")

st.markdown("---")

# 8. LIVE 3-SHEET INVENTORY TABS & WHATSAPP ACTIONS
st.subheader(f"📊 Live Inventory: [{selected_phase}] — [{clean_filter_block}]")
try:
    try:
        data = workbook.worksheet(selected_phase).get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        data = []

    if len(data) > 1:
        headers = ["Timestamp", "Source", "Category", "Phase", "Block", "Property Type", "Size", "Demand / Price", "Phone Number", "Features", "Raw Listing Text"]
        df = pd.DataFrame(data[1:], columns=headers[:len(data[1])])
        
        # Dynamic Block Filtering
        if clean_filter_block != "All Blocks" and not clean_filter_block.startswith("---"):
            core_block_letter = re.search(r'Block\s*([A-Z0-9-]+)', clean_filter_block)
            search_token = core_block_letter.group(0) if core_block_letter else clean_filter_block
            df = df[df["Block"].str.contains(search_token, case=False, na=False) |
                    df["Raw Listing Text"].str.contains(search_token, case=False, na=False)]
            
        # Size Filtering
        if selected_size_filter != "All Sizes":
            df = df[df["Size"].str.contains(selected_size_filter, case=False, na=False) |
                    df["Raw Listing Text"].str.contains(selected_size_filter, case=False, na=False)]
            
        # Global Search Filtering
        if search_query:
            df = df[df["Raw Listing Text"].str.contains(search_query, case=False, na=False) |
                    df["Features"].str.contains(search_query, case=False, na=False) |
                    df["Block"].str.contains(search_query, case=False, na=False) |
                    df["Demand / Price"].str.contains(search_query, case=False, na=False)]

        ts, tb, tr = st.tabs(["🔴 Available Inventory (Selling)", "🟢 Buyer Requirements (Buying)", "🔵 Rental & Leases"])
        
        def display_listings(filt_df, badge_c):
            if filt_df.empty:
                st.info("No matching records found in this category.")
>>>>>>> a52e46999e0e7f6f00280fa44aeb732073571e70
                return
            for _, r in filt_df.iterrows():
                wa = create_wa_link(r.to_dict())
                c1, c2 = st.columns([4, 1.2])
                with c1:
<<<<<<< HEAD
                    st.markdown(f"""
                    <div class="property-card">
                        <span class="badge {badge_class}">{r.get('Category', '')}</span>
                        <span class="badge badge-feature">{r.get('Features', '')}</span>
                        <span class="badge badge-phase">{r.get('Phase', '')}</span>
                        <br/><br/>
                        <b>{r.get('Phase', '')} — {r.get('Block', '')} — {r.get('Size', '')}</b>
                        <p style="margin: 8px 0 4px 0; color:#475569; font-size:14px; line-height:1.5;">{r.get('Raw Listing Text', '')}</p>
                        <small style="color:#94A3B8;">🕐 {r.get('Timestamp', '')} &nbsp;|&nbsp; 📂 {r.get('Source', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="{wa}" target="_blank" class="wa-btn">📲 WhatsApp Share</a>', unsafe_allow_html=True)

        with ts:
            display_listings(df[df["Category"] == "Selling"] if "Category" in df.columns else df, "badge-selling")
        with tb:
            display_listings(df[df["Category"] == "Buying"] if "Category" in df.columns else df, "badge-buying")
        with tr:
            display_listings(df[df["Category"] == "Rental"] if "Category" in df.columns else df, "badge-rental")
    else:
        st.info(f"Sheet tab [{active_tab}] is empty. Add your first listing above! 👆")

except Exception as e:
    st.error(f"Error loading inventory: {e}")

# ── Footer ──
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 12px; color: #90CAF9; font-size: 12px; font-weight: 500;">
    🏢 DHA Smart Property Engine &nbsp;|&nbsp; Phase+Block Routing &nbsp;|&nbsp; Light Blue Stitch UI
</div>
""", unsafe_allow_html=True)
=======
                    p_type_val = r.get('Property Type', 'Residential')
                    dem_val = r.get('Demand / Price', 'N/A')
                    phn_val = r.get('Phone Number', 'N/A')
                    st.markdown(f"""
                        <div class="property-card">
                            <span class="badge {badge_c}">{r.get('Category', '')}</span>
                            <span class="badge badge-type">{p_type_val}</span>
                            <span class="badge badge-price">💰 {dem_val}</span>
                            <span class="badge badge-feature">{r.get('Features', '')}</span>
                            <b>{r.get('Phase', '')} {r.get('Block', '')} — {r.get('Size', '')}</b>
                            <p style="margin: 6px 0 0 0; color:#475569; font-size:14px;">{r.get('Raw Listing Text', '')}</p>
                            <small style="color:#94A3B8;">Source: {r.get('Source', '')} | Phone: {phn_val} | Added: {r.get('Timestamp', '')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="{wa}" target="_blank" class="wa-btn">📲 WhatsApp</a>', unsafe_allow_html=True)

        with ts: display_listings(df[df["Category"] == "Selling"] if "Category" in df.columns else df, "badge-selling")
        with tb: display_listings(df[df["Category"] == "Buying"] if "Category" in df.columns else df, "badge-buying")
        with tr: display_listings(df[df["Category"] == "Rental"] if "Category" in df.columns else df, "badge-rental")
    else:
        st.info(f"Google Sheet tab **[{selected_phase}]** is active and connected. Add your first listing above to view records!")
except Exception as e:
    st.error(f"Data Load Error: {e}")
>>>>>>> a52e46999e0e7f6f00280fa44aeb732073571e70
