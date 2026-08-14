import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import re
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime
import io
from PIL import Image

# ---------------------------------------------------------
# 1. Page Configuration & Storage Paths
# ---------------------------------------------------------
st.set_page_config(
    page_title="DHA Smart Property Engine | PropSync DHA",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOCAL_CSV_PATH = os.path.join(LOCAL_DATA_DIR, "properties.csv")
SECRETS_DIR = os.path.join(os.path.dirname(__file__), ".streamlit")
SECRETS_PATH = os.path.join(SECRETS_DIR, "secrets.toml")
PLAN_XLSX_PATH = os.path.join(LOCAL_DATA_DIR, "Implementation_Plan_DHA_App_Till_Date.xlsx")

os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(SECRETS_DIR, exist_ok=True)

CSV_COLUMNS = [
    "Timestamp", "Source", "Category", "Property Type", 
    "City", "Phase", "Block", "Size", "Road Width", "Features", 
    "Price", "Phone", "Agency", "Raw Listing Text"
]

# ---------------------------------------------------------
# 2. Session State Initialization
# ---------------------------------------------------------
if "agency_name" not in st.session_state:
    st.session_state["agency_name"] = "Wali Muhammad Associates"
if "agency_phone" not in st.session_state:
    st.session_state["agency_phone"] = "0300-1234567"
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = "Lahore"
if "active_phase" not in st.session_state:
    st.session_state["active_phase"] = "Phase 6"

# ---------------------------------------------------------
# 3. Google Stitch UI Design Tokens & Styling CSS
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Google Stitch & Slate Theme */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        background-color: #F8FAFC;
        color: #0F172A;
    }
    
    /* Header Banner */
    .stitch-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #0F172A 100%);
        padding: 24px 32px;
        border-radius: 18px;
        color: #FFFFFF;
        margin-bottom: 22px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2), 0 8px 10px -6px rgba(15, 23, 42, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .stitch-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .stitch-subtitle {
        color: #94A3B8;
        font-size: 13.5px;
        margin-top: 4px;
        font-weight: 400;
    }
    .agency-tag {
        background: rgba(14, 165, 233, 0.15);
        color: #38BDF8;
        border: 1px solid rgba(14, 165, 233, 0.35);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #FFFFFF;
        padding: 16px 20px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08);
        border-color: #CBD5E1;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 800;
        color: #0F172A;
    }
    .metric-label {
        font-size: 11.5px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    
    /* Extraction Preview Card */
    .preview-box {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 22px;
        border: 1px solid #E2E8F0;
        border-left: 6px solid #0EA5E9;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
    }
    
    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12.5px;
        font-weight: 600;
        margin: 3px 4px 3px 0;
    }
    .badge-cat-selling { background-color: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
    .badge-cat-buying { background-color: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
    .badge-cat-rental { background-color: #F3E8FF; color: #7E22CE; border: 1px solid #E9D5FF; }
    .badge-phase { background-color: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; }
    .badge-block { background-color: #EDE9FE; color: #6D28D9; border: 1px solid #DDD6FE; }
    .badge-type { background-color: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }
    .badge-size { background-color: #F1F5F9; color: #334155; border: 1px solid #E2E8F0; }
    .badge-road { background-color: #FEF9C3; color: #854D0E; border: 1px solid #FEF08A; }
    .badge-price { background-color: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; font-weight: 700; }
    .badge-phone { background-color: #E0F2FE; color: #0284C7; border: 1px solid #BAE6FD; }
    .badge-tag { background-color: #F8FAFC; color: #475569; border: 1px solid #CBD5E1; }
    
    /* Action Buttons */
    .wa-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #10B981;
        color: #FFFFFF !important;
        padding: 10px 18px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 13.5px;
        text-decoration: none;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        transition: all 0.2s ease;
        gap: 8px;
    }
    .wa-btn:hover {
        background-color: #059669;
        text-decoration: none;
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
    }
    
    /* Phase Bar Pills */
    .phase-pill {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        color: #334155;
        cursor: pointer;
        margin: 2px;
        transition: all 0.15s ease;
    }
    .phase-pill:hover {
        border-color: #0EA5E9;
        color: #0284C7;
        background: #F0F9FF;
    }
    
    /* Streamlit widget tweaks */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px !important;
    }
    div.stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    div.stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 10px 10px 0px 0px;
        font-weight: 600;
        padding: 0 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Google Sheets Backend & Dynamic Block Routing
# ---------------------------------------------------------
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"

@st.cache_resource
def get_google_client():
    """Initializes gspread client from secrets if present."""
    try:
        if "gcp_service_account" not in st.secrets:
            return None, None, "Secrets not configured (missing 'gcp_service_account')"
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        sheet_url = st.secrets.get("google_sheet_url", DEFAULT_SHEET_URL)
        spreadsheet = gc.open_by_url(sheet_url)
        return gc, spreadsheet, None
    except Exception as e:
        return None, None, str(e)

gc, spreadsheet, sheet_err = get_google_client()

def load_local_data():
    """Reads properties from local CSV with fallback columns."""
    if os.path.exists(LOCAL_CSV_PATH):
        try:
            df = pd.read_csv(LOCAL_CSV_PATH)
            for col in CSV_COLUMNS:
                if col not in df.columns:
                    df[col] = "N/A"
            return df[CSV_COLUMNS]
        except Exception:
            return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.DataFrame(columns=CSV_COLUMNS)

def save_local_data(df):
    """Saves DataFrame to local CSV."""
    df.to_csv(LOCAL_CSV_PATH, index=False)

def route_and_save_to_google_sheet(spreadsheet_obj, row_data, phase, block):
    """
    Dynamic Block Routing:
    1. Determines target block tab name (e.g., 'Phase 6 - Block M' or 'Block M').
    2. Auto-creates worksheet if missing and injects standardized column headers.
    3. Appends structured row to the block worksheet tab.
    4. Also appends row to 'Master_Inventory' tab for unified search.
    """
    if spreadsheet_obj is None:
        return False, "Google Spreadsheet connection is offline"
        
    try:
        # Determine tab name
        clean_block = block.strip() if block and block != "N/A" else "General"
        clean_phase = phase.strip() if phase and phase != "N/A" else "Phase General"
        target_tab_title = f"{clean_phase} - {clean_block}"[:30]
        
        existing_sheets = [ws.title for ws in spreadsheet_obj.worksheets()]
        
        # 1. Block-Specific Worksheet
        if target_tab_title not in existing_sheets:
            block_ws = spreadsheet_obj.add_worksheet(title=target_tab_title, rows=1000, cols=len(CSV_COLUMNS) + 2)
            block_ws.append_row(CSV_COLUMNS)
        else:
            block_ws = spreadsheet_obj.worksheet(target_tab_title)
            
        block_ws.append_row(row_data)
        
        # 2. Master_Inventory Worksheet
        if "Master_Inventory" not in existing_sheets:
            master_ws = spreadsheet_obj.add_worksheet(title="Master_Inventory", rows=5000, cols=len(CSV_COLUMNS) + 2)
            master_ws.append_row(CSV_COLUMNS)
        else:
            master_ws = spreadsheet_obj.worksheet("Master_Inventory")
            
        master_ws.append_row(row_data)
        return True, f"Synced to tabs: '{target_tab_title}' & 'Master_Inventory'"
    except Exception as e:
        return False, str(e)

def save_property_entry(source, cat, p_type, city, phase, block, size, road_width, features_str, price, phone, agency, raw_text):
    """Saves property entry locally and routes dynamically to Google Sheets."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_dict = {
        "Timestamp": now_str,
        "Source": source,
        "Category": cat,
        "Property Type": p_type,
        "City": city,
        "Phase": phase,
        "Block": block,
        "Size": size,
        "Road Width": road_width,
        "Features": features_str,
        "Price": price,
        "Phone": phone,
        "Agency": agency,
        "Raw Listing Text": raw_text
    }
    row_list = [row_dict[c] for c in CSV_COLUMNS]
    
    # 1. Local CSV update
    df = load_local_data()
    df = pd.concat([pd.DataFrame([row_dict]), df], ignore_index=True)
    save_local_data(df)
    
    # 2. Dynamic Google Sheets Routing
    sheet_synced = False
    sync_msg = ""
    if spreadsheet is not None:
        sheet_synced, sync_msg = route_and_save_to_google_sheet(spreadsheet, row_list, phase, block)
        
    return True, sheet_synced, sync_msg

# ---------------------------------------------------------
# 5. Smart Regex Parser Engine v3.0
# ---------------------------------------------------------
def parse_property_text(text):
    text_clean = text.strip()
    text_upper = text_clean.upper()
    
    # --- A. Category ---
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED", "DEMANDING CLIENT", "LOOKING FOR", "URGENT BUYER"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT", "OFFICE RENT", "HOUSE RENT", "SHOP RENT", "FOR LEASE"]):
        category = "Rental"
    elif any(w in text_upper for w in ["FOR SALE", "AVAILABLE", "SELLING", "DIRECT SALE", "OFFER", "DEMAND"]):
        category = "Selling"
        
    # --- B. Property Type ---
    prop_type = "Plot"
    if any(w in text_upper for w in ["COMMERCIAL", "SHOP", "PLAZA", "OFFICE", "HALL", "BUILDING", "CCA", "COMM"]):
        prop_type = "Commercial"
    elif any(w in text_upper for w in ["HOUSE", "VILLA", "BUNGALOW", "PORTION", "STOREY", "BEDROOM", "BATH", "BRAND NEW HOUSE", "FURNISHED HOUSE"]):
        prop_type = "House"
    elif any(w in text_upper for w in ["APARTMENT", "FLAT", "PENTHOUSE", "STUDIO"]):
        prop_type = "Apartment"
    elif any(w in text_upper for w in ["FILE", "AFFIDAVIT", "ALLOCATION", "INTIQAL", "BALLOT", "OPEN FILE"]):
        prop_type = "File / Affidavit"
    elif any(w in text_upper for w in ["PLOT", "RESIDENTIAL PLOT", "RES PLOT"]):
        prop_type = "Plot"

    # --- C. City Detection ---
    city = "Lahore"
    if "ISLAMABAD" in text_upper or "RAWALPINDI" in text_upper or "DHA ISB" in text_upper:
        city = "Islamabad"
    elif "KARACHI" in text_upper or "DHA KHI" in text_upper or "CITY KARACHI" in text_upper:
        city = "Karachi"
    elif "GUJRANWALA" in text_upper:
        city = "Gujranwala"
    elif "MULTAN" in text_upper:
        city = "Multan"
    elif "BAHAWALPUR" in text_upper:
        city = "Bahawalpur"
    elif "QUETTA" in text_upper:
        city = "Quetta"
    elif "PESHAWAR" in text_upper:
        city = "Peshawar"

    # --- D. Phase Detection ---
    phase = "Phase 6"
    if "PRISM" in text_upper or "PHASE 9 PRISM" in text_upper or "9 PRISM" in text_upper:
        phase = "Phase 9 Prism"
    elif "9 TOWN" in text_upper or "PHASE 9 TOWN" in text_upper:
        phase = "Phase 9 Town"
    elif "RAHBAR" in text_upper or "PHASE 11" in text_upper:
        phase = "DHA Rahbar (Ph 11)"
    elif "EME" in text_upper or "PHASE 12" in text_upper:
        phase = "DHA EME (Ph 12)"
    elif "RAHWALI" in text_upper:
        phase = "DHA Rahwali"
    else:
        phase_pattern = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII)\b', text_upper)
        if phase_pattern:
            p_val = phase_pattern.group(1)
            roman_map = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10", "XI": "11", "XII": "12", "XIII": "13"}
            p_clean = roman_map.get(p_val, p_val)
            phase = f"Phase {p_clean}"

    # --- E. Block Detection ---
    block = "Block A"
    b_match = re.search(r'(?:BLOCK|BLK|SECTOR|SEC)[\s:.-]*([A-Z]{1,2}(?:\d)?)\b', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    elif "CCA-1" in text_upper or "CCA 1" in text_upper:
        block = "CCA 1"
    elif "CCA-2" in text_upper or "CCA 2" in text_upper:
        block = "CCA 2"
    elif "CCA-3" in text_upper or "CCA 3" in text_upper:
        block = "CCA 3"
    elif "CCA" in text_upper:
        block = "CCA"
    elif "COMMERCIAL BROADWAY" in text_upper or "BROADWAY" in text_upper:
        block = "Commercial Broadway"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(?:BLOCK|BLK)\b', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    # --- F. Size Detection ---
    size = "1 Kanal"
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(MARLA|KANAL|SQFT|SQ FT|SQFT\.|SQ YARD|SQ\. YARDS?|YARDS?|ACRE)', text_upper)
    if size_match:
        val = size_match.group(1)
        unit = size_match.group(2).replace("SQ FT", "Sqft").replace("SQ YARDS", "Sq Yd").title()
        size = f"{val} {unit}"

    # --- G. Road Width Detection ---
    road_width = "Standard Road"
    if any(w in text_upper for w in ["MAIN BOULEVARD", "MAIN BLVD", " MB ", "150 FT", "150FT", "150'"]):
        road_width = "Main Boulevard (150ft)"
    elif "100 FT" in text_upper or "100FT" in text_upper or "100'" in text_upper:
        road_width = "100ft Road"
    elif "80 FT" in text_upper or "80FT" in text_upper or "80'" in text_upper:
        road_width = "80ft Road"
    elif "60 FT" in text_upper or "60FT" in text_upper or "60'" in text_upper:
        road_width = "60ft Road"
    elif "40 FT" in text_upper or "40FT" in text_upper or "40'" in text_upper:
        road_width = "40ft Road"
    else:
        road_match = re.search(r'(\d{2,3})\s*(?:FT|FEET|\')\s*(?:ROAD|STREET|MAIN|WIDE)?', text_upper)
        if road_match:
            r_val = road_match.group(1)
            road_width = f"{r_val}ft Road"

    # --- H. Price / Demand / Budget Detection ---
    price = "N/A"
    price_match = re.search(r'(?:DEMAND|BUDGET|PRICE|ASKING|RENT|DEMANDING|COST)?[\s:.-]*(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*(CRORE|CR|CRORES|LACS?|LAKH|LACS|COROR|MILLION|K|THOUSAND)\b', text_upper)
    if price_match:
        p_val = price_match.group(1)
        p_unit = price_match.group(2)
        if p_unit in ["CRORE", "CR", "CRORES", "COROR"]:
            price = f"{p_val} Crore"
        elif p_unit in ["LAC", "LACS", "LAKH"]:
            price = f"{p_val} Lacs"
        elif p_unit in ["K", "THOUSAND"]:
            price = f"{p_val}k"
        elif p_unit == "MILLION":
            price = f"{p_val} Million"
        else:
            price = f"{p_val} {p_unit.title()}"
    else:
        demand_num = re.search(r'(?:DEMAND|BUDGET)[\s:.-]*(\d+(?:\.\d+)?)\b', text_upper)
        if demand_num:
            price = f"{demand_num.group(1)} (Numeric)"

    # --- I. Phone Number Detection ---
    phone = "N/A"
    phone_clean = ""
    phone_match = re.search(r'(?:\+?92|0092|0)?[\s-]*(3\d{2})[\s-]*(\d{7})\b', text)
    if phone_match:
        code = phone_match.group(1)
        num = phone_match.group(2)
        phone = f"0{code}-{num}"
        phone_clean = f"92{code}{num}"

    # --- J. Special Attributes & Smart Tags ---
    tags = []
    if "CORNER" in text_upper:
        tags.append("Corner")
    if "PARK FACING" in text_upper or "PARK FACE" in text_upper or "FACING PARK" in text_upper:
        tags.append("Facing Park")
    if "EXCESS LAND" in text_upper or "EXTRA LAND" in text_upper:
        tags.append("Excess Land")
    if "POSSESSION" in text_upper and "NON" not in text_upper:
        tags.append("Possession")
    elif "NON POSSESSION" in text_upper or "NON-POSSESSION" in text_upper:
        tags.append("Non-Possession")
    if "URGENT" in text_upper or "URGENT SALE" in text_upper or "DISTRESS" in text_upper:
        tags.append("Urgent Deal")
    if "DIRECT" in text_upper or "DIRECT OWNER" in text_upper or "DIRECT CLIENT" in text_upper:
        tags.append("Direct Owner/Client")
    if "PAIR" in text_upper or "PAIR PLOT" in text_upper:
        tags.append("Pair Plots")
    if "FACING COMMERCIAL" in text_upper or "COMMERCIAL FACING" in text_upper:
        tags.append("Facing Commercial")
    if "HOT LOCATION" in text_upper or "PRIME LOCATION" in text_upper:
        tags.append("Prime Location")

    return category, prop_type, city, phase, block, size, road_width, price, phone, phone_clean, tags

# ---------------------------------------------------------
# 6. Stitch Header & Agency Branding Component
# ---------------------------------------------------------
all_properties_df = load_local_data()

# Header status pills
sheet_status_badge = '<span style="color:#10B981; font-weight:700;">🟢 Cloud Active</span>' if spreadsheet is not None else '<span style="color:#F59E0B; font-weight:700;">🟡 Local Storage</span>'

st.markdown(f"""
    <div class="stitch-header">
        <div>
            <div class="stitch-title">
                🏢 DHA Smart Property Engine
                <span class="agency-tag">✨ {st.session_state['agency_name']}</span>
            </div>
            <div class="stitch-subtitle">
                PropSync DHA • Multimodal Real Estate Parser & Dynamic Block-Wise Google Sheets Hub
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="background:rgba(255,255,255,0.08); padding:8px 16px; border-radius:12px; border:1px solid rgba(255,255,255,0.15); font-size:13px;">
                Sheets Engine: {sheet_status_badge}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Top Live KPI Counters
m1, m2, m3, m4, m5 = st.columns(5)
total_count = len(all_properties_df)
selling_count = len(all_properties_df[all_properties_df["Category"] == "Selling"]) if total_count > 0 and "Category" in all_properties_df.columns else 0
buying_count = len(all_properties_df[all_properties_df["Category"] == "Buying"]) if total_count > 0 and "Category" in all_properties_df.columns else 0
rental_count = len(all_properties_df[all_properties_df["Category"] == "Rental"]) if total_count > 0 and "Category" in all_properties_df.columns else 0

with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Total Inventory</div><div class="metric-value">{total_count}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Selling / Available</div><div class="metric-value" style="color:#10B981;">{selling_count}</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Buying / Wanted</div><div class="metric-value" style="color:#D97706;">{buying_count}</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Rental / Leases</div><div class="metric-value" style="color:#7E22CE;">{rental_count}</div></div>', unsafe_allow_html=True)
with m5:
    routing_status = "Dynamic Block Tabs" if spreadsheet is not None else "Local CSV Database"
    st.markdown(f'<div class="metric-card"><div class="metric-label">Target Routing</div><div class="metric-value" style="font-size:15px; color:#0284C7; margin-top:5px;">{routing_status}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. Sidebar: Navigation & Agency Profile Settings
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/real-estate.png", width=60)
    st.title("PropSync DHA")
    st.caption("AI-Powered Automation Portal")
    
    app_mode = st.radio(
        "📍 Navigation",
        ["📥 Multimodal Data Ingestion", "📊 3-Sheet Inventory Hub", "🔎 Ultra-Smart Search", "⚙️ Cloud & Agency Settings"],
        index=0
    )
    
    st.markdown("---")
    st.subheader("🏢 Agency Profile")
    new_agency = st.text_input("Agency / Office Name", value=st.session_state["agency_name"])
    new_agency_phone = st.text_input("Agency WhatsApp Number", value=st.session_state["agency_phone"])
    if new_agency != st.session_state["agency_name"] or new_agency_phone != st.session_state["agency_phone"]:
        st.session_state["agency_name"] = new_agency
        st.session_state["agency_phone"] = new_agency_phone
        st.rerun()

    st.markdown("---")
    st.subheader("🗺️ Location Quick-Switch")
    city_options = ["Lahore", "Islamabad", "Karachi", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"]
    st.session_state["selected_city"] = st.selectbox("Active City", city_options, index=city_options.index(st.session_state["selected_city"]))
    
    phase_options = ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase 7", "Phase 8", "Phase 9 Prism", "Phase 9 Town", "Phase 10", "DHA Rahbar (Ph 11)", "DHA EME (Ph 12)", "Phase 13", "DHA Rahwali"]
    if st.session_state["active_phase"] in phase_options:
        p_idx = phase_options.index(st.session_state["active_phase"])
    else:
        p_idx = 5
    st.session_state["active_phase"] = st.selectbox("Active Phase", phase_options, index=p_idx)

# ---------------------------------------------------------
# VIEW 1: 📥 MULTIMODAL DATA INGESTION
# ---------------------------------------------------------
if app_mode == "📥 Multimodal Data Ingestion":
    st.subheader("📥 Ingestion & Live Smart Parsing")
    st.caption("Convert raw WhatsApp messages, camera newspaper snaps, and text files into structured block inventory records.")
    
    tab_text, tab_camera, tab_file = st.tabs(["📝 Raw Text Listing", "📷 Camera Input (OCR Snap)", "📁 File & Image Uploader"])
    
    extracted_text = ""
    source_type = "WhatsApp Group"
    
    with tab_text:
        st.markdown("**⚡ Quick Test Presets:**")
        q1, q2, q3, q4 = st.columns(4)
        preset_text = ""
        if q1.button("📋 Urgent 1K Plot (Sale)", use_container_width=True):
            preset_text = "DHA Phase 6 Block M 1 Kanal plot for urgent sale. Demand 4.5 crore. Prime location, park facing on 80ft road, possession. Contact 0300-1234567"
        if q2.button("📋 10M House (Buying)", use_container_width=True):
            preset_text = "Required 10 Marla brand new double storey house in DHA Phase 5 Block C. Budget 4.25 Crore direct client. Call 0321-7654321"
        if q3.button("📋 Commercial Rent Plaza", use_container_width=True):
            preset_text = "Available 4 Marla commercial plaza in DHA Phase 8 CCA 1 for rent. Corner building on 100 ft road. Rent 3.5 Lacs. 0333-8889990"
        if q4.button("📋 MB Pair Plots (Sale)", use_container_width=True):
            preset_text = "DHA Phase 9 Prism Block D 2 Kanal pair plots available on Main Boulevard 150 ft road. Excess land, direct owner demand 8.5 Crore. 0302-5556667"
            
        c_src, c_empty = st.columns([1, 2])
        with c_src:
            source_type = st.selectbox("📌 Data Origin", ["WhatsApp Group", "Direct Client", "Facebook Group", "Newspaper Classified", "Colleague Agent", "Field Survey"])
            
        text_val = preset_text if preset_text else ""
        raw_input = st.text_area(
            "📋 Paste Raw Listing Text",
            value=text_val,
            height=160,
            placeholder="Paste any listing e.g.: DHA Phase 6 Block M 1 Kanal plot for urgent sale demand 4.5 crore corner park facing 80ft road 0300-1234567..."
        )
        if raw_input.strip():
            extracted_text = raw_input.strip()

    with tab_camera:
        st.markdown("📸 **Snap Newspaper Ad or Paper Slip:**")
        camera_img = st.camera_input("Capture Listing Photo")
        if camera_img is not None:
            img = Image.open(camera_img)
            st.image(img, caption="Snapped Listing Document", width=380)
            st.info("💡 **Image Captured**: Type or edit key details extracted from photo below:")
            ocr_manual_text = st.text_area("Parsed Text from Photo", value="DHA Phase 7 Block T 1 Kanal plot for sale demand 2.65 Crore corner facing park 0300-9998877", height=100)
            if ocr_manual_text.strip():
                extracted_text = ocr_manual_text.strip()
                source_type = "Newspaper Classified (Camera OCR)"

    with tab_file:
        st.markdown("📁 **Upload Screenshot or Document:**")
        uploaded_file = st.file_uploader("Upload Image (.png, .jpg) or Text File (.txt)", type=["png", "jpg", "jpeg", "txt"])
        if uploaded_file is not None:
            if uploaded_file.name.endswith(".txt"):
                txt_content = uploaded_file.read().decode("utf-8")
                extracted_text = txt_content.strip()
                st.success(f"Loaded text file: {uploaded_file.name}")
            else:
                img = Image.open(uploaded_file)
                st.image(img, caption=uploaded_file.name, width=380)
                file_text = st.text_area("Extracted Listing Content", value="DHA Phase 6 Block C 2 Kanal House available for sale demand 11.5 Crore Main Boulevard 0321-4443322", height=100)
                if file_text.strip():
                    extracted_text = file_text.strip()
                    source_type = "Image / Document Upload"

    st.markdown("---")
    
    # Live Visual Preview & Extraction
    p_col1, p_col2 = st.columns([1.2, 1])
    
    if extracted_text:
        cat, p_type, city, phase, block, size, road_width, price, phone, phone_clean, tags = parse_property_text(extracted_text)
        
        with p_col1:
            st.subheader("⚡ Live Extraction Card")
            badge_cat_class = f"badge-cat-{cat.lower()}"
            tags_html = "".join([f'<span class="badge badge-tag">🏷️ {t}</span>' for t in tags]) if tags else '<span style="color:#94A3B8; font-size:12px;">No specific tags</span>'
            
            st.markdown(f"""
                <div class="preview-box">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                        <span class="badge {badge_cat_class}" style="font-size:14px; padding:6px 16px;">📂 {cat}</span>
                        <span class="badge badge-type" style="font-size:13px;">🏡 {p_type}</span>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:14px;">
                        <div><small style="color:#64748B; font-weight:600;">Location / Phase:</small><br><span class="badge badge-phase">📍 {city} • {phase}</span></div>
                        <div><small style="color:#64748B; font-weight:600;">Target Block:</small><br><span class="badge badge-block">🧱 {block}</span></div>
                        <div><small style="color:#64748B; font-weight:600;">Property Size:</small><br><span class="badge badge-size">📏 {size}</span></div>
                        <div><small style="color:#64748B; font-weight:600;">Road Width:</small><br><span class="badge badge-road">🛣️ {road_width}</span></div>
                        <div><small style="color:#64748B; font-weight:600;">Demand / Budget:</small><br><span class="badge badge-price">💰 {price}</span></div>
                        <div><small style="color:#64748B; font-weight:600;">Contact Phone:</small><br><span class="badge badge-phone">📞 {phone}</span></div>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <small style="color:#64748B; font-weight:600;">Detected Attributes & Tags:</small><br>
                        {tags_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with p_col2:
            st.subheader("⚡ Fast Actions & CRM")
            
            # Direct WhatsApp Chat Action
            if phone_clean:
                inquiry_msg = f"Assalam-o-Alaikum! Inquiring regarding {size} {p_type} in {city} {phase} {block} (Demand: {price}). From {st.session_state['agency_name']}."
                encoded_msg = urllib.parse.quote(inquiry_msg)
                wa_url = f"https://wa.me/{phone_clean}?text={encoded_msg}"
                st.markdown(f"""
                    <div style="margin-bottom:14px;">
                        <a href="{wa_url}" target="_blank" class="wa-btn" style="width:100%; text-align:center;">
                            💬 Direct WhatsApp Chat ({phone})
                        </a>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("📞 No mobile number detected in listing text.")
                
            # Formatted Listing for WhatsApp Sharing
            branded_listing = f"*{st.session_state['agency_name']}* Exclusive\n" \
                              f"📍 *{city} - {phase} - {block}*\n" \
                              f"🏡 Category: {cat} ({p_type})\n" \
                              f"📏 Size: {size} | Road: {road_width}\n" \
                              f"💰 Demand: {price}\n" \
                              f"🏷️ Features: {', '.join(tags) if tags else 'Standard'}\n" \
                              f"📞 Contact: {phone if phone != 'N/A' else st.session_state['agency_phone']}"
                              
            st.text_area("📋 WhatsApp Branded Copy Text", value=branded_listing, height=140)
            
            target_routing_tab = f"{phase} - {block}"
            st.info(f"🎯 **Target Google Sheet Worksheet Tab**: `{target_routing_tab}`")

        # Save Button
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save & Route to Block Worksheet Tab", type="primary", use_container_width=True):
            tags_str = ", ".join(tags) if tags else "N/A"
            success, sheet_synced, sync_info = save_property_entry(
                source_type, cat, p_type, city, phase, block, size, road_width, tags_str, price, phone, st.session_state["agency_name"], extracted_text
            )
            if success:
                if sheet_synced:
                    st.success(f"✅ Record Successfully Saved to **Local Database** and **Google Sheets** ({sync_info})!")
                else:
                    st.success(f"✅ Record Saved to **Local Inventory**: {phase} • {block} • {size} • {price} *(Offline Mode)*")
                st.balloons()
    else:
        st.info("💡 Paste a listing message above or click one of the quick test presets to view live smart extraction.")

# ---------------------------------------------------------
# VIEW 2: 📊 3-SHEET INVENTORY HUB
# ---------------------------------------------------------
elif app_mode == "📊 3-Sheet Inventory Hub":
    st.subheader("📊 Categorized 3-Sheet Database Hub")
    st.caption("Live block-synchronized inventory split into dedicated Selling, Buying, and Rental views.")
    
    df_all = load_local_data()
    
    # Location Filter Bar
    l1, l2, l3 = st.columns([1, 1, 1])
    with l1:
        unique_cities = ["All Cities"] + list(df_all["City"].dropna().unique()) if len(df_all) > 0 else ["All Cities", "Lahore"]
        filter_city = st.selectbox("Select City", unique_cities)
    with l2:
        unique_phases = ["All Phases"] + list(df_all["Phase"].dropna().unique()) if len(df_all) > 0 else ["All Phases", "Phase 6"]
        filter_phase = st.selectbox("Select Phase", unique_phases)
    with l3:
        unique_blocks = ["All Blocks"] + list(df_all["Block"].dropna().unique()) if len(df_all) > 0 else ["All Blocks", "Block M"]
        filter_block = st.selectbox("Select Block", unique_blocks)

    # Filter base dataset
    df_filtered = df_all.copy()
    if filter_city != "All Cities":
        df_filtered = df_filtered[df_filtered["City"] == filter_city]
    if filter_phase != "All Phases":
        df_filtered = df_filtered[df_filtered["Phase"] == filter_phase]
    if filter_block != "All Blocks":
        df_filtered = df_filtered[df_filtered["Block"] == filter_block]

    tab_selling, tab_buying, tab_rental = st.tabs([
        f"🟢 1. Selling / Available ({len(df_filtered[df_filtered['Category'] == 'Selling']) if len(df_filtered) > 0 else 0})",
        f"🟠 2. Buying / Requirements ({len(df_filtered[df_filtered['Category'] == 'Buying']) if len(df_filtered) > 0 else 0})",
        f"🟣 3. Rental / Leases ({len(df_filtered[df_filtered['Category'] == 'Rental']) if len(df_filtered) > 0 else 0})"
    ])
    
    def render_inventory_view(sub_df, category_title, badge_color):
        if len(sub_df) > 0:
            st.markdown(f"**Showing {len(sub_df)} records in {category_title}**")
            st.dataframe(sub_df, use_container_width=True, height=320)
            
            # Fast Download Options
            d1, d2 = st.columns(2)
            with d1:
                csv_bytes = sub_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download {category_title} (CSV)",
                    data=csv_bytes,
                    file_name=f"dha_{category_title.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with d2:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                    sub_df.to_excel(writer, index=False, sheet_name=category_title[:30])
                st.download_button(
                    label=f"📊 Download {category_title} (Excel .xlsx)",
                    data=buf.getvalue(),
                    file_name=f"dha_{category_title.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.info(f"📭 No active listings found for '{category_title}' matching the selected filters.")

    with tab_selling:
        df_sell = df_filtered[df_filtered["Category"] == "Selling"] if len(df_filtered) > 0 else pd.DataFrame(columns=CSV_COLUMNS)
        render_inventory_view(df_sell, "Selling Inventory", "#10B981")
        
    with tab_buying:
        df_buy = df_filtered[df_filtered["Category"] == "Buying"] if len(df_filtered) > 0 else pd.DataFrame(columns=CSV_COLUMNS)
        render_inventory_view(df_buy, "Buying Requirements", "#F59E0B")
        
    with tab_rental:
        df_rent = df_filtered[df_filtered["Category"] == "Rental"] if len(df_filtered) > 0 else pd.DataFrame(columns=CSV_COLUMNS)
        render_inventory_view(df_rent, "Rental Listings", "#7E22CE")

# ---------------------------------------------------------
# VIEW 3: 🔎 ULTRA-SMART SEARCH
# ---------------------------------------------------------
elif app_mode == "🔎 Ultra-Smart Search":
    st.subheader("🔎 Supreme Ultra-Smart Search")
    st.caption("Search across Phase, Block, Size, Road Width (40ft-MB), and Special Attributes with 1-click WhatsApp CRM.")
    
    df = load_local_data()
    
    if len(df) > 0:
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        with s_col1:
            phase_opts = ["All"] + sorted([str(p) for p in df["Phase"].dropna().unique() if str(p) != "nan"])
            s_phase = st.selectbox("Phase Filter", phase_opts)
        with s_col2:
            block_opts = ["All"] + sorted([str(b) for b in df["Block"].dropna().unique() if str(b) != "nan"])
            s_block = st.selectbox("Block Filter", block_opts)
        with s_col3:
            road_opts = ["All", "40ft Road", "60ft Road", "80ft Road", "100ft Road", "Main Boulevard (150ft)"]
            s_road = st.selectbox("Road Width", road_opts)
        with s_col4:
            search_query = st.text_input("Free Keyword Search", placeholder="e.g. Corner, 4.5 Cr, Park Facing...")
            
        results = df.copy()
        if s_phase != "All":
            results = results[results["Phase"] == s_phase]
        if s_block != "All":
            results = results[results["Block"] == s_block]
        if s_road != "All":
            results = results[results["Road Width"].str.contains(s_road.split()[0], case=False, na=False)]
        if search_query.strip():
            sq = search_query.strip()
            results = results[
                results["Raw Listing Text"].str.contains(sq, case=False, na=False) |
                results["Features"].str.contains(sq, case=False, na=False) |
                results["Price"].str.contains(sq, case=False, na=False) |
                results["Block"].str.contains(sq, case=False, na=False)
            ]
            
        st.markdown(f"**🎯 Found {len(results)} matching properties**")
        st.dataframe(results, use_container_width=True, height=350)
        
        # Action cards for top matches
        st.markdown("### ⚡ Quick Contact & WhatsApp Cards")
        for idx, row in results.head(5).iterrows():
            with st.container():
                st.markdown(f"""
                    <div style="background:white; border-radius:12px; padding:14px 18px; margin-bottom:10px; border:1px solid #E2E8F0; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>📍 {row.get('City', 'Lahore')} • {row.get('Phase', 'Phase')} • {row.get('Block', 'Block')}</strong> | 
                            <span>📏 {row.get('Size', 'N/A')}</span> | 
                            <span style="color:#047857; font-weight:700;">💰 {row.get('Price', 'N/A')}</span> | 
                            <span>🛣️ {row.get('Road Width', 'Standard')}</span> | 
                            <small style="color:#64748B;">🏷️ {row.get('Features', 'N/A')}</small>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📭 No property records in database yet. Add entries in the 'Multimodal Ingestion' tab.")

# ---------------------------------------------------------
# VIEW 4: ⚙️ CLOUD & AGENCY SETTINGS
# ---------------------------------------------------------
elif app_mode == "⚙️ Cloud & Agency Settings":
    st.subheader("⚙️ Google Sheets & System Credentials Manager")
    
    cfg_col1, cfg_col2 = st.columns(2)
    
    with cfg_col1:
        st.markdown("### 📊 Live Connection Status")
        if spreadsheet is not None:
            st.success("🟢 **Google Sheets Connection**: CONNECTED & ACTIVE")
            try:
                sheet_titles = [ws.title for ws in spreadsheet.worksheets()]
                st.info(f"📋 **Spreadsheet Title**: `{spreadsheet.title}`")
                st.caption(f"📁 **Active Dynamic Tabs ({len(sheet_titles)})**: {', '.join(sheet_titles[:10])}...")
            except Exception:
                pass
        else:
            st.warning("🟡 **Google Sheets Connection**: OFFLINE / LOCAL MODE")
            if sheet_err:
                st.caption(f"Status Note: {sheet_err}")
                
        st.markdown("---")
        st.markdown("### 📄 Implementation Plan Spreadsheet")
        st.write("Current project specification & multi-tab implementation plan spreadsheet:")
        if os.path.exists(PLAN_XLSX_PATH):
            with open(PLAN_XLSX_PATH, "rb") as f:
                plan_bytes = f.read()
            st.download_button(
                label="📥 Download Implementation_Plan_DHA_App_Till_Date.xlsx",
                data=plan_bytes,
                file_name="Implementation_Plan_DHA_App_Till_Date.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.caption("✅ Contains 5 tabs: Project_Overview, Feature_Roadmap, Database_Schema, Location_Taxonomy, Sheets_Routing_Logic.")
        
    with cfg_col2:
        st.markdown("### 🔑 Google Service Account JSON Setup")
        st.write("Upload or paste your `service_account.json` to enable automated dynamic Google Sheets routing:")
        
        up_json = st.file_uploader("Upload `service_account.json`", type=["json"])
        raw_json = st.text_area("Or Paste Service Account JSON content here:", height=130, placeholder='{"type": "service_account", "project_id": "...", ...}')
        
        custom_sheet_url = st.text_input("Target Google Spreadsheet URL", value=DEFAULT_SHEET_URL)
        
        if st.button("💾 Save Credentials & Connect Google Sheets", type="primary", use_container_width=True):
            creds_data = None
            if up_json is not None:
                try:
                    creds_data = json.load(up_json)
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")
            elif raw_json.strip():
                try:
                    creds_data = json.loads(raw_json)
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")
                    
            if creds_data:
                try:
                    secrets_content = f'google_sheet_url = "{custom_sheet_url}"\n\n[gcp_service_account]\n'
                    for k, v in creds_data.items():
                        if isinstance(v, str):
                            v_clean = v.replace('"', '\\"').replace('\n', '\\n')
                            secrets_content += f'{k} = "{v_clean}"\n'
                        else:
                            secrets_content += f'{k} = {json.dumps(v)}\n'
                            
                    with open(SECRETS_PATH, "w", encoding="utf-8") as f:
                        f.write(secrets_content)
                        
                    st.success("✅ Credentials saved to `.streamlit/secrets.toml`! Reloading app...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to write secrets: {e}")
            else:
                st.warning("Please upload a file or paste your Service Account JSON first.")

    st.markdown("---")
    st.markdown("""
        ### 📖 3-Step Google Drive & Sheets Setup:
        1. Go to [Google Cloud Console](https://console.cloud.google.com/), create a project, and enable **Google Sheets API** & **Google Drive API**.
        2. Create a Service Account, generate a JSON Key, and upload it above.
        3. Open your Google Sheet and share it with the Service Account email (`client_email`) with **Editor** permissions.
    """)
