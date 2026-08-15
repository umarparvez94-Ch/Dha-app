import streamlit as st
import gspread
import re
import json
import io
import os
import time
import urllib.request
import pandas as pd
from datetime import datetime
from PIL import Image

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
    page_title="DHA Enterprise CRM & Smart AI Engine",
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
if "synced_plots_history" not in st.session_state:
    st.session_state["synced_plots_history"] = set()

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
    .property-card { background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 5px; font-size: 11.5px; font-weight: 700; margin-right: 5px; }
    .badge-selling { background-color: #FEE2E2; color: #DC2626; }
    .badge-price { background-color: #ECFDF5; color: #059669; font-weight: 800; }
    .badge-repeat { background-color: #FEF3C7; color: #B45309; font-weight: 700; }
    .badge-feature { background-color: #EEF2FF; color: #4338CA; font-weight: 600; }
    .ai-badge-active { background: #DCFCE7; border: 1px solid #86EFAC; color: #15803D; font-size: 12.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }
    .ai-badge-inactive { background: #FEF3C7; border: 1px solid #FCD34D; color: #B45309; font-size: 12.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }
    .summary-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
    .stat-pill { background: #F1F5F9; border-radius: 6px; padding: 6px 12px; font-size: 13px; font-weight: 600; color: #334155; display: inline-block; margin-right: 8px; margin-bottom: 6px; }
    .eta-box { background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 10px 14px; margin: 10px 0; color: #166534; font-size: 13px; }
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
    creds_dict = dict(st.secrets["gcp_service_account"])
    return gspread.service_account_from_dict(creds_dict)

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
        # If not found, create new tab
        ws = safe_gspread_call(workbook.add_worksheet, title=clean_title, rows=500, cols=16)
        safe_gspread_call(ws.append_row, CRM_SHEET_HEADERS)
        return ws
    except Exception:
        return workbook.sheet1

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

def parse_with_strict_gemini_schema(raw_text, default_phase):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    chunk_size = 10000
    text_chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]
    all_results = []

    for chunk in text_chunks:
        prompt = f"""You are an expert DHA Lahore Real Estate CRM extraction engine.
Parse the text into a clean JSON list of individual property listings.

CRITICAL RULES:
1. Official Phases: 'DHA Phase 1', 'DHA Phase 2', 'DHA Phase 3', 'DHA Phase 4', 'DHA Phase 5', 'DHA Phase 6', 'DHA Phase 7', 'DHA Phase 8 (Proper)', 'DHA Phase 8 (Ivy Green / Sector Z)', 'DHA Phase 8 (Park View)', 'DHA Phase 8 (Air Avenue / Sector AA)', 'DHA Phase 9 Prism', 'DHA Phase 9 Town', 'DHA Phase 11 (Rahbar 1 to 4 & Sec 5)', 'DHA Phase 12 (EME Sector)'.
2. Block names MUST strictly match catalog: {catalog_json_str}.
3. SIZE RULE: Extract EXACT size if stated in text ('5 Marla', '10 Marla', '1 Kanal', '2 Kanal', '8 Marla', '4 Marla', '13 Marla', '28 Marla'). If NO size is stated in message, leave "Size" as empty string "". DO NOT assume or force 1 Kanal.
4. Extract exact Plot No, Demand / Price, Plot Features (Corner, Park Face, MB, Direct, Possession, Non-Possession), Seller / Dealer Name, and Contact No without dummy fillers.

Input Raw Text:
{chunk}

Return ONLY a valid JSON Array with format:
[
  {{
    "Category": "Selling",
    "Phase": "DHA Phase 7",
    "Block": "Block U",
    "Plot No": "Plot 398",
    "Size": "",
    "Plot Features": "Standard Layout",
    "Demand / Price": "720 Lac",
    "Seller Type": "Dealer",
    "Seller / Dealer Name": "",
    "Contact No": "",
    "Office / Agency": "Wali Muhammad Associates",
    "Deal Status": "Available",
    "Last Conversation / Notes": "Direct WhatsApp Ingestion",
    "Raw Listing & Source Material": "398 U 720 Lac"
  }}
]"""

        chunk_parsed = False
        if gemini_active and gemini_client:
            try:
                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                parsed = json.loads(response.text)
                if isinstance(parsed, list):
                    for item in parsed:
                        item["Size"] = resolve_size_text_first_or_map(
                            item.get("Phase", default_phase),
                            item.get("Block", "Block A"),
                            item.get("Plot No", ""),
                            item.get("Size", "")
                        )
                    all_results.extend(parsed)
                    chunk_parsed = True
            except Exception:
                pass

        if not chunk_parsed:
            all_results.extend(parse_fallback_heuristic(chunk, default_phase))

    return all_results

def parse_fallback_heuristic(text_clean, default_phase):
    lines = [l.strip() for l in text_clean.split('\n') if l.strip()]
    phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', text_clean)
    main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else ""
    
    current_phase = default_phase
    current_size = ""
    extracted = []
    
    for line in lines:
        l_up = line.upper()
        if "PHASE 12" in l_up or "EME" in l_up:
            current_phase = "DHA Phase 12 (EME Sector)"
            continue
        elif "PHASE 11" in l_up or "RAHBAR" in l_up:
            current_phase = "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)"
            continue
        elif "PHASE 9 PRISM" in l_up or "PRISM" in l_up:
            current_phase = "DHA Phase 9 Prism"
            continue
        elif "PHASE 9 TOWN" in l_up or "9 TOWN" in l_up:
            current_phase = "DHA Phase 9 Town"
            continue
        elif "PHASE 8" in l_up:
            current_phase = "DHA Phase 8 (Proper)"
            continue
        elif "PHASE 7" in l_up:
            current_phase = "DHA Phase 7"
            continue
        elif "PHASE 6" in l_up:
            current_phase = "DHA Phase 6"
            continue
        elif "PHASE 5" in l_up:
            current_phase = "DHA Phase 5"
            continue
        elif "PHASE 4" in l_up:
            current_phase = "DHA Phase 4"
            continue
        elif "PHASE 3" in l_up:
            current_phase = "DHA Phase 3"
            continue
        elif "PHASE 2" in l_up:
            current_phase = "DHA Phase 2"
            continue
        elif "PHASE 1" in l_up:
            current_phase = "DHA Phase 1"
            continue

        m = re.search(r'([A-Z0-9-]{1,3})\s*[-.:/ ]\s*([0-9]{1,5})\s*(?:@|\bDEMAND\b:?)?\s*(\d+\.?\d*)\s*(?:[.]?(LAC|LACS|CRORE|CR))?', l_up)
        if m:
            blk = f"Block {m.group(1).upper()}"
            plt = f"Plot {m.group(2)}"
            prc = f"{m.group(3)} {m.group(4) if m.group(4) else 'Lac'}".strip() if m.group(3) else ""
            final_sz = resolve_size_text_first_or_map(current_phase, blk, plt, current_size)
            
            extracted.append({
                "Category": "Selling",
                "Phase": current_phase,
                "Block": blk,
                "Plot No": plt,
                "Size": final_sz,
                "Plot Features": "Standard Layout",
                "Demand / Price": prc,
                "Seller Type": "Dealer",
                "Seller / Dealer Name": "",
                "Contact No": main_phone,
                "Office / Agency": st.session_state["office_name"],
                "Deal Status": "Available",
                "Last Conversation / Notes": "Fallback Local Engine",
                "Raw Listing & Source Material": line
            })
    return extracted

# 7. Persistent Summary Routing Control Panel with Exact Sheet Synchronization
@st.dialog("⚡ DHA Extraction Summary & Multi-Phase Push Center", width="large")
def show_routing_popup(payloads, phase_wb_map, gc_client):
    total_raw_items = len(payloads)
    
    # 1. Base Ingestion Dataframe
    base_data = []
    for item in payloads:
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
    df_all = pd.DataFrame(base_data)

    # 2. Top Bar: Live Edit Mode Toggle + Dropdowns for Targeted Extraction
    col_t1, col_t2, col_t3 = st.columns([1.2, 1.4, 1.4])
    
    with col_t1:
        edit_popup_mode = st.toggle("✏️ Edit Mode (ON / OFF)", value=False, key="toggle_popup_edit_mode")

    all_dha_phases = ["All Phases (Everything)"] + list(DHA_PHASE_BLOCK_CATALOG.keys())
    with col_t2:
        selected_phase_target = st.selectbox(
            "📍 Target Phase Sheet:",
            options=all_dha_phases,
            index=0,
            key="popup_target_phase_select"
        )

    if selected_phase_target == "All Phases (Everything)":
        available_tabs = ["All Block Tabs / CCAs"] + sorted(list(df_all["Target Tab"].unique()))
        df_filtered_phase = df_all
    else:
        p_data = DHA_PHASE_BLOCK_CATALOG.get(selected_phase_target, {})
        full_catalog_blocks = p_data.get("residential", []) + p_data.get("commercial", [])
        available_tabs = ["All Block Tabs / CCAs"] + full_catalog_blocks
        df_filtered_phase = df_all[df_all["Target Phase"] == selected_phase_target]

    with col_t3:
        selected_block_target = st.selectbox(
            "🧱 Target Block Tab:",
            options=available_tabs,
            index=0,
            key="popup_target_block_select"
        )

    if selected_block_target != "All Block Tabs / CCAs":
        df_final_display = df_filtered_phase[df_filtered_phase["Target Tab"] == selected_block_target]
    else:
        df_final_display = df_filtered_phase

    # 3. Summary Intelligence Metrics Card
    num_selected = len(df_final_display)
    unique_tabs_count = df_final_display[["Target Phase", "Target Tab"]].drop_duplicates().shape[0] if num_selected > 0 else 0
    with_demand_count = df_final_display[df_final_display["Demand / Price"] != ""].shape[0]
    with_contact_count = df_final_display[df_final_display["Contact No"] != ""].shape[0]

    st.markdown(f"""
        <div class="summary-card">
            <span class="stat-pill">📊 <b>Selected View:</b> {num_selected} Plots</span>
            <span class="stat-pill">📁 <b>Target Tabs:</b> {unique_tabs_count} Tabs</span>
            <span class="stat-pill">💰 <b>Prices Identified:</b> {with_demand_count}</span>
            <span class="stat-pill">📞 <b>Contacts Identified:</b> {with_contact_count}</span>
            <span class="stat-pill">🛡️ <b>Total In Memory:</b> {total_raw_items} Listings</span>
        </div>
    """, unsafe_allow_html=True)

    # 4. Table Display / Editable Sheet
    if edit_popup_mode:
        st.info("💡 **Edit Mode Active:** You can edit cells or delete rows. Only rows shown below will sync.")
        final_df = st.data_editor(
            df_final_display,
            use_container_width=True,
            num_rows="dynamic",
            height=300,
            key="popup_active_data_editor"
        )
    else:
        final_df = df_final_display
        st.dataframe(final_df, use_container_width=True, height=280)

    final_sync_count = len(final_df)
    
    # 5. Dynamic ETA Calculator
    est_seconds = max(3, int(unique_tabs_count * 1.2 + (final_sync_count / 50) * 0.8))
    e_min = est_seconds // 60
    e_sec = est_seconds % 60
    eta_label = f"{e_min}m {e_sec}s" if e_min > 0 else f"{e_sec} seconds"

    st.markdown(f"""
        <div class="eta-box">
            🚀 <b>Ready for Sync:</b> {final_sync_count} listings across {unique_tabs_count} tabs | ⏱️ <b>Estimated Sync Time:</b> ~{eta_label}
        </div>
    """, unsafe_allow_html=True)

    # 6. Action Buttons (Stay on Screen upon Push!)
    col_b1, col_b2 = st.columns([1.6, 1])
    with col_b1:
        if st.button(f"🚀 Push ({final_sync_count} Plots) to Sheet Tabs", use_container_width=True):
            if final_sync_count == 0:
                st.warning("No listings in current selection to sync.")
            else:
                now_dt = datetime.now()
                today_str = now_dt.strftime("%Y-%m-%d")
                now_str = now_dt.strftime("%Y-%m-%d %H:%M")
                
                grouped_data = {}
                for _, row in final_df.iterrows():
                    target_phase = str(row.get("Target Phase", "DHA Phase 1")).strip()
                    target_block = str(row.get("Target Tab", "Block A")).strip()
                    key = (target_phase, target_block)
                    if key not in grouped_data:
                        grouped_data[key] = []
                    grouped_data[key].append(row)
                
                saved_count = 0
                skipped_today = 0
                repeated_tracked = 0
                
                workbook_cache = {}
                total_groups = len(grouped_data)
                
                progress_bar = st.progress(0)
                status_placeholder = st.empty()
                
                for idx, ((phase, block), rows_list) in enumerate(grouped_data.items()):
                    pct = int(((idx + 1) / total_groups) * 100)
                    status_placeholder.markdown(f"⏳ **Syncing:** `[{phase} ➔ {block}]` — ({idx+1}/{total_groups} tabs) • **{pct}% Complete**")
                    
                    if phase not in workbook_cache:
                        wb = get_phase_workbook(gc_client, phase)
                        workbook_cache[phase] = wb
                    
                    wb = workbook_cache[phase]
                    # Exactly connect to the specific block tab
                    ws = get_or_create_clean_tab_exact(wb, block)
                    
                    try:
                        existing_rows = safe_gspread_call(ws.get_all_values)
                    except Exception:
                        existing_rows = []
                    
                    if len(existing_rows) == 0:
                        safe_gspread_call(ws.append_row, CRM_SHEET_HEADERS)
                    
                    existing_plots_today = set()
                    plot_repeat_map = {}
                    
                    if len(existing_rows) > 1:
                        for r in existing_rows[1:]:
                            r_date = r[0] if len(r) > 0 else ""
                            r_plot = str(r[4]).strip().lower() if len(r) > 4 else ""
                            if r_plot:
                                plot_repeat_map[r_plot] = plot_repeat_map.get(r_plot, 0) + 1
                                if today_str in r_date:
                                    existing_plots_today.add(r_plot)
                    
                    rows_to_append = []
                    for row in rows_list:
                        plot_val = str(row.get("Plot No", "")).strip()
                        plot_val_clean = plot_val.lower()
                        
                        if plot_val_clean and plot_val_clean in existing_plots_today:
                            skipped_today += 1
                            continue
                        
                        repeat_count = plot_repeat_map.get(plot_val_clean, 0)
                        notes_txt = "Direct WhatsApp Ingestion"
                        if repeat_count > 0:
                            repeated_tracked += 1
                            notes_txt = f"🔁 Repeated {repeat_count + 1} times this month"
                        
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
                        if plot_val_clean:
                            existing_plots_today.add(plot_val_clean)
                    
                    # Chunked write
                    CHUNK_SIZE = 50
                    for i in range(0, len(rows_to_append), CHUNK_SIZE):
                        chunk_slice = rows_to_append[i:i + CHUNK_SIZE]
                        safe_gspread_call(ws.append_rows, chunk_slice, value_input_option="USER_ENTERED")
                        saved_count += len(chunk_slice)
                        time.sleep(0.4)
                    
                    progress_bar.progress((idx + 1) / total_groups)
                    time.sleep(0.3)
                
                status_placeholder.empty()
                progress_bar.empty()
                st.success(f"🎉 **Success!** Saved **{saved_count} listings** directly to `[{selected_phase_target}]`! (Duplicates skipped: **{skipped_today}**, Repeats marked: **{repeated_tracked}**)")
                st.info("💡 **Screen remains open:** You can now change Phase/Block above to push other portions, or click 'Back' below.")

    with col_b2:
        if st.button("⬅️ Back to Main Screen", use_container_width=True):
            st.session_state["parsed_payloads"] = []
            st.rerun()

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

# 9. Main Dashboard
else:
    try:
        gc_client = get_gspread_client()
    except Exception as e:
        st.error(f"⚠️ Google Sheets Authentication Error: {e}")
        st.stop()

    st.markdown(f"""
        <div class="header-banner">
            <span class="office-badge">📍 {st.session_state['office_name']}</span>
            <h1 class="header-title">🏢 DHA Smart Property Engine & CRM</h1>
            <div class="header-subtitle">Multi-Phase Selective Ingestion & Verification Engine (Active: {st.session_state['user_email']})</div>
        </div>
    """, unsafe_allow_html=True)

    col_city, col_phase = st.columns([1.2, 2.5])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Multan", "Gujranwala"])
    with col_phase:
        phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
        selected_phase = st.selectbox("📍 Select DHA Phase (Active Workbook View)", phase_options, index=11)

    try:
        phase_workbook = get_phase_workbook(gc_client, selected_phase)
    except Exception as e:
        st.error(f"Could not open spreadsheet for {selected_phase}. Please share sheet with `dha-bot@dha-property-sync.iam.gserviceaccount.com` as Editor.")
        st.stop()

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

    sheet_link = DHA_PHASE_SHEET_URLS.get(selected_phase, "")
    st.markdown(f"🔗 **Active Google Sheet:** [Open {selected_phase} in Google Sheets ↗]({sheet_link}) | Current Tab: **`{selected_active_block}`**")

    st.subheader(f"📊 Live Inventory Table: [{selected_phase} ➔ Tab: `{selected_active_block}`]")
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        edit_mode = st.toggle("✏️ Enable Live Edit Mode (Edit Data on Screen)", value=False)
    with col_t2:
        if st.button("🔄 Refresh Table from Google Sheet"):
            st.rerun()

    try:
        current_ws = get_or_create_clean_tab_exact(phase_workbook, selected_active_block)
        records = safe_gspread_call(current_ws.get_all_values)
        
        if len(records) > 1:
            df = pd.DataFrame(records[1:], columns=CRM_SHEET_HEADERS[:len(records[1])])
            
            if edit_mode:
                st.info("💡 **Edit Mode ON:** Edit any cell below, add rows, or delete rows. Click **'Save Changes'** when done.")
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    num_rows="dynamic",
                    height=320,
                    key=f"editor_{selected_phase}_{selected_active_block}"
                )
                
                if st.button("💾 Save Changes to Google Sheet", use_container_width=True):
                    with st.spinner("Updating Google Sheet Tab..."):
                        try:
                            updated_values = [CRM_SHEET_HEADERS] + edited_df.fillna("").values.tolist()
                            safe_gspread_call(current_ws.clear)
                            safe_gspread_call(current_ws.update, updated_values)
                            st.success(f"✅ Google Sheet Tab **[{selected_active_block}]** successfully updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update error: {e}")
            else:
                st.dataframe(df, use_container_width=True, height=280)
                
                for idx, r in df.iterrows():
                    dem_val = r.get('Demand / Price', '')
                    phn_val = r.get('Contact No', '')
                    plt_val = r.get('Plot No', '')
                    sz_val = r.get('Size', '')
                    sz_display = f"({sz_val})" if sz_val else ""
                    feat_val = r.get('Plot Features', '')
                    feat_badge = f'<span class="badge badge-feature">⭐ {feat_val}</span>' if feat_val else ""
                    cat_val = r.get('Category', 'Selling')
                    notes_val = r.get('Last Conversation / Notes', '')
                    raw_val = r.get('Raw Listing & Source Material', '')

                    repeat_badge = f'<span class="badge badge-repeat">{notes_val}</span>' if "Repeated" in notes_val else ""

                    st.markdown(f"""
                        <div class="property-card">
                            <span class="badge badge-selling">{cat_val}</span>
                            <span class="badge badge-price">💰 {dem_val if dem_val else 'Demand N/A'}</span>
                            {feat_badge}
                            {repeat_badge}
                            <b>{selected_phase} {selected_active_block} — {plt_val} {sz_display}</b>
                            <div style="margin-top: 5px; font-size: 13px; color: #475569;">📞 Contact: <b>{phn_val if phn_val else '—'}</b> | Added: {r.get('Date / Timestamp', '')}</div>
                            <div style="margin-top: 4px; font-size: 12px; color: #64748B; background: #F8FAFC; padding: 5px 8px; border-radius: 6px;">📝 {raw_val}</div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Tab **[{selected_active_block}]** is active in Google Sheets. Currently 0 entries found. Add listings in the box below to see them appear here!")
    except Exception as e:
        st.error(f"Error connecting to Tab [{selected_active_block}]: {e}")

    st.markdown("---")

    # ==========================================================================
    # 3. BOTTOM SECTION: AI MULTI-SOURCE INGESTION & HIGH SPEED BATCH ROUTING
    # ==========================================================================
    if gemini_active:
        st.markdown('<div class="ai-badge-active">🟢 Google Gemini AI Extraction Engine: Connected & Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ai-badge-inactive">🟡 Gemini API Key Missing — Operating on Fallback Pattern Parser (Add GEMINI_API_KEY to Secrets for full AI power)</div>', unsafe_allow_html=True)

    st.subheader("🧠 AI Multi-Source Data Ingestion Engine")
    
    col_u1, col_u2 = st.columns([1.5, 1.5])
    
    with col_u2:
        tab_upload, tab_gdrive, tab_camera, tab_direct = st.tabs(["📎 Upload File", "☁️ G-Drive Link", "📸 Camera", "📋 Direct Paste"])
        
        with tab_upload:
            uploaded_file = st.file_uploader(
                "Upload TXT, Excel, JSON, PDF, or Image:",
                type=["txt", "xlsx", "xls", "json", "csv", "pdf", "png", "jpg", "jpeg", "webp"],
                help="Upload property spreadsheets, JSON lists, flyers, or WhatsApp exported chats."
            )
            if uploaded_file is not None:
                with st.spinner(f"Reading `{uploaded_file.name}`..."):
                    try:
                        extracted_content = extract_text_from_any_file_or_image(uploaded_file, is_camera=False)
                        if extracted_content:
                            st.session_state["extracted_file_text"] = extracted_content
                            st.success(f"✅ Successfully loaded `{uploaded_file.name}` into the extraction box!")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

        with tab_gdrive:
            gdrive_url_in = st.text_input("Paste Google Drive Shared Link (TXT / WhatsApp Chat):", placeholder="https://drive.google.com/file/d/1A2B3C.../view?usp=sharing")
            if st.button("☁️ Push G-Drive File Data to Box", use_container_width=True):
                if gdrive_url_in.strip():
                    with st.spinner("Downloading, cleaning chat timestamps and loading into box..."):
                        gdrive_content = fetch_content_from_gdrive_url(gdrive_url_in.strip())
                        if gdrive_content and not gdrive_content.startswith("[Error"):
                            st.session_state["extracted_file_text"] = gdrive_content
                            st.success("✅ Cleaned WhatsApp data loaded into extraction box below!")
                        else:
                            st.error(gdrive_content)
                else:
                    st.warning("Please enter a valid Google Drive file link.")
        
        with tab_camera:
            camera_photo = st.camera_input("Take a photo of a property document / map / flyer:")
            if camera_photo is not None:
                with st.spinner("🧠 Scanning document via Google Vision OCR..."):
                    camera_text = extract_text_from_any_file_or_image(camera_photo, is_camera=True)
                    if camera_text:
                        st.session_state["extracted_file_text"] = camera_text
                        st.success("✅ Camera photo transcribed into the extraction box below!")

        with tab_direct:
            pasted_txt = st.text_area("Paste large WhatsApp exports or text blocks directly:", height=110, placeholder="Paste text here...")
            if st.button("📥 Push Pasted Text to Box", use_container_width=True):
                if pasted_txt.strip():
                    st.session_state["extracted_file_text"] = pasted_txt.strip()
                    st.success("✅ Text loaded into extraction box below!")

    with col_u1:
        default_box_value = st.session_state.get("extracted_file_text", "")
        
        raw_text = st.text_area(
            "📋 Raw Real Estate Ingestion Box (Enterprise Fault-Tolerant Engine):",
            value=default_box_value,
            height=220,
            placeholder="Data loaded from files, Google Drive, camera or copy-paste will appear here for processing..."
        )

    if st.button("🚀 Process, Segregate & Route to Block Tabs", use_container_width=True):
        final_input_text = raw_text.strip()
        if final_input_text:
            with st.spinner("🧠 AI Engine is extracting listings and preparing interactive batch editor..."):
                payloads = parse_with_strict_gemini_schema(final_input_text, selected_phase)
                if payloads:
                    st.session_state["parsed_payloads"] = payloads
                    show_routing_popup(payloads, DHA_PHASE_SHEET_URLS, gc_client)
                else:
                    st.warning("No valid property listings could be identified in the text.")
        else:
            st.warning("Please provide listing text, take a camera photo, or upload a file.")
