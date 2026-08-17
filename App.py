import streamlit as st
import gspread
import re
import json
import io
import os
import time
import math
import urllib.request
import pandas as pd
from datetime import datetime
from PIL import Image
from google.oauth2 import service_account

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Enterprise CRM & Live AI Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Persistent Session States
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"
if "parsed_payloads" not in st.session_state:
    st.session_state["parsed_payloads"] = []
if "extracted_file_text" not in st.session_state:
    st.session_state["extracted_file_text"] = ""
if "uploaded_temp_text" not in st.session_state:
    st.session_state["uploaded_temp_text"] = ""

# Batch Processing State Machine
if "extraction_active" not in st.session_state:
    st.session_state["extraction_active"] = False
if "extraction_paused" not in st.session_state:
    st.session_state["extraction_paused"] = False
if "all_chunks" not in st.session_state:
    st.session_state["all_chunks"] = []
if "current_chunk_idx" not in st.session_state:
    st.session_state["current_chunk_idx"] = 0
if "extraction_default_phase" not in st.session_state:
    st.session_state["extraction_default_phase"] = "DHA Phase 9 Prism"

# Setup Google Gemini AI Client
gemini_client = None
gemini_active = False

api_key_val = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if HAS_GENAI and api_key_val:
    try:
        gemini_client = genai.Client(api_key=api_key_val)
        gemini_active = True
    except Exception:
        gemini_active = False

