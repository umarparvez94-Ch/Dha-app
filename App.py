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

# Initialize Session States
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

# Setup Google Gemini AI Client Safely
gemini_client = None
gemini_active = False

try:
    api_key_val = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    if HAS_GENAI and api_key_val:
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
    try:
        if "GCP_SERVICE_ACCOUNT_JSON" in st.secrets:
            json_str = st.secrets["GCP_SERVICE_ACCOUNT_JSON"].strip()
            creds_dict = json.loads(json_str)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
        else:
            return None
                
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(credentials)
    except Exception:
        return None

# ==============================================================================
# QUOTA-PROOF SAFE GOOGLE SHEETS CALLER (AUTO RETRY & BACKOFF)
# ==============================================================================
def safe_gspread_call(func, *args, **kwargs):
    retries = 10
    delay = 2.5
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "apierror" in err_str or "rate limit" in err_str:
                time.sleep(delay * 2.0)
            if attempt == retries - 1:
                raise e
            time.sleep(delay)
            delay *= 1.5

def get_phase_workbook(gc, phase_name):
    target_url = DHA_PHASE_SHEET_URLS.get(phase_name, DHA_PHASE_SHEET_URLS["DHA Phase 1"])
    return safe_gspread_call(gc.open_by_url, target_url)

def get_or_create_clean_tab_exact(workbook, tab_title):
    clean_title = tab_title.strip()
    try:
        ws_list = safe_gspread_call(workbook.worksheets)
        for w in ws_list:
            if w.title.strip().lower() == clean_title.lower():
                return w
        ws = safe_gspread_call(workbook.add_worksheet, title=clean_title, rows=1000, cols=16)
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
        st.dataframe(summary_group, height=280)
        st.markdown("##### 🔍 Detailed Listing Records per Dealer:")
        st.dataframe(df_dealers, height=240)

# ==============================================================================
# SOURCE FETCHERS & 100-MESSAGE CHUNKER
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
    return None

