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

# Batch Processing & Pause/Resume State Machine
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
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
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
    .ai-badge-active { background: #DCFCE7; border: 1px solid #86EFAC; color: #15803D; font-size: 12.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }
    .ai-badge-inactive { background: #FEF3C7; border: 1px solid #FCD34D; color: #B45309; font-size: 12.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }
    .summary-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
    .stat-pill { background: #F1F5F9; border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 600; color: #334155; display: inline-block; margin-right: 8px; margin-bottom: 6px; }
    .control-panel-box { background: #FFFFFF; border: 2px solid #00113A; border-radius: 12px; padding: 16px 20px; margin: 15px 0; box-shadow: 0 4px 14px rgba(0,17,58,0.08); }
    .backend-info-card { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 10px; padding: 16px; font-size: 13px; color: #1E293B; line-height: 1.6; }
    
    .unified-prompt-card {
        background: #FFFFFF;
        border: 2px solid #CBD5E1;
        border-radius: 16px;
        padding: 16px 18px 12px 18px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0, 17, 58, 0.04);
    }
    .unified-prompt-card:focus-within {
        border-color: #00113A;
    }
    </style>
""", unsafe_allow_html=True)

CRM_SHEET_HEADERS = [
    "Date / Timestamp",
    "Category",
    "Phase",
    "Block",
    "Plot No",
    "Size",
    "Plot Features",
    "Demand / Price",
    "Seller Type",
    "Seller / Dealer Name",
    "Contact No",
    "Office / Agency",
    "Deal Status",
    "Last Conversation / Notes",
    "Raw Listing & Source Material"
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
        st.info("No dealer records loaded in memory yet. Ingest WhatsApp logs, portals, or classifieds to populate.")
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

def clean_whatsapp_chat_text(raw_bytes):
    try:
        decoded_text = raw_bytes.decode('utf-8', errors='ignore')
    except Exception:
        try:
            decoded_text = raw_bytes.decode('latin-1', errors='ignore')
        except Exception:
            decoded_text = str(raw_bytes)

    chat_patterns = [
        r'^\s*\[?\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\]?\s*-?\s*[^:]+:\s*',
        r'^\s*\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*-\s*[^:]+:\s*'
    ]

    cleaned_lines = []
    for line in decoded_text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        if "Messages and calls are end-to-end encrypted" in line_str or "<Media omitted>" in line_str:
            continue
        
        for pat in chat_patterns:
            line_str = re.sub(pat, '', line_str)
        
        line_str = line_str.strip()
        if line_str and len(line_str) > 2:
            cleaned_lines.append(line_str)

    return "\n".join(cleaned_lines)

def fetch_content_from_gdrive_url(drive_url):
    file_id_match = re.search(r'[-\w]{25,}', drive_url)
    if not file_id_match:
        return "[Invalid Google Drive URL format]"
    
    file_id = file_id_match.group(0)
    direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        req = urllib.request.Request(
            direct_download_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            file_bytes = response.read()
            return clean_whatsapp_chat_text(file_bytes)
    except Exception as e:
        return f"[Error fetching from Google Drive: {e}]"

def fetch_text_from_portal_url(url_in):
    if not url_in.startswith("http"):
        url_in = "https://" + url_in
    try:
        req = urllib.request.Request(
            url_in,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
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
                        "Extract all DHA Lahore property listings, phases, blocks, plot numbers, sizes, and demand prices from this image:",
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

    return clean_whatsapp_chat_text(file_bytes)

def process_single_chunk_via_gemini(chunk_text, default_phase):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    prompt = f"""You are an expert DHA Lahore Real Estate CRM extraction engine.
Extract EVERY single individual property listing from the provided text into a JSON array of objects.

OFFICIAL DHA PHASES:
'DHA Phase 1', 'DHA Phase 2', 'DHA Phase 3', 'DHA Phase 4', 'DHA Phase 5', 'DHA Phase 6', 'DHA Phase 7', 'DHA Phase 8 (Proper)', 'DHA Phase 8 (Ivy Green / Sector Z)', 'DHA Phase 8 (Park View)', 'DHA Phase 8 (Air Avenue / Sector AA)', 'DHA Phase 9 Prism', 'DHA Phase 9 Town', 'DHA Phase 11 (Rahbar 1 to 4 & Sec 5)', 'DHA Phase 12 (EME Sector)'.

OFFICIAL DHA CATALOG BLOCKS:
{catalog_json_str}

STRICT EXTRACTION RULES:
1. "Phase": Identify the phase from context/headers or fallback to '{default_phase}'.
2. "Block": Must match the official block name (e.g. 'Block A', 'Block W', 'CCA 1 Commercial', 'Broadway Commercial').
3. "Plot No": Extract the COMPLETE full plot number exactly as written (e.g. 'Plot 980', 'Plot 1008', 'Plot 432', 'Plot 654'). DO NOT cut off digits!
4. "Demand / Price": Extract full demand (e.g. '585 Lac', '440 Lac', '3.8 Crore'). If no price is mentioned, leave as "". NEVER invent '0 Lac'.
5. "Size": If size is explicitly mentioned ('5 Marla', '10 Marla', '1 Kanal', '2 Kanal', '8 Marla', '4 Marla', '13 Marla'), write it. If not mentioned in message, leave as "".
6. "Plot Features": Extract features like 'Corner', 'Park Facing', 'Corner / Park Facing', 'Main Boulevard (MB)', 'Direct Option', 'Possession Plot', 'Non-Possession'. Otherwise 'Standard Layout'.
7. "Contact No": Extract valid Pakistani phone number from line/section if available, else "".
8. "Raw Listing & Source Material": Copy the exact line from input text.

Input Text:
{chunk_text}

Return ONLY a valid JSON Array with format:
[
  {{
    "Category": "Selling",
    "Phase": "DHA Phase 9 Prism",
    "Block": "Block A",
    "Plot No": "Plot 980",
    "Size": "1 Kanal",
    "Plot Features": "Corner / Facing Park",
    "Demand / Price": "585 Lac",
    "Seller Type": "Dealer",
    "Seller / Dealer Name": "",
    "Contact No": "",
    "Office / Agency": "Wali Muhammad Associates",
    "Deal Status": "Available",
    "Last Conversation / Notes": "Direct Ingestion",
    "Raw Listing & Source Material": "A 980 corner f park"
  }}
]"""

    if gemini_active and gemini_client:
        for retry in range(3):
            try:
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                parsed_json = json.loads(response.text)
                if isinstance(parsed_json, list):
                    for item in parsed_json:
                        item["Size"] = resolve_size_text_first_or_map(
                            item.get("Phase", default_phase),
                            item.get("Block", "Block A"),
                            item.get("Plot No", ""),
                            item.get("Size", "")
                        )
                    return parsed_json
            except Exception:
                time.sleep(1.0)

    return fallback_regex_tokenizer(chunk_text, default_phase)

def fallback_regex_tokenizer(text_chunk, default_phase):
    lines = [l.strip() for l in text_chunk.splitlines() if l.strip()]
    phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', text_chunk)
    main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else ""
    
    current_phase = default_phase
    extracted = []
    
    for line in lines:
        l_up = line.upper()
        if "PHASE 12" in l_up or "EME" in l_up:
            current_phase = "DHA Phase 12 (EME Sector)"
        elif "PHASE 11" in l_up or "RAHBAR" in l_up:
            current_phase = "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)"
        elif "PHASE 9 PRISM" in l_up or "PRISM" in l_up:
            current_phase = "DHA Phase 9 Prism"
        elif "PHASE 9 TOWN" in l_up or "9 TOWN" in l_up:
            current_phase = "DHA Phase 9 Town"
        elif "PHASE 8" in l_up:
            current_phase = "DHA Phase 8 (Proper)"
        elif "PHASE 7" in l_up:
            current_phase = "DHA Phase 7"
        elif "PHASE 6" in l_up:
            current_phase = "DHA Phase 6"
        elif "PHASE 5" in l_up:
            current_phase = "DHA Phase 5"
        elif "PHASE 4" in l_up:
            current_phase = "DHA Phase 4"
        elif "PHASE 3" in l_up:
            current_phase = "DHA Phase 3"
        elif "PHASE 2" in l_up:
            current_phase = "DHA Phase 2"
        elif "PHASE 1" in l_up:
            current_phase = "DHA Phase 1"

        line_sz = ""
        if "10 MARLA" in l_up or "10M" in l_up:
            line_sz = "10 Marla"
        elif "5 MARLA" in l_up or "5M" in l_up or "5.5 MARLA" in l_up:
            line_sz = "5 Marla"
        elif "2 KANAL" in l_up or "2K" in l_up:
            line_sz = "2 Kanal"
        elif "1 KANAL" in l_up or "1K" in l_up:
            line_sz = "1 Kanal"

        feat = "Standard Layout"
        if "CORNER" in l_up and "PARK" in l_up:
            feat = "Corner / Park Facing"
        elif "CORNER" in l_up:
            feat = "Corner"
        elif "PARK" in l_up:
            feat = "Facing Park"

        m = re.search(r'(?:BLOCK\s*)?([A-Z0-9-]{1,4})\s*[-.:/# ]\s*([0-9]{1,5})(?:\s*[@:]\s*|\s+DEMAND\s*[:@]?\s*|\s+@\s*|\s+)?([0-9]{2,5}(?:\.[0-9]+)?)?\s*(LAC|LACS|CRORE|CR)?', l_up)
        if m:
            blk_raw = m.group(1).upper()
            blk = f"Block {blk_raw}" if not blk_raw.startswith("BLOCK") else blk_raw
            plt_num = m.group(2)
            raw_prc = m.group(3)
            prc_unit = m.group(4) if m.group(4) else "Lac"
            prc = f"{raw_prc} {prc_unit}".strip() if (raw_prc and float(raw_prc) > 5) else ""

            extracted.append({
                "Category": "Selling",
                "Phase": current_phase,
                "Block": blk,
                "Plot No": f"Plot {plt_num}",
                "Size": line_sz,
                "Plot Features": feat,
                "Demand / Price": prc,
                "Seller Type": "Dealer",
                "Seller / Dealer Name": "",
                "Contact No": main_phone,
                "Office / Agency": st.session_state["office_name"],
                "Deal Status": "Available",
                "Last Conversation / Notes": "Direct Ingestion",
                "Raw Listing & Source Material": line
            })
    return extracted

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
                <div class="stitch-title">Welcome to DHA</div>
                <div class="stitch-subtitle">Clinical & Property CRM Data Systems</div>
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
        if st.button("🔑 CONTINUE WITH SINGLE SIGN-ON (SSO)", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "sso.agent@dha.pk"
            st.rerun()

# 9. Main Clean Live Summary Dashboard
else:
    try:
        gc_client = get_gspread_client()
    except Exception as e:
        st.error(f"⚠️ Google Sheets Authentication Error: {e}")
        st.stop()

    # Header with Dealer Directory Trigger Button
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
        if st.button("👥 Dealer Ledger & Directory", use_container_width=True):
            show_dealer_ledger_dialog(st.session_state.get("parsed_payloads", []))

    # Top DHA Phase Switcher & Dynamic Tab Selection
    col_city, col_phase = st.columns([1.2, 2.5])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Multan", "Gujranwala"])
    with col_phase:
        phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
        selected_phase = st.selectbox("📍 Select DHA Phase (Active Workbook View)", phase_options, index=11)

    sheet_base_link = DHA_PHASE_SHEET_URLS.get(selected_phase, "")

    p_info = DHA_PHASE_BLOCK_CATALOG.get(selected_phase, {})
    res_b = p_info.get("residential", [])
    com_b = p_info.get("commercial", [])
    all_phase_blocks = res_b + com_b

    st.markdown(f"##### 🧱 Choose Block Sheet Tab for **[{selected_phase}]**:")
    
    selected_active_block = st.radio(
        "Direct Block Switcher:",
        options=all_phase_blocks,
        horizontal=True,
        key="block_feature_tab_bar"
    )

    try:
        active_wb = get_phase_workbook(gc_client, selected_phase)
        exact_block_tab_url = get_specific_tab_url(active_wb, sheet_base_link, selected_active_block)
    except Exception:
        exact_block_tab_url = sheet_base_link

    col_btn_info, col_btn_sheet = st.columns([1.5, 2.5])
    with col_btn_info:
        if st.button("ℹ️ Connection Details & Architecture", use_container_width=True):
            show_backend_connection_dialog(selected_phase, selected_active_block, exact_block_tab_url)

    with col_btn_sheet:
        st.link_button(
            f"📑 Open [{selected_active_block}] Tab in Google Sheets ↗",
            url=exact_block_tab_url,
            use_container_width=True
        )

    st.markdown("---")

    # Live-Streaming Summary Report Workspace
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
        selected_summary_phase = st.selectbox(
            "📍 Filter / Target Phase:",
            options=all_dha_phases_summary,
            index=0,
            key="summary_target_phase_select"
        )

    if selected_summary_phase == "All Phases (Everything)":
        available_summary_tabs = ["All Block Tabs / CCAs"] + (sorted(list(df_all_live["Target Tab"].unique())) if total_parsed_now > 0 else [])
        df_filtered_summary_phase = df_all_live
    else:
        p_data = DHA_PHASE_BLOCK_CATALOG.get(selected_summary_phase, {})
        full_catalog_blocks = p_data.get("residential", []) + p_data.get("commercial", [])
        available_summary_tabs = ["All Block Tabs / CCAs"] + full_catalog_blocks
        df_filtered_summary_phase = df_all_live[df_all_live["Target Phase"] == selected_summary_phase] if total_parsed_now > 0 else df_all_live

    with col_sc3:
        selected_summary_block = st.selectbox(
            "🧱 Filter / Target Block:",
            options=available_summary_tabs,
            index=0,
            key="summary_target_block_select"
        )

    if selected_summary_block != "All Block Tabs / CCAs" and total_parsed_now > 0:
        df_final_summary_display = df_filtered_summary_phase[df_filtered_summary_phase["Target Tab"] == selected_summary_block]
    else:
        df_final_summary_display = df_filtered_summary_phase

    with col_sc4:
        st.metric(label="📊 Plots In View", value=f"{len(df_final_summary_display)}", delta=f"{total_parsed_now} Total Loaded")

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
            <span class="stat-pill">⚡ <b>Total Extracted So Far:</b> {total_parsed_now} Listings</span>
        </div>
    """, unsafe_allow_html=True)

    if total_parsed_now > 0:
        if edit_summary_mode:
            st.info("💡 **Edit Mode Active:** Modify cells or delete rows. Only rows shown below will push to Google Sheets.")
            final_summary_df = st.data_editor(
                df_final_summary_display,
                use_container_width=True,
                num_rows="dynamic",
                height=280,
                key="summary_active_live_editor"
            )
        else:
            final_summary_df = df_final_summary_display
            st.dataframe(final_summary_df, use_container_width=True, height=280)
    else:
        final_summary_df = df_final_summary_display
        st.info("ℹ️ Summary workspace is ready. Paste text or attach sources below and click **'🚀 ➔ Start AI Extraction'**.")

    final_sync_count_live = len(final_summary_df)
    col_pb1, col_pb2 = st.columns([2, 1])
    with col_pb1:
        if st.button(f"🚀 Push ({final_sync_count_live} Filtered Plots) to Sheet Tabs", use_container_width=True, disabled=(final_sync_count_live == 0)):
            now_dt = datetime.now()
            today_str = now_dt.strftime("%Y-%m-%d")
            now_str = now_dt.strftime("%Y-%m-%d %H:%M")
            
            grouped_data = {}
            for _, row in final_summary_df.iterrows():
                target_phase = str(row.get("Target Phase", "DHA Phase 1")).strip()
                target_block = str(row.get("Target Tab", "Block A")).strip()
                key = (target_phase, target_block)
                if key not in grouped_data:
                    grouped_data[key] = []
                grouped_data[key].append(row)
            
            saved_count = 0
            repeated_tracked = 0
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
                
                try:
                    existing_rows = safe_gspread_call(ws.get_all_values)
                except Exception:
                    existing_rows = []
                
                if len(existing_rows) == 0:
                    safe_gspread_call(ws.append_row, CRM_SHEET_HEADERS)
                
                plot_repeat_map = {}
                if len(existing_rows) > 1:
                    for r in existing_rows[1:]:
                        r_plot = str(r[4]).strip().lower() if len(r) > 4 else ""
                        if r_plot:
                            plot_repeat_map[r_plot] = plot_repeat_map.get(r_plot, 0) + 1
                
                rows_to_append = []
                for row in rows_list:
                    plot_val = str(row.get("Plot No", "")).strip()
                    plot_val_clean = plot_val.lower()
                    
                    repeat_count = plot_repeat_map.get(plot_val_clean, 0)
                    notes_txt = "Direct Ingestion"
                    if repeat_count > 0:
                        repeated_tracked += 1
                        notes_txt = f"🔁 Repeated {repeat_count + 1} times this month"
                    
                    plot_repeat_map[plot_val_clean] = repeat_count + 1
                    
                    row_data = [
                        str(now_str),
                        str(row.get("Category", "Selling")),
                        str(phase),
                        str(block),
                        str(plot_val),
                        str(row.get("Size", "")),
                        str(row.get("Plot Features", "Standard Layout")),
                        str(row.get("Demand / Price", "")),
                        "Dealer",
                        "",
                        str(row.get("Contact No", "")),
                        str(st.session_state['office_name']),
                        "Available",
                        str(notes_txt),
                        f"[AI Ingest] {str(row.get('Source Text', ''))}"
                    ]
                    rows_to_append.append(row_data)
                
                CHUNK_SIZE = 50
                for i in range(0, len(rows_to_append), CHUNK_SIZE):
                    chunk_slice = rows_to_append[i:i + CHUNK_SIZE]
                    safe_gspread_call(ws.append_rows, chunk_slice, value_input_option="USER_ENTERED")
                    saved_count += len(chunk_slice)
                    time.sleep(0.4)
                
                progress_bar_sync.progress((idx + 1) / total_groups)
                time.sleep(0.3)
            
            status_placeholder_sync.empty()
            progress_bar_sync.empty()
            st.success(f"🎉 **Push Complete!** Successfully saved ALL **{saved_count} listings** directly to Google Sheets! (0 Records Lost • Repeats Tracked: **{repeated_tracked}**)")
            st.balloons()

    with col_pb2:
        if st.button("🗑️ Clear Extracted Summary Data", use_container_width=True):
            st.session_state["parsed_payloads"] = []
            st.session_state["extraction_active"] = False
            st.session_state["extraction_paused"] = False
            st.rerun()

    st.markdown("---")

    # Unified All-in-One Ingestion Prompt Enclosure
    if gemini_active:
        st.markdown('<div class="ai-badge-active">🟢 Google Gemini AI Extraction Engine: Connected & Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ai-badge-inactive">🟡 Gemini API Key Missing — Operating on Fallback Pattern Parser (Add GEMINI_API_KEY to Secrets for full AI power)</div>', unsafe_allow_html=True)

    st.subheader("🧠 Multi-Source Data Ingestion Engine")
    
    default_box_value = st.session_state.get("extracted_file_text", "")

    st.markdown('<div class="unified-prompt-card">', unsafe_allow_html=True)
    
    raw_text = st.text_area(
        "📋 Live Real Estate Ingestion Stream:",
        value=default_box_value,
        height=260,
        placeholder="Paste thousands of WhatsApp chat messages, portal feeds, or use [+] Attach Sources below...",
        label_visibility="collapsed"
    )

    col_in_attach, col_in_btn = st.columns([3.6, 1.4])
    
    with col_in_attach:
        with st.expander("➕ **Attach Sources (Files, Drive, OCR, Zameen, Classifieds)**", expanded=False):
            tab_upload, tab_gdrive, tab_camera, tab_direct, tab_zameen, tab_news = st.tabs([
                "📎 Files", "☁️ G-Drive", "📸 Camera", "📋 Direct", "🌐 Zameen", "📰 Classifieds"
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
                                st.session_state["extracted_file_text"] = extracted_content
                                st.success(f"✅ Loaded `{uploaded_file.name}` into box!")
                        except Exception as e:
                            st.error(f"Error reading file: {e}")

            with tab_gdrive:
                gdrive_url_in = st.text_input("Paste Google Drive Link:", placeholder="https://drive.google.com/...", key="inner_gdrive_in")
                if st.button("☁️ Push G-Drive File Data", use_container_width=True, key="btn_push_gdrive_inner"):
                    if gdrive_url_in.strip():
                        with st.spinner("Fetching and cleaning timestamps..."):
                            gdrive_content = fetch_content_from_gdrive_url(gdrive_url_in.strip())
                            if gdrive_content and not gdrive_content.startswith("[Error"):
                                st.session_state["extracted_file_text"] = gdrive_content
                                st.success("✅ Google Drive data loaded!")
                            else:
                                st.error(gdrive_content)

            with tab_camera:
                camera_photo = st.camera_input("Take photo of property listing/document:", key="inner_cam_in")
                if camera_photo is not None:
                    with st.spinner("🧠 Scanning document via Google Vision OCR..."):
                        camera_text = extract_text_from_any_file_or_image(camera_photo, is_camera=True)
                        if camera_text:
                            st.session_state["extracted_file_text"] = camera_text
                            st.success("✅ Camera OCR loaded!")

            with tab_direct:
                pasted_txt = st.text_area("Paste Raw WhatsApp Broadcasts or Text:", height=80, placeholder="Paste text...", key="inner_paste_in")
                if st.button("📥 Push Pasted Text", use_container_width=True, key="btn_push_direct_inner"):
                    if pasted_txt.strip():
                        st.session_state["extracted_file_text"] = pasted_txt.strip()
                        st.success("✅ Direct text loaded!")

            with tab_zameen:
                portal_url = st.text_input("Paste Zameen / Portal Listing URL:", placeholder="https://www.zameen.com/...", key="inner_portal_in")
                if st.button("🌐 Scrape & Ingest Portal Link", use_container_width=True, key="btn_push_portal_inner"):
                    if portal_url.strip():
                        with st.spinner("Connecting and extracting portal property feed..."):
                            portal_raw = fetch_text_from_portal_url(portal_url.strip())
                            st.session_state["extracted_file_text"] = portal_raw
                            st.success("✅ Portal content fetched into box!")
                    else:
                        st.warning("Please provide a valid property portal URL.")

            with tab_news:
                news_txt = st.text_area("Paste Newspaper Classified Ads Text (Jang, Dawn, etc.):", height=80, placeholder="Paste newspaper ads...", key="inner_news_in")
                if st.button("📰 Ingest Classified Ads", use_container_width=True, key="btn_push_news_inner"):
                    if news_txt.strip():
                        st.session_state["extracted_file_text"] = f"[Classified Ads Source]\n" + news_txt.strip()
                        st.success("✅ Classified ads loaded!")

    with col_in_btn:
        if not st.session_state["extraction_active"]:
            st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 ➔ Start AI Extraction", use_container_width=True, key="btn_run_stream_inner"):
                final_input_text = raw_text.strip()
                if final_input_text:
                    all_lines = [l.strip() for l in final_input_text.splitlines() if l.strip()]
                    LINES_PER_CHUNK = 60
                    chunks = ["\n".join(all_lines[i:i+LINES_PER_CHUNK]) for i in range(0, len(all_lines), LINES_PER_CHUNK)]
                    
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
                    ⚡ Live AI Streaming: Processing Chunk {curr_idx + 1} of {total_chunks} • Streamed: {total_parsed_now} Listings into Summary
                </div>
            </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1.2])
        with col_p1:
            if not st.session_state["extraction_paused"]:
                if st.button("⏸️ Pause Extraction", use_container_width=True):
                    st.session_state["extraction_paused"] = True
                    st.rerun()
            else:
                if st.button("▶️ Resume Extraction", use_container_width=True):
                    st.session_state["extraction_paused"] = False
                    st.rerun()
                    
        with col_p2:
            if st.button("⏹️ Stop & Keep Extracted Data", use_container_width=True):
                st.session_state["extraction_active"] = False
                st.session_state["extraction_paused"] = False
                st.rerun()

        with col_p3:
            if st.button("❌ Cancel / Reset", use_container_width=True):
                st.session_state["extraction_active"] = False
                st.session_state["extraction_paused"] = False
                st.session_state["parsed_payloads"] = []
                st.rerun()

        if not st.session_state["extraction_paused"] and curr_idx < total_chunks:
            with st.spinner(f"🧠 AI Gemini Processing Chunk {curr_idx + 1} of {total_chunks}..."):
                chunk_to_process = chunks[curr_idx]
                new_listings = process_single_chunk_via_gemini(chunk_to_process, st.session_state["extraction_default_phase"])
                st.session_state["parsed_payloads"].extend(new_listings)
                st.session_state["current_chunk_idx"] += 1
                
                if st.session_state["current_chunk_idx"] >= total_chunks:
                    st.session_state["extraction_active"] = False
                    st.session_state["extraction_paused"] = False
                    st.success(f"🎉 100% Complete! Extracted {len(st.session_state['parsed_payloads'])} listings into summary workspace.")
                    st.rerun()
                else:
                    st.rerun()