# 2. CSS Styling
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;600&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
    <style>
    #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }
    .stAppDeployButton { display: none !important; }
    .block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
    .stApp { background-color: #F8FAFB !important; font-family: 'Inter', sans-serif !important; color: #1A1B20 !important; }
    .stitch-navbar { background: #FAFAFF; border-bottom: 1px solid #C5C6D2; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; border-radius: 12px; margin-bottom: 20px; box-shadow: 0px 2px 6px rgba(0, 17, 58, 0.02); }
    .stitch-logo-text { font-family: 'Manrope', sans-serif; font-weight: 700; font-size: 20px; color: #00113A; display: flex; align-items: center; gap: 8px; }
    .header-banner { background: linear-gradient(135deg, #00113A 0%, #102A6B 100%); padding: 20px 24px; border-radius: 14px; color: white; margin-bottom: 20px; box-shadow: 0 8px 20px -5px rgba(0, 17, 58, 0.2); }
    .header-title { font-family: 'Manrope', sans-serif; font-size: 24px; font-weight: 800; margin: 0; color: #FFFFFF; }
    .header-subtitle { color: #B3C5FF; font-size: 13px; margin-top: 4px; }
    .office-badge { background-color: #006B5E; color: #9FF2E1; padding: 5px 12px; border-radius: 16px; font-size: 12px; font-weight: 600; float: right; }
    .stitch-login-box { background: #FFFFFF; border: 1px solid rgba(197, 198, 210, 0.6); border-radius: 16px; box-shadow: 0px 8px 24px rgba(0, 17, 58, 0.04); padding: 32px 28px; margin-bottom: 16px; text-align: center; }
    .stitch-avatar { width: 60px; height: 60px; border-radius: 50%; background-color: #D6E2FF; border: 1px solid #B3C5FF; display: inline-flex; align-items: center; justify-content: center; color: #00113A; margin-bottom: 12px; }
    .summary-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
    .stat-pill { background: #F1F5F9; border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 600; color: #334155; display: inline-block; margin-right: 8px; margin-bottom: 6px; }
    .control-panel-box { background: #FFFFFF; border: 2px solid #00113A; border-radius: 12px; padding: 16px 20px; margin: 15px 0; box-shadow: 0 4px 14px rgba(0,17,58,0.08); }
    .backend-info-card { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 10px; padding: 16px; font-size: 13px; color: #1E293B; line-height: 1.6; }
    .unified-prompt-card { background: #FFFFFF; border: 2px solid #CBD5E1; border-radius: 16px; padding: 16px 18px 14px 18px; margin-bottom: 16px; box-shadow: 0 4px 16px rgba(0, 17, 58, 0.04); }
    .unified-prompt-card:focus-within { border-color: #00113A; }
    .news-badge { display: inline-block; padding: 4px 10px; margin: 3px 2px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; color: #00113A; background: #E2E8F0; border: 1px solid #CBD5E1; }
    .news-badge:hover { background: #D6E2FF; }
    </style>
""", unsafe_allow_html=True)

CRM_SHEET_HEADERS = [
    "Date / Timestamp", "Category", "Phase", "Block", "Plot No",
    "Size", "Plot Features", "Demand / Price", "Seller Type",
    "Seller / Dealer Name", "Contact No", "Office / Agency",
    "Deal Status", "Last Conversation / Notes", "Raw Listing & Source Material"
]

DHA_PHASE_SHEET_URLS = {
    "DHA Phase 1": "https://docs.google.com/spreadsheets/d/11Ns7taFjOJ7CNwyGJpGcSh6wgar3RbEWzUA7uR_N6D8/edit",
    "DHA Phase 2": "https://docs.google.com/spreadsheets/d/1bvmcU_68Oz1LxIjGirSe8p4Y_fUBe75J7UUkAh7wiJc/edit",
    "DHA Phase 3": "https://docs.google.com/spreadsheets/d/1Y7wznstQRPGPYxgpnBOyVPxdN4V869JvEl6fzX981cE/edit",
    "DHA Phase 4": "https://docs.google.com/spreadsheets/d/1YuXlKVO1EoenHzYkxiSUE53_gIS_coOrr9XPcfeSPa4/edit",
    "DHA Phase 5": "https://docs.google.com/spreadsheets/d/1R8OS2MikcqQWRa_MdLa26UjuCb_lmSgoEvKHiNcgS48/edit",
    "DHA Phase 6": "https://docs.google.com/spreadsheets/d/18pl3cuvmDBL0nLq8n04GCuE7dvrsANY_OYtt7a8Zqn4/edit",
    "DHA Phase 7": "https://docs.google.com/spreadsheets/d/1y-JgTuIXDODpqfC4cm-6QxQPCND6Wyq-WOOBDYj9Ysc/edit",
    "DHA Phase 8 (Proper)": "https://docs.google.com/spreadsheets/d/1mHJM1z9g313D90ZpI5toj5l2uBkrPLLlrwW3EIJkBPA/edit",
    "DHA Phase 8 (Ivy Green / Sector Z)": "https://docs.google.com/spreadsheets/d/12ylbY5ZeVKQzeoAM5GadJfrQbSeWNytStSDCRCY93J8/edit",
    "DHA Phase 8 (Park View)": "https://docs.google.com/spreadsheets/d/1QjeNBg63AsG-DdgV_3hj_KN3-1VifEAZW_QgFYoR1rg/edit",
    "DHA Phase 8 (Air Avenue / Sector AA)": "https://docs.google.com/spreadsheets/d/1symBkI9q-KqfBdINU_RIU5JdmvKcmfRvraerVOu73uY/edit",
    "DHA Phase 9 Prism": "https://docs.google.com/spreadsheets/d/1Sfdn1B482sN0IRc1ae31szAs62g8GQ8EqeISF6h5Pb8/edit",
    "DHA Phase 9 Town": "https://docs.google.com/spreadsheets/d/1AfidqzYwWWTkouwBkGKosxyK3CzwAyG8AEilS8-Nd0w/edit",
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": "https://docs.google.com/spreadsheets/d/1bVB4maSRNR_pzcqzVzYKPirePrm_I9Yhu1TqodBPypU/edit",
    "DHA Phase 12 (EME Sector)": "https://docs.google.com/spreadsheets/d/1Ai07OSySM4pcPV9yRr--fsMpKNPXtD2uwJx285_mPho/edit"
}

DHA_CUTTING_MAP_RULES = {
    "DHA Phase 5": {
        "Block A": [(1, 120, "2 Kanal"), (121, 500, "1 Kanal")],
        "Block B": [(1, 80, "2 Kanal"), (81, 600, "1 Kanal")],
        "Block C": [(1, 50, "2 Kanal"), (51, 450, "1 Kanal")],
        "Block G": [(1, 350, "1 Kanal"), (351, 700, "10 Marla")],
        "Block H": [(1, 400, "10 Marla"), (401, 800, "5 Marla")],
        "Block J": [(1, 500, "10 Marla"), (501, 950, "5 Marla")],
    },
    "DHA Phase 6": {
        "Block A": [(1, 150, "2 Kanal"), (151, 800, "1 Kanal")],
        "Block B": [(1, 100, "2 Kanal"), (101, 700, "1 Kanal")],
        "Block C": [(1, 650, "1 Kanal")],
        "Block D": [(1, 700, "1 Kanal")],
        "Block E": [(1, 550, "1 Kanal")],
        "Block J": [(1, 600, "10 Marla")],
        "Block L": [(1, 800, "10 Marla"), (801, 1200, "5 Marla")],
    },
    "DHA Phase 7": {
        "Block P": [(1, 1100, "1 Kanal")],
        "Block Q": [(1, 900, "1 Kanal")],
        "Block R": [(1, 1050, "1 Kanal")],
        "Block S": [(1, 950, "1 Kanal")],
        "Block T": [(1, 1200, "1 Kanal")],
        "Block U": [(1, 1400, "1 Kanal")],
        "Block W": [(1, 1400, "10 Marla")],
        "Block X": [(1, 1300, "10 Marla")],
        "Block Y": [(1, 900, "5 Marla")],
        "Block Z": [(1, 1100, "5 Marla")]
    },
    "DHA Phase 8 (Proper)": {
        "Block A": [(1, 100, "2 Kanal"), (101, 550, "1 Kanal")],
        "Block B": [(1, 80, "2 Kanal"), (81, 500, "1 Kanal")],
        "Block C": [(1, 70, "2 Kanal"), (71, 480, "1 Kanal")],
        "Block D": [(1, 600, "1 Kanal")],
        "Block E": [(1, 550, "1 Kanal")],
        "Block F": [(1, 500, "1 Kanal")],
        "Block S": [(1, 750, "10 Marla")],
        "Block T": [(1, 800, "10 Marla"), (801, 1300, "5 Marla")],
        "Block U": [(1, 900, "5 Marla")],
        "Block V": [(1, 850, "5 Marla")],
        "Block W": [(1, 700, "8 Marla")]
    },
    "DHA Phase 9 Prism": {
        "Block A": [(1, 600, "1 Kanal")],
        "Block B": [(1, 550, "1 Kanal")],
        "Block C": [(1, 700, "1 Kanal")],
        "Block D": [(1, 650, "1 Kanal")],
        "Block E": [(1, 500, "1 Kanal")],
        "Block F": [(1, 700, "1 Kanal")],
        "Block G": [(1, 600, "1 Kanal")],
        "Block J": [(1, 1200, "10 Marla")],
        "Block K": [(1, 1100, "10 Marla")],
        "Block L": [(1, 1300, "10 Marla")],
        "Block R": [(1, 1800, "5 Marla")],
        "Block Q": [(1, 1600, "5 Marla")]
    }
}

DHA_PHASE_BLOCK_CATALOG = {
    "DHA Phase 1": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P"],
        "commercial": ["Block F Commercial", "Block G Commercial", "Block H Commercial", "Block J Commercial", "Block M Commercial", "Sector Shops"]
    },
    "DHA Phase 2": {
        "residential": ["Block Q", "Block R", "Block S", "Block T", "Block U", "Block V"],
        "commercial": ["Commercial CCA", "Block R Commercial", "Block T Commercial", "Sector Shops"]
    },
    "DHA Phase 3": {
        "residential": ["Block W", "Block X", "Block Y", "Block Z", "Block XX"],
        "commercial": ["Y Block Commercial", "Z Block Commercial", "W Block Commercial", "Sector Shops"]
    },
    "DHA Phase 4": {
        "residential": ["Block AA", "Block BB", "Block CC", "Block DD", "Block EE", "Block FF", "Block GG", "Block JJ", "Block KK"],
        "commercial": ["CCA 1 Commercial", "CCA 2 Commercial", "Block DD Commercial", "Sector Shops"]
    },
    "DHA Phase 5": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M"],
        "commercial": ["CCA 1 Commercial", "CCA 2 Commercial", "Sector Shops"]
    },
    "DHA Phase 6": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N"],
        "commercial": ["Main Boulevard (MB) Commercial", "CCA 1 Commercial", "CCA 2 Commercial", "Sector Shops"]
    },
    "DHA Phase 7": {
        "residential": ["Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y", "Block Z", "Block Z-1", "Block Z-2"],
        "commercial": ["CCA 1 Commercial", "CCA 2 Commercial", "CCA 3 Commercial", "CCA 4 Commercial", "Sector Y Commercial", "Sector Shops"]
    },
    "DHA Phase 8 (Proper)": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y"],
        "commercial": ["Broadway Commercial", "Commercial CCA 1", "Commercial CCA 2", "Commercial CCA 3", "Sector Shops"]
    },
    "DHA Phase 8 (Ivy Green / Sector Z)": {
        "residential": ["Block Z-1", "Block Z-2", "Block Z-3", "Block Z-4", "Block Z-5", "Block Z-6"],
        "commercial": ["Commercial CCA Sector Z", "Sector Shops"]
    },
    "DHA Phase 8 (Park View)": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K"],
        "commercial": ["Commercial Zone Park View", "Sector Shops"]
    },
    "DHA Phase 8 (Air Avenue / Sector AA)": {
        "residential": ["Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"],
        "commercial": ["Commercial CCA Air Avenue"]
    },
    "DHA Phase 9 Prism": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"],
        "commercial": ["Zone 1 Commercial", "Zone 2 Commercial", "Zone 3 Commercial", "Main Oval Commercial", "Prism Direct MB Commercial"]
    },
    "DHA Phase 9 Town": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E"],
        "commercial": ["Commercial CCA Phase 9 Town", "Sector Shops"]
    },
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": {
        "residential": ["Sector 1", "Sector 2", "Sector 2 Extension", "Sector 3", "Sector 4", "Sector 5"],
        "commercial": ["Rahbar CCA 1", "Rahbar CCA 2", "Rahbar Sector 5 Commercial", "Sector Shops"]
    },
    "DHA Phase 12 (EME Sector)": {
        "residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J"],
        "commercial": ["Civic Centre EME", "Block D Commercial", "Block H Commercial", "Sector Shops"]
    }
}

def resolve_size_text_first_or_map(phase, block, plot_no, extracted_size):
    cleaned_size = str(extracted_size).strip() if extracted_size else ""
    if cleaned_size and cleaned_size.lower() not in ["n/a", "unknown", "none", ""]:
        return cleaned_size
    try:
        p_num = int(re.sub(r'[^0-9]', '', str(plot_no)))
    except Exception:
        return ""
    phase_rules = DHA_CUTTING_MAP_RULES.get(phase, {})
    block_ranges = phase_rules.get(block, [])
    for start_n, end_n, official_sz in block_ranges:
        if start_n <= p_num <= end_n:
            return official_sz
    return ""

@st.cache_resource
def get_gspread_client():
    if "GCP_SERVICE_ACCOUNT_JSON" in st.secrets:
        json_str = st.secrets["GCP_SERVICE_ACCOUNT_JSON"].strip()
        creds_dict = json.loads(json_str)
    else:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(credentials)

def safe_gspread_call(func, *args, **kwargs):
    retries = 6
    delay = 1.5
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(delay)
            delay *= 1.8

def get_phase_workbook(gc, phase_name):
    target_url = DHA_PHASE_SHEET_URLS.get(phase_name)
    if not target_url:
        target_url = DHA_PHASE_SHEET_URLS["DHA Phase 1"]
    return safe_gspread_call(gc.open_by_url, target_url)

def get_or_create_clean_tab_exact(workbook, tab_title):
    clean_title = tab_title.strip()
    try:
        ws_list = safe_gspread_call(workbook.worksheets)
        for w in ws_list:
            if w.title.strip().lower() == clean_title.lower():
                return w
        ws = safe_gspread_call(workbook.add_worksheet, title=clean_title, rows=500, cols=16)
        safe_gspread_call(ws.append_row, CRM_SHEET_HEADERS)
        return ws
    except Exception:
        return workbook.sheet1

def get_specific_tab_url(workbook, base_url, tab_title):
    clean_title = tab_title.strip().lower()
    try:
        ws_list = safe_gspread_call(workbook.worksheets)
        for w in ws_list:
            if w.title.strip().lower() == clean_title:
                clean_base = base_url.split("#")[0].rstrip("/")
                if not clean_base.endswith("/edit"):
                    clean_base = clean_base + "/edit"
                return f"{clean_base}#gid={w.id}"
    except Exception:
        pass
    return base_url

@st.dialog("🔗 Backend Google Sheets Connection Details", width="large")
def show_backend_connection_dialog(selected_phase, selected_block, target_url):
    st.markdown(f"#### 🏢 Google Sheets Connection Architecture: [{selected_phase}]")
    st.markdown(f"""
        <div class="backend-info-card">
            <b>🔑 Service Account:</b> <code>dha-bot@dha-property-sync.iam.gserviceaccount.com</code><br>
            <b>🌐 Active Spreadsheet Target:</b> <a href="{target_url}" target="_blank">{selected_phase} Database</a><br>
            <b>🧱 Target Tab Attached:</b> <code>{selected_block}</code><br>
            <b>⚡ Sync Protocols:</b> Chunked Append with Exponential Backoff (Quota 429 Protection)<br>
            <b>🛡️ Schema Compliance:</b> 15 Canonical CRM Column Headers strictly mapped.
        </div>
    """, unsafe_allow_html=True)

@st.dialog("👥 Dealer Directory & Market Partner Activity Ledger", width="large")
def show_dealer_ledger_dialog(payloads):
    st.markdown("### 📋 Dealer Market Activity & Circulation Ledger")
    if not payloads:
        st.info("No dealer records loaded in memory yet.")
        return

    dealer_data = []
    for item in payloads:
        contact = item.get("Contact No", "").strip()
        dealer_name = item.get("Seller / Dealer Name", "").strip()
        plot = f"{item.get('Phase', '')} {item.get('Block', '')} - {item.get('Plot No', '')}"
        demand = item.get("Demand / Price", "")
        raw_msg = item.get("Raw Listing & Source Material", "")
        
        dealer_key = contact if contact else (dealer_name if dealer_name else "Unknown Direct")
        dealer_data.append({
            "Dealer / Phone": dealer_key,
            "Plot Option": plot,
            "Demand": demand,
            "Raw Log": raw_msg
        })

    df_dealers = pd.DataFrame(dealer_data)
    if not df_dealers.empty:
        summary_group = df_dealers.groupby("Dealer / Phone").agg(
            Total_Listings=("Plot Option", "count"),
            Active_Demands=("Demand", lambda x: ", ".join([str(v) for v in x if v][:3]))
        ).reset_index().sort_values(by="Total_Listings", ascending=False)

        st.markdown(f"**Total Active Dealers in Memory:** `{len(summary_group)}`")
        st.dataframe(summary_group, use_container_width=True, height=280)
        st.markdown("##### 🔍 Detailed Listing Records per Dealer:")
        st.dataframe(df_dealers, use_container_width=True, height=240)

# ==============================================================================
# SOURCE FETCHERS, 100-MESSAGE CHUNKER & OCR PROCESSORS
# ==============================================================================
def split_raw_into_message_chunks(raw_text, messages_per_chunk=100):
    msg_split_pattern = r'(?=\n?\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4},?\s+\d{1,2}:\d{2})'
    raw_messages = re.split(msg_split_pattern, raw_text)
    
    clean_messages = []
    for msg in raw_messages:
        m_str = msg.strip()
        if not m_str:
            continue
        if "Messages and calls are end-to-end encrypted" in m_str or "<Media omitted>" in m_str or "security code changed" in m_str:
            continue
        clean_messages.append(m_str)
    
    if not clean_messages:
        clean_messages = [l.strip() for l in raw_text.splitlines() if l.strip()]

    chunks = []
    for i in range(0, len(clean_messages), messages_per_chunk):
        chunk_batch = clean_messages[i:i + messages_per_chunk]
        chunks.append("\n\n===MESSAGE_START===\n" + "\n\n===MESSAGE_START===\n".join(chunk_batch))
        
    return chunks

def fetch_content_from_gdrive_url(drive_url):
    file_id_match = re.search(r'[-\w]{25,}', drive_url)
    if not file_id_match:
        return "[Invalid Google Drive URL format]"
    file_id = file_id_match.group(0)
    direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        req = urllib.request.Request(direct_download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            file_bytes = response.read()
            return file_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"[Error fetching from Google Drive: {e}]"

def fetch_text_from_portal_url(url_in):
    if not url_in.startswith("http"):
        url_in = "https://" + url_in
    try:
        req = urllib.request.Request(url_in, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8', errors='ignore')
            text_only = re.sub(r'<[^>]+>', ' ', html)
            text_clean = re.sub(r'\s+', ' ', text_only).strip()
            return f"[Source: {url_in}]\n" + text_clean[:30000]
    except Exception as e:
        return f"[Error connecting to Portal URL: {e}]"

def extract_text_from_any_file_or_image(file_obj, is_camera=False):
    if file_obj is None:
        return ""
    file_bytes = file_obj.getvalue()
    
    if is_camera or (hasattr(file_obj, 'name') and any(file_obj.name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])):
        if gemini_active and gemini_client:
            try:
                img = Image.open(io.BytesIO(file_bytes))
                res = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        "Extract all DHA Lahore property listings, newspaper classified ads, phases, blocks, plot numbers, sizes, and demand prices from this image:",
                        img
                    ]
                )
                return res.text.strip()
            except Exception as e:
                return f"[Image OCR extraction error: {e}]"
        else:
            return "[Image loaded. Add GEMINI_API_KEY to secrets to extract live OCR]"

    fname = file_obj.name.lower() if hasattr(file_obj, 'name') else "file.txt"
    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        try:
            excel_df = pd.read_excel(io.BytesIO(file_bytes))
            return excel_df.to_string(index=False)
        except Exception as e:
            return f"[Error reading Excel file: {e}]"
    elif fname.endswith(".csv"):
        try:
            csv_df = pd.read_csv(io.BytesIO(file_bytes))
            return csv_df.to_string(index=False)
        except Exception as e:
            return f"[Error reading CSV file: {e}]"
    elif fname.endswith(".json"):
        try:
            json_data = json.loads(file_bytes.decode('utf-8', errors='ignore'))
            return json.dumps(json_data, indent=2)
        except Exception as e:
            return f"[Error reading JSON file: {e}]"
    elif fname.endswith(".pdf"):
        if HAS_PYPDF:
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pdf_text = [p.extract_text() for p in reader.pages if p.extract_text()]
                return "\n".join(pdf_text)
            except Exception as e:
                return f"[Error reading PDF: {e}]"
        else:
            return "[pypdf not installed]"

    return file_bytes.decode('utf-8', errors='ignore')

# ==============================================================================
# ROBUST BACKUP REGEX PARSER (FALLBACK)
# ==============================================================================
def clean_line_from_artifacts(l):
    return re.sub(r'[*_~`]', ' ', l).strip()

def detect_phase_from_header(line_up):
    if "PHASE 12" in line_up or "EME" in line_up:
        return "DHA Phase 12 (EME Sector)"
    elif "PHASE 11" in line_up or "RAHBAR" in line_up:
        return "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)"
    elif "IVY GREEN" in line_up or "SECTOR Z" in line_up:
        return "DHA Phase 8 (Ivy Green / Sector Z)"
    elif "9PRISM" in line_up or "9 PRISM" in line_up or "PRISM" in line_up:
        return "DHA Phase 9 Prism"
    elif "9TOWN" in line_up or "9 TOWN" in line_up:
        return "DHA Phase 9 Town"
    elif "PHASE 8" in line_up or "PH 8" in line_up:
        return "DHA Phase 8 (Proper)"
    elif "PHASE 7" in line_up or "PH 7" in line_up:
        return "DHA Phase 7"
    elif "PHASE 6" in line_up or "PH 6" in line_up:
        return "DHA Phase 6"
    elif "PHASE 5" in line_up or "PH 5" in line_up:
        return "DHA Phase 5"
    elif "PHASE 4" in line_up or "PH 4" in line_up:
        return "DHA Phase 4"
    elif "PHASE 3" in line_up or "PH 3" in line_up:
        return "DHA Phase 3"
    elif "PHASE 2" in line_up or "PH 2" in line_up:
        return "DHA Phase 2"
    elif "PHASE 1" in line_up or "PH 1" in line_up:
        return "DHA Phase 1"
    return