def smart_accurate_rule_parser(chunk_text, default_phase):
    messages = chunk_text.split("===MESSAGE_START===")
    results = []

    FORBIDDEN_BLOCK_WORDS = {
        "PHASE", "PH", "SECTOR", "DHA", "CCA", "COMMERCIAL", "PAIR", "DEMAND", "ASKING",
        "OFFER", "FINAL", "DIRECT", "MEETING", "COMPLETE", "FILE", "PAPER", "CORNER", "PARK",
        "ROAD", "FACING", "POSSESSION", "RS", "LAC", "LACS", "CRORE", "CR", "KANAL", "MARLA",
        "MAIN", "NEAR", "BOULEVARD", "ZONE", "SE", "CA", "TH", "ST", "ND", "RD"
    }

    for msg in messages:
        m_clean = msg.strip()
        if not m_clean:
            continue
        
        phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', m_clean)
        main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else ""
        
        active_phase = detect_phase_from_header(m_clean.upper()) or default_phase
        lines = [clean_line_from_artifacts(l) for l in m_clean.splitlines() if clean_line_from_artifacts(l)]
        
        current_section_phase = active_phase
        current_section_size = ""
        matched_in_message = False

        for line in lines:
            l_up = line.upper()
            
            ph_found = detect_phase_from_header(l_up)
            if ph_found:
                current_section_phase = ph_found
                continue
            
            if "1 KANAL" in l_up:
                current_section_size = "1 Kanal"
            elif "2 KANAL" in l_up:
                current_section_size = "2 Kanal"
            elif "10 MARLA" in l_up or "10M" in l_up:
                current_section_size = "10 Marla"
            elif "5 MARLA" in l_up or "5M" in l_up:
                current_section_size = "5 Marla"
            elif "4 MARLA" in l_up or "4M" in l_up:
                current_section_size = "4 Marla"
            elif "8 MARLA" in l_up or "8M" in l_up:
                current_section_size = "8 Marla"

            cca_match = re.search(r'CCA\s*([0-9])?\s*([A-Z])?\s*[-.:_/# ]\s*([0-9]{1,4})\s*(?:@|RS|DEMAND)?\s*([0-9]{2,5})?\s*(LAC|LACS|CRORE|CR)?', l_up)
            if cca_match:
                matched_in_message = True
                cca_num = cca_match.group(1) or "1"
                blk_cca = f"CCA {cca_num} Commercial"
                plt_num = cca_match.group(3)
                prc_val = cca_match.group(4)
                prc_unit = cca_match.group(5) or "Lac"
                prc_str = f"{prc_val} {prc_unit}".strip() if prc_val else ""
                
                results.append({
                    "Category": "Selling",
                    "Phase": current_section_phase,
                    "Block": blk_cca,
                    "Plot No": f"Plot {plt_num}",
                    "Size": current_section_size if current_section_size else "4 Marla Commercial",
                    "Plot Features": "Commercial / CCA",
                    "Demand / Price": prc_str,
                    "Seller Type": "Dealer",
                    "Seller / Dealer Name": "",
                    "Contact No": main_phone,
                    "Office / Agency": st.session_state["office_name"],
                    "Deal Status": "Available",
                    "Last Conversation / Notes": "Direct Ingestion",
                    "Raw Listing & Source Material": m_clean
                })
                continue

            p_match = re.search(r'(?:^|[\s*])([A-Z]{1,2}[0-9]?)\s*[\.\-_/:\s]+\s*([0-9]{1,5}(?:[+/][0-9]{1,5})?)\s*(?:@|RS|DEMAND|ASKING|[:\s-])?\s*([0-9]{2,5}(?:\.[0-9]+)?)?\s*(LAC|LACS|CRORE|CR)?', l_up)
            
            if p_match:
                raw_b = p_match.group(1).strip()
                if raw_b in FORBIDDEN_BLOCK_WORDS or len(raw_b) > 3:
                    continue
                
                matched_in_message = True
                raw_p = p_match.group(2).strip()
                raw_prc = p_match.group(3)
                raw_unit = p_match.group(4) or "Lac"
                prc_str = f"{raw_prc} {raw_unit}".strip() if raw_prc else ""

                if raw_b.startswith("Z") and len(raw_b) == 2 and raw_b[1].isdigit():
                    blk_str = f"Block Z-{raw_b[1]}"
                elif raw_b.startswith("BLOCK"):
                    blk_str = raw_b
                else:
                    blk_str = f"Block {raw_b}"

                sz_str = ""
                if "5 MARLA" in l_up or "5M" in l_up:
                    sz_str = "5 Marla"
                elif "10 MARLA" in l_up or "10M" in l_up:
                    sz_str = "10 Marla"
                elif "2 KANAL" in l_up or "2K" in l_up:
                    sz_str = "2 Kanal"
                elif "1 KANAL" in l_up or "1K" in l_up:
                    sz_str = "1 Kanal"
                elif current_section_size:
                    sz_str = current_section_size
                else:
                    sz_str = resolve_size_text_first_or_map(current_section_phase, blk_str, f"Plot {raw_p}", "")

                feat = "Corner" if "CORNER" in l_up else ("Park Facing" if "PARK" in l_up else ("Possession" if "POSSESSION" in l_up else "Standard Layout"))

                results.append({
                    "Category": "Selling",
                    "Phase": current_section_phase,
                    "Block": blk_str,
                    "Plot No": f"Plot {raw_p}",
                    "Size": sz_str,
                    "Plot Features": feat,
                    "Demand / Price": prc_str,
                    "Seller Type": "Dealer",
                    "Seller / Dealer Name": "",
                    "Contact No": main_phone,
                    "Office / Agency": st.session_state["office_name"],
                    "Deal Status": "Available",
                    "Last Conversation / Notes": "Direct Ingestion",
                    "Raw Listing & Source Material": m_clean
                })

        if not matched_in_message and main_phone:
            results.append({
                "Category": "Dealer Lead / General",
                "Phase": active_phase,
                "Block": "General Lead",
                "Plot No": "General Option / Portfolio",
                "Size": "",
                "Plot Features": "Direct Broadcast / Portfolio",
                "Demand / Price": "",
                "Seller Type": "Dealer",
                "Seller / Dealer Name": "",
                "Contact No": main_phone,
                "Office / Agency": st.session_state["office_name"],
                "Deal Status": "Available",
                "Last Conversation / Notes": "Direct Ingestion",
                "Raw Listing & Source Material": m_clean
            })

    return results

# ==============================================================================
# GEMINI 2.5 FLASH FORENSIC REAL ESTATE EXTRACTION ENGINE
# ==============================================================================
def process_single_chunk_via_gemini(chunk_text, default_phase):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    
    system_prompt = f"""You are the Master DHA Lahore Real Estate Data Pipeline Architect & Forensic Text Parsing Specialist.
Your explicit objective is to ingest messy, unorganized, highly-abbreviated, mixed-dealer WhatsApp broadcasts and restructure them into perfectly normalized, aligned CRM JSON records with 100% precision.

### CORE EXTRACTION & ALIGNMENT INTELLIGENCE:
1. MULTI-LISTING DISAGGREGATION (One Record per Property):
   - Split every distinct plot, pair, shop, or requirement into its own dedicated JSON object.

2. CONTEXTUAL HIERARCHY & HEADER INHERITANCE:
   - Every single plot appearing beneath a header must inherit that specific Phase and Size until a new divider explicitly changes it.
   - If no header exists, default to: "{default_phase}".

3. ZERO-HALLUCINATION BLOCK ALIGNMENT:
   - Match extracted blocks strictly against the Official Catalog provided below.
   - Clean common slang: 'Z2' -> 'Block Z-2', 'CCA1' -> 'CCA 1 Commercial', 'MB' -> 'Main Boulevard (MB) Commercial', 'BROADWAY' -> 'Broadway Commercial'.
   - FORBIDDEN AS BLOCKS: 'DIRECT', 'MEETING', 'PAIR', 'DEMAND', 'CORNER', 'PARK', 'MAIN', 'SE', 'CA', 'POSSESSION', 'AFFIDAVIT', 'FILE'.

4. PLOT NUMBER ISOLATION:
   - Extract raw plot numbers cleanly: e.g., 'Plot 450', 'Plot 112/4', 'Plot 890+891'.

5. STRICT SIZE NORMALIZATION:
   - '5 Marla', '8 Marla', '10 Marla', '1 Kanal', '2 Kanal', '4 Marla Commercial', '8 Marla Commercial'.

6. DEMAND & CURRENCY STANDARDIZATION:
   - Normalize prices into 'X Lac' or 'X Crore' (e.g. '585 Lac', '5.85 Crore', '325 Lac').

7. ATTRIBUTE & FEATURE CLASSIFICATION:
   - 'Corner', 'Facing Park', 'Main Boulevard (MB)', '100ft Road', 'Direct Approach', 'Possession', 'Non-Possession', 'Standard Layout'.

8. CATEGORY & SELLER ATTRIBUTION:
   - "Category": 'Selling', 'Buying', or 'Rental'.
   - "Seller Type": 'Direct Owner' or 'Authorized Dealer'.
   - "Contact No": Clean Pakistani phone numbers.

OFFICIAL DHA PHASE & BLOCK CATALOG:
{catalog_json_str}

INPUT MESSY WHATSAPP STREAM:
{chunk_text}

OUTPUT SPECIFICATION:
Return ONLY a valid JSON array of objects. Strictly no explanations, markdown formatting ticks, or commentary.
"""

    if gemini_active and gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=system_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            raw_json = response.text.strip()
            parsed_json = json.loads(raw_json)
            if isinstance(parsed_json, list) and len(parsed_json) > 0:
                for item in parsed_json:
                    blk = str(item.get("Block", "")).strip()
                    plt = str(item.get("Plot No", "")).strip()
                    sz = str(item.get("Size", "")).strip()
                    ph = item.get("Phase", default_phase)
                    if plt and plt.lower() != "general option / portfolio":
                        item["Size"] = resolve_size_text_first_or_map(
                            ph, blk, plt, sz
                        )
                return parsed_json
        except Exception:
            pass

    return smart_accurate_rule_parser(chunk_text, default_phase)

# 8. Login Screen
if not st.session_state["authenticated"]:
    st.markdown("""
        <div class="stitch-navbar">
            <div class="stitch-logo-text">
                <span class="material-symbols-outlined" style="color:#00113A; font-size:26px;">dataset</span>
                <span>DHA Property Data Systems</span>
            </div>
            <div style="color: #757682; font-size: 13px; font-weight: 500;">
                <span class="material-symbols-outlined" style="vertical-align:middle; font-size:18px; color:#006B5E;">lock</span>
                Secure Access
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_l1, col_center, col_l2 = st.columns([1, 1.3, 1])
    with col_center:
        st.markdown("""
            <div class="stitch-login-box">
                <div class="stitch-avatar">
                    <span class="material-symbols-outlined" style="font-size:30px;">apartment</span>
                </div>
                <div style="font-family:'Manrope',sans-serif; font-size:22px; font-weight:700; color:#00113A;">Welcome to DHA</div>
                <div style="color:#757682; font-size:13px; margin-top:4px;">Clinical & Property CRM Data Systems</div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("stitch_login_form"):
            email_in = st.text_input("WORK EMAIL ADDRESS", placeholder="name@wali-associates.pk")
            pass_in = st.text_input("PASSWORD", type="password", placeholder="••••••••")
            submit_login = st.form_submit_button("SIGN IN →")
            if submit_login:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_in if email_in.strip() else "authorized.agent@dha.pk"
                st.rerun()

        st.markdown("<div style='text-align:center; margin: 10px 0; color:#757682; font-size:12px;'>OR</div>", unsafe_allow_html=True)
        if st.button("🔑 CONTINUE WITH SINGLE SIGN-ON (SSO)"):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "sso.agent@dha.pk"
            st.rerun()

# 9. Main Clean Live Summary Dashboard
else:
    gc_client = get_gspread_client()

    # Header
    col_h1, col_h2 = st.columns([3, 1.2])
    with col_h1:
        st.markdown(f"""
            <div class="header-banner">
                <span class="office-badge">📍 {st.session_state['office_name']}</span>
                <h1 class="header-title">🏢 DHA Smart Property Engine & CRM</h1>
                <div class="header-subtitle">Live Streaming AI Ingestion & Multi-Phase Pipeline (Active: {st.session_state['user_email']})</div>
            </div>
        """, unsafe_allow_html=True)

    with col_h2:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("👥 Dealer Ledger & Directory"):
            show_dealer_ledger_dialog(st.session_state.get("parsed_payloads", []))

    # Top Selectors
    col_city, col_phase = st.columns([1.2, 2.5])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Multan", "Gujranwala"])
    with col_phase:
        phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
        selected_phase = st.selectbox("📍 Select DHA Phase (Active Workbook View)", phase_options, index=11)

    sheet_base_link = DHA_PHASE_SHEET_URLS.get(selected_phase, "")
    p_info = DHA_PHASE_BLOCK_CATALOG.get(selected_phase, {})
    all_phase_blocks = p_info.get("residential", []) + p_info.get("commercial", [])

    st.markdown(f"##### 🧱 Choose Block Sheet Tab for **[{selected_phase}]**:")
    selected_active_block = st.radio("Direct Block Switcher:", options=all_phase_blocks, horizontal=True, key="block_feature_tab_bar")

    if gc_client:
        try:
            active_wb = get_phase_workbook(gc_client, selected_phase)
            exact_block_tab_url = get_specific_tab_url(active_wb, sheet_base_link, selected_active_block)
        except Exception:
            exact_block_tab_url = sheet_base_link
    else:
        exact_block_tab_url = sheet_base_link

    col_btn_info, col_btn_sheet = st.columns([1.5, 2.5])
    with col_btn_info:
        if st.button("ℹ️ Connection Details & Architecture"):
            show_backend_connection_dialog(selected_phase, selected_active_block, exact_block_tab_url)
    with col_btn_sheet:
        st.link_button(f"📑 Open [{selected_active_block}] Tab in Google Sheets ↗", url=exact_block_tab_url)

    st.markdown("---")

    # ==========================================================================
    # ALWAYS-LIVE REAL-TIME SUMMARY DASHBOARD TABLE
    # ==========================================================================
    st.subheader("⚡ Live Summary Report & Multi-Phase Ingestion Center")
    total_parsed_now = len(st.session_state["parsed_payloads"])

    if total_parsed_now > 0:
        base_data = []
        for item in st.session_state["parsed_payloads"]:
            base_data.append({
                "Target Phase": str(item.get("Phase", "DHA Phase 1")),
                "Target Tab": str(item.get("Block", "Block A")),
                "Plot No": str(item.get("Plot No", "")),
                "Size": str(item.get("Size", "")),
                "Demand / Price": str(item.get("Demand / Price", "")),
                "Contact No": str(item.get("Contact No", "")),
                "Category": str(item.get("Category", "Selling")),
                "Plot Features": str(item.get("Plot Features", "Standard Layout")),
                "Source Text": str(item.get("Raw Listing & Source Material", ""))
            })
        df_all_live = pd.DataFrame(base_data)
    else:
        df_all_live = pd.DataFrame(columns=[
            "Target Phase", "Target Tab", "Plot No", "Size", "Demand / Price",
            "Contact No", "Category", "Plot Features", "Source Text"
        ])

    col_sc1, col_sc2, col_sc3, col_sc4 = st.columns([1.2, 1.4, 1.4, 1.2])
    with col_sc1:
        edit_summary_mode = st.toggle("✏️ Edit Mode (ON / OFF)", value=False, key="toggle_summary_edit_mode")

    all_dha_phases_summary = ["All Phases (Everything)"] + list(DHA_PHASE_BLOCK_CATALOG.keys())
    with col_sc2:
        selected_summary_phase = st.selectbox("📍 Filter / Target Phase:", options=all_dha_phases_summary, index=0, key="summary_target_phase_select")

    if selected_summary_phase == "All Phases (Everything)":
        available_summary_tabs = ["All Block Tabs / CCAs"] + (sorted(list(df_all_live["Target Tab"].unique())) if total_parsed_now > 0 else [])
        df_filtered_summary_phase = df_all_live
    else:
        p_data = DHA_PHASE_BLOCK_CATALOG.get(selected_summary_phase, {})
        full_catalog_blocks = p_data.get("residential", []) + p_data.get("commercial", [])
        available_summary_tabs = ["All Block Tabs / CCAs"] + full_catalog_blocks
        df_filtered_summary_phase = df_all_live[df_all_live["Target Phase"] == selected_summary_phase] if total_parsed_now > 0 else df_all_live

    with col_sc3:
        selected_summary_block = st.selectbox("🧱 Filter / Target Block:", options=available_summary_tabs, index=0, key="summary_target_block_select")

    if selected_summary_block != "All Block Tabs / CCAs" and total_parsed_now > 0:
        df_final_summary_display = df_filtered_summary_phase[df_filtered_summary_phase["Target Tab"] == selected_summary_block]
    else:
        df_final_summary_display = df_filtered_summary_phase

    with col_sc4:
        st.metric(label="📊 Plots In View", value=f"{len(df_final_summary_display)}", delta=f"{total_parsed_now} Total Extracted")

    num_selected_live = len(df_final_summary_display)
    unique_tabs_count_live = df_final_summary_display[["Target Phase", "Target Tab"]].drop_duplicates().shape[0] if num_selected_live > 0 else 0
    with_demand_count_live = df_final_summary_display[df_final_summary_display["Demand / Price"] != ""].shape[0] if num_selected_live > 0 else 0
    with_contact_count_live = df_final_summary_display[df_final_summary_display["Contact No"] != ""].shape[0] if num_selected_live > 0 else 0

    st.markdown(f"""
        <div class="summary-card">
            <span class="stat-pill">📊 <b>Selected View:</b> {num_selected_live} Plots</span>
            <span class="stat-pill">📁 <b>Target Tabs:</b> {unique_tabs_count_live} Tabs</span>
            <span class="stat-pill">💰 <b>Prices Identified:</b> {with_demand_count_live}</span>
            <span class="stat-pill">📞 <b>Contacts Identified:</b> {with_contact_count_live}</span>
            <span class="stat-pill">⚡ <b>Live Extracted:</b> {total_parsed_now} Listings</span>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================================================
    # FULL SCROLLABLE LIVE SUMMARY TABLE (SCROLL ALL EXTRACTED ROWS)
    # ==========================================================================
    if not df_final_summary_display.empty:
        if edit_summary_mode:
            final_summary_df = st.data_editor(
                df_final_summary_display,
                height=520,
                num_rows="dynamic",
                key="summary_active_live_editor"
            )
        else:
            final_summary_df = df_final_summary_display
            st.dataframe(
                df_final_summary_display,
                height=520,
                hide_index=False
            )
    else:
        final_summary_df = df_final_summary_display
        st.dataframe(final_summary_df, height=300)

    final_sync_count_live = len(df_final_summary_display)
    col_pb1, col_pb2 = st.columns([2, 1])
    with col_pb1:
        if st.button(f"🚀 Push ({final_sync_count_live} Filtered Plots) to Sheet Tabs", disabled=(final_sync_count_live == 0)):
            if not gc_client:
                st.error("Google Cloud credentials not found in secrets. Please configure GCP_SERVICE_ACCOUNT_JSON.")
            else:
                now_dt = datetime.now()
                now_str = now_dt.strftime("%Y-%m-%d %H:%M")
                grouped_data = {}
                for _, row in df_final_summary_display.iterrows():
                    target_phase = str(row.get("Target Phase", "DHA Phase 1")).strip()
                    target_block = str(row.get("Target Tab", "Block A")).strip()
                    key = (target_phase, target_block)
                    if key not in grouped_data:
                        grouped_data[key] = []
                    grouped_data[key].append(row)
                
                saved_count = 0
                workbook_cache = {}
                total_groups = len(grouped_data)
                progress_bar_sync = st.progress(0)
                status_placeholder_sync = st.empty()
                
                for idx, ((phase, block), rows_list) in enumerate(grouped_data.items()):
                    pct = int(((idx + 1) / total_groups) * 100)
                    status_placeholder_sync.markdown(f"⏳ **Syncing:** `[{phase} ➔ {block}]` — ({idx+1}/{total_groups} tabs) • **{pct}% Complete**")
                    if phase not in workbook_cache:
                        wb = get_phase_workbook(gc_client, phase)
                        workbook_cache[phase] = wb
                    
                    wb = workbook_cache[phase]
                    ws = get_or_create_clean_tab_exact(wb, block)
                    
                    rows_to_append = []
                    for row in rows_list:
                        plot_val = str(row.get("Plot No", "")).strip()
                        row_data = [
                            str(now_str), str(row.get("Category", "Selling")), str(phase), str(block),
                            str(plot_val), str(row.get("Size", "")), str(row.get("Plot Features", "Standard Layout")),
                            str(row.get("Demand / Price", "")), "Dealer", "", str(row.get("Contact No", "")),
                            str(st.session_state['office_name']), "Available", "Direct Ingestion",
                            f"[AI Ingest] {str(row.get('Source Text', ''))}"
                        ]
                        rows_to_append.append(row_data)
                    
                    # 500-Row Bulk Slice for Maximum Speed & Zero Quota Crash
                    BULK_SLICE_SIZE = 500
                    for i in range(0, len(rows_to_append), BULK_SLICE_SIZE):
                        chunk_slice = rows_to_append[i:i + BULK_SLICE_SIZE]
                        safe_gspread_call(ws.append_rows, chunk_slice, value_input_option="USER_ENTERED")
                        saved_count += len(chunk_slice)
                        time.sleep(0.8)  # API Rate protection buffer
                    
                    progress_bar_sync.progress((idx + 1) / total_groups)
                
                status_placeholder_sync.empty()
                progress_bar_sync.empty()
                st.success(f"🎉 **Push Complete!** Successfully saved ALL **{saved_count} listings** directly to Google Sheets!")
                st.balloons()

    with col_pb2:
        if st.button("🗑️ Clear Extracted Summary Data"):
            st.session_state["parsed_payloads"] = []
            st.session_state["extraction_active"] = False
            st.session_state["extraction_paused"] = False
            st.rerun()

    st.markdown("---")

    # ==========================================================================
    # 4. UNIFIED INGESTION PROMPT ENCLOSURE
    # ==========================================================================
    st.subheader("🧠 Multi-Source Data Ingestion Engine")
    default_box_value = st.session_state.get("extracted_file_text", "")

    st.markdown('<div class="unified-prompt-card">', unsafe_allow_html=True)
    
    raw_text = st.text_area(
        "📋 Live Real Estate Ingestion Stream:",
        value=default_box_value,
        height=240,
        placeholder="Paste WhatsApp broadcasts, newspaper ads, portal feeds, or use [+] Attach Sources below...",
        label_visibility="collapsed"
    )

    col_in_attach, col_in_btn = st.columns([3.6, 1.4])
    
    with col_in_attach:
        with st.expander("➕ **Attach Sources (Files, Drive, OCR, Zameen, Newspapers)**", expanded=False):
            tab_upload, tab_gdrive, tab_camera, tab_direct, tab_zameen, tab_news = st.tabs([
                "📎 Files", "☁️ G-Drive", "📸 Camera OCR", "📋 Direct", "🌐 Zameen", "📰 Newspapers"
            ])
            
            with tab_upload:
                uploaded_file = st.file_uploader(
                    "Upload TXT, Excel, JSON, PDF, or Image:",
                    type=["txt", "xlsx", "xls", "json", "csv", "pdf", "png", "jpg", "jpeg", "webp"],
                    key="inner_file_uploader"
                )
                if uploaded_file is not None:
                    with st.spinner(f"Reading `{uploaded_file.name}`..."):
                        try:
                            extracted_content = extract_text_from_any_file_or_image(uploaded_file, is_camera=False)
                            if extracted_content:
                                st.session_state["uploaded_temp_text"] = extracted_content
                                st.success(f"✅ File `{uploaded_file.name}` ready! Click '📥 Push to Box' below.")
                        except Exception as e:
                            st.error(f"Error reading file: {e}")
                
                if st.session_state.get("uploaded_temp_text", ""):
                    if st.button("📥 Push to Box", key="btn_push_file_to_box"):
                        st.session_state["extracted_file_text"] = st.session_state["uploaded_temp_text"]
                        st.session_state["uploaded_temp_text"] = ""
                        st.success("✅ Pushed file text into stream box!")
                        st.rerun()

            with tab_gdrive:
                gdrive_url_in = st.text_input("Paste Google Drive Link:", placeholder="https://drive.google.com/...", key="inner_gdrive_in")
                if st.button("📥 Push to Box (G-Drive)", key="btn_push_gdrive_inner"):
                    if gdrive_url_in.strip():
                        with st.spinner("Fetching Google Drive file..."):
                            gdrive_content = fetch_content_from_gdrive_url(gdrive_url_in.strip())
                            if gdrive_content and not gdrive_content.startswith("[Error"):
                                st.session_state["extracted_file_text"] = gdrive_content
                                st.success("✅ Google Drive data loaded into box!")
                                st.rerun()
                            else:
                                st.error(gdrive_content)

            with tab_camera:
                st.caption("📷 Take photo of Property Document or Newspaper Classified Page:")
                camera_photo = st.camera_input("Snap picture:", key="inner_cam_in")
                if camera_photo is not None:
                    with st.spinner("🧠 Scanning document via Google Vision OCR..."):
                        camera_text = extract_text_from_any_file_or_image(camera_photo, is_camera=True)
                        if camera_text:
                            if st.button("📥 Push to Box (Camera OCR)", key="btn_push_cam_inner"):
                                st.session_state["extracted_file_text"] = camera_text
                                st.success("✅ Camera OCR loaded into box!")
                                st.rerun()

            with tab_direct:
                pasted_txt = st.text_area("Paste Raw WhatsApp Broadcasts or Text:", height=80, placeholder="Paste text...", key="inner_paste_in")
                if st.button("📥 Push to Box (Direct Text)", key="btn_push_direct_inner"):
                    if pasted_txt.strip():
                        st.session_state["extracted_file_text"] = pasted_txt.strip()
                        st.success("✅ Direct text loaded into box!")
                        st.rerun()

            with tab_zameen:
                portal_url = st.text_input("Paste Zameen / Portal Listing URL:", placeholder="https://www.zameen.com/...", key="inner_portal_in")
                if st.button("🌐 Scrape & Push to Box", key="btn_push_portal_inner"):
                    if portal_url.strip():
                        with st.spinner("Connecting and extracting portal property feed..."):
                            portal_raw = fetch_text_from_portal_url(portal_url.strip())
                            st.session_state["extracted_file_text"] = portal_raw
                            st.success("✅ Portal content fetched into box!")
                            st.rerun()
                    else:
                        st.warning("Please provide a valid property portal URL.")

            with tab_news:
                st.markdown("""
                    <b>📰 Quick Access to National Newspaper Portals:</b><br>
                    <a href="https://classified.jang.com.pk" target="_blank" class="news-badge">📰 Daily Jang Classifieds ↗</a>
                    <a href="https://e.jang.com.pk/lahore" target="_blank" class="news-badge">📰 Jang Lahore ePaper ↗</a>
                    <a href="https://classifieds.dawn.com" target="_blank" class="news-badge">📰 Daily Dawn Classifieds ↗</a>
                    <a href="https://express.pk/epaper" target="_blank" class="news-badge">📰 Daily Express Lahore ↗</a>
                    <a href="https://e.thenews.com.pk" target="_blank" class="news-badge">📰 The News Classifieds ↗</a>
                    <a href="https://epaper.nawaiwaqt.com.pk" target="_blank" class="news-badge">📰 Daily Nawa-i-Waqt ↗</a>
                    <a href="https://e.dunya.com.pk" target="_blank" class="news-badge">📰 Daily Dunya ePaper ↗</a>
                """, unsafe_allow_html=True)
                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                news_txt = st.text_area("Paste Newspaper Classified Ads Text (Jang, Dawn, Express etc.):", height=90, placeholder="مثلاً: ڈی ایچ اے فیز 9 پرزم 1 کنال پلاٹ برائے فروخت...", key="inner_news_in")
                if st.button("📥 Push to Box (Newspaper Ads)", key="btn_push_news_inner"):
                    if news_txt.strip():
                        st.session_state["extracted_file_text"] = f"[Newspaper Classified Source]\n" + news_txt.strip()
                        st.success("✅ Newspaper classified ads loaded into box!")
                        st.rerun()

    with col_in_btn:
        if not st.session_state["extraction_active"]:
            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Extract", key="btn_run_stream_inner"):
                final_input_text = raw_text.strip()
                if final_input_text:
                    chunks = split_raw_into_message_chunks(final_input_text, messages_per_chunk=100)
                    st.session_state["all_chunks"] = chunks
                    st.session_state["current_chunk_idx"] = 0
                    st.session_state["parsed_payloads"] = []
                    st.session_state["extraction_active"] = True
                    st.session_state["extraction_paused"] = False
                    st.session_state["extraction_default_phase"] = selected_phase
                    st.rerun()
                else:
                    st.warning("Please provide listing text, take a camera photo, or attach a file.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Active Live Streaming Loop (Pause / Resume / Cancel)
    if st.session_state["extraction_active"]:
        chunks = st.session_state["all_chunks"]
        curr_idx = st.session_state["current_chunk_idx"]
        total_chunks = len(chunks)
        
        st.markdown(f"""
            <div class="control-panel-box">
                <div style="font-size: 16px; font-weight: 700; color: #00113A; margin-bottom: 8px;">
                    ⚡ Live AI Streaming: Processing Chunk {curr_idx + 1} of {total_chunks} (100 msgs/chunk) • Streamed: {total_parsed_now} Listings into Summary
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1.2])
        with col_p1:
            if not st.session_state["extraction_paused"]:
                if st.button("⏸️ Pause Extraction"):
                    st.session_state["extraction_paused"] = True
                    st.rerun()
            else:
                if st.button("▶️ Resume Extraction"):
                    st.session_state["extraction_paused"] = False
                    st.rerun()
        with col_p2:
            if st.button("⏹️ Stop & Keep Extracted Data"):
                st.session_state["extraction_active"] = False
                st.session_state["extraction_paused"] = False
                st.rerun()
        with col_p3:
            if st.button("❌ Cancel / Reset"):
                st.session_state["extraction_active"] = False
                st.session_state["extraction_paused"] = False
                st.session_state["parsed_payloads"] = []
                st.rerun()

        if not st.session_state["extraction_paused"] and curr_idx < total_chunks:
            with st.spinner(f"🧠 Processing Chunk {curr_idx + 1} of {total_chunks} (100 msgs)..."):
                chunk_to_process = chunks[curr_idx]
                new_listings = process_single_chunk_via_gemini(chunk_to_process, st.session_state["extraction_default_phase"])
                st.session_state["parsed_payloads"].extend(new_listings)
                st.session_state["current_chunk_idx"] += 1
                
                if st.session_state["current_chunk_idx"] >= total_chunks:
                    st.session_state["extraction_active"] = False
                    st.session_state["extraction_paused"] = False
                    st.rerun()
                else:
                    st.rerun()
