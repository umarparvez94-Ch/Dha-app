import streamlit as st
import gspread
import re
import json
import io
import os
import time
import math
import urllib.request
import urllib.parse
import pandas as pd
from datetime import datetime
from PIL import Image
from google.oauth2 import service_account

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# Google GenAI SDK Setup
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Property Search Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session State Variables
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

# Batch Streaming State Machine
if "extraction_active" not in st.session_state:
    st.session_state["extraction_active"] = False
if "extraction_paused" not in st.session_state:
    st.session_state["extraction_paused"] = False
if "all_chunks" not in st.session_state:
    st.session_state["all_chunks"] = []
if "current_chunk_idx" not in st.session_state:
    st.session_state["current_chunk_idx"] = 0

# Safe Gemini Client Activation
gemini_client = None
gemini_active = False
try:
    api_key_val = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    if HAS_GENAI and api_key_val:
        gemini_client = genai.Client(api_key=api_key_val)
        gemini_active = True
except Exception:
    gemini_active = False

# 2. Modern Responsive UI/UX Styling
st.markdown("""<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&family=Manrope:wght@600;700;800&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"><style>#MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }.stAppDeployButton { display: none !important; }.block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }.stApp { background-color: #F7F9FB !important; font-family: 'Inter', sans-serif !important; color: #191C1E !important; }.header-banner { background: linear-gradient(135deg, #00113A 0%, #102A6B 100%); padding: 16px 20px; border-radius: 12px; color: white; margin-bottom: 14px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; box-shadow: 0 4px 14px rgba(0, 17, 58, 0.1); }.header-title { font-family: 'Manrope', sans-serif; font-size: 20px; font-weight: 800; margin: 0; color: #FFFFFF; }.header-subtitle { color: #B3C5FF; font-size: 12px; margin-top: 2px; }.office-badge { background-color: #006B5E; color: #9FF2E1; padding: 4px 12px; border-radius: 14px; font-size: 12px; font-weight: 600; }.stitch-login-box { background: #FFFFFF; border: 1px solid #C5C6D0; border-radius: 16px; box-shadow: 0px 8px 24px rgba(0, 17, 58, 0.04); padding: 32px 28px; margin-bottom: 16px; text-align: center; }.stitch-avatar { width: 60px; height: 60px; border-radius: 50%; background-color: #D6E2FF; border: 1px solid #B3C5FF; display: inline-flex; align-items: center; justify-content: center; color: #00113A; margin-bottom: 12px; }div[role="radiogroup"] { display: flex !important; flex-direction: row !important; overflow-x: auto !important; white-space: nowrap !important; padding-bottom: 8px !important; gap: 8px !important; scrollbar-width: thin; }div[role="radiogroup"] label { background: #FFFFFF !important; border: 1px solid #C5C6D0 !important; border-radius: 20px !important; padding: 4px 14px !important; font-size: 12px !important; font-weight: 600 !important; color: #191C1E !important; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important; }.summary-card { background: #FFFFFF; border: 1px solid #C5C6D0; border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); display: flex; flex-wrap: wrap; gap: 8px; }.stat-pill { background: #ECEEF0; border-radius: 20px; padding: 6px 12px; font-size: 12px; font-weight: 600; color: #191C1E; display: inline-block; }.stat-pill b { color: #00113A; font-family: 'JetBrains Mono', monospace; }.stitch-card-container { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 14px; box-shadow: 0 2px 8px rgba(0, 17, 58, 0.03); margin-bottom: 12px; }.control-panel-box { background: #FFFFFF; border: 2px solid #00113A; border-radius: 12px; padding: 14px 18px; margin: 12px 0; box-shadow: 0 4px 14px rgba(0,17,58,0.06); }.backend-info-card { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 10px; padding: 16px; font-size: 13px; color: #1E293B; line-height: 1.6; }.news-badge { display: inline-block; padding: 4px 10px; margin: 3px 2px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; color: #00113A; background: #E2E8F0; border: 1px solid #CBD5E1; }.stButton > button { border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; min-height: 38px !important; border: 1px solid #CBD5E1 !important; background-color: #FFFFFF !important; color: #00113A !important; transition: all 0.15s ease-in-out !important; }div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea { background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important; border-radius: 8px !important; color: #191C1E !important; font-size: 13px !important; }@media (max-width: 768px) { .header-banner { flex-direction: column; align-items: flex-start; } .stButton > button { width: 100% !important; } }</style>""", unsafe_allow_html=True)

# 15 Canonical CRM Schema Columns for Google Sheets Backend
CRM_SHEET_HEADERS = [
    "Date / Timestamp", "Category", "Phase", "Block", "Plot No",
    "Size", "Plot Features", "Demand / Price", "Seller Type",
    "Seller / Dealer Name", "Contact No", "Office / Agency",
    "Deal Status", "Last Conversation / Notes", "Raw Listing & Source Material"
]

# Google Sheets URL Workbooks Directory
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

# Full Official DHA Cutting Map Rules
DHA_CUTTING_MAP_RULES = {
    "DHA Phase 1": {"Block A": [(1, 800, "1 Kanal")], "Block B": [(1, 900, "1 Kanal")], "Block C": [(1, 850, "1 Kanal")], "Block D": [(1, 750, "1 Kanal")], "Block E": [(1, 600, "1 Kanal")], "Block J": [(1, 700, "1 Kanal")], "Block K": [(1, 650, "1 Kanal")], "Block L": [(1, 800, "10 Marla")], "Block M": [(1, 950, "10 Marla")], "Block N": [(1, 1100, "5 Marla")], "Block P": [(1, 1200, "5 Marla")]},
    "DHA Phase 2": {"Block Q": [(1, 600, "1 Kanal")], "Block R": [(1, 700, "1 Kanal")], "Block S": [(1, 800, "1 Kanal")], "Block T": [(1, 900, "10 Marla")], "Block U": [(1, 1000, "10 Marla")], "Block V": [(1, 1200, "5 Marla")]},
    "DHA Phase 3": {"Block W": [(1, 500, "2 Kanal"), (501, 1100, "1 Kanal")], "Block X": [(1, 400, "2 Kanal"), (401, 1000, "1 Kanal")], "Block Y": [(1, 300, "2 Kanal"), (301, 900, "1 Kanal")], "Block Z": [(1, 800, "1 Kanal")], "Block XX": [(1, 950, "1 Kanal")]},
    "DHA Phase 4": {"Block AA": [(1, 700, "1 Kanal")], "Block BB": [(1, 800, "1 Kanal")], "Block CC": [(1, 900, "1 Kanal")], "Block DD": [(1, 650, "1 Kanal")], "Block EE": [(1, 850, "10 Marla")], "Block GG": [(1, 950, "10 Marla")], "Block JJ": [(1, 1100, "10 Marla")], "Block KK": [(1, 1200, "5 Marla")]},
    "DHA Phase 5": {"Block A": [(1, 120, "2 Kanal"), (121, 500, "1 Kanal")], "Block B": [(1, 80, "2 Kanal"), (81, 600, "1 Kanal")], "Block C": [(1, 50, "2 Kanal"), (51, 450, "1 Kanal")], "Block D": [(1, 600, "1 Kanal")], "Block E": [(1, 550, "1 Kanal")], "Block F": [(1, 500, "1 Kanal")], "Block G": [(1, 350, "1 Kanal"), (351, 700, "10 Marla")], "Block H": [(1, 400, "10 Marla"), (401, 800, "5 Marla")], "Block J": [(1, 500, "10 Marla"), (501, 950, "5 Marla")], "Block K": [(1, 600, "10 Marla")], "Block L": [(1, 750, "10 Marla"), (751, 1200, "5 Marla")], "Block M": [(1, 800, "5 Marla")]},
    "DHA Phase 6": {"Block A": [(1, 150, "2 Kanal"), (151, 800, "1 Kanal")], "Block B": [(1, 100, "2 Kanal"), (101, 700, "1 Kanal")], "Block C": [(1, 650, "1 Kanal")], "Block D": [(1, 700, "1 Kanal")], "Block E": [(1, 550, "1 Kanal")], "Block F": [(1, 600, "1 Kanal")], "Block G": [(1, 650, "1 Kanal")], "Block H": [(1, 700, "1 Kanal")], "Block J": [(1, 600, "10 Marla")], "Block K": [(1, 650, "10 Marla")], "Block L": [(1, 800, "10 Marla"), (801, 1200, "5 Marla")], "Block M": [(1, 850, "10 Marla")], "Block N": [(1, 900, "10 Marla")]},
    "DHA Phase 7": {"Block P": [(1, 1100, "1 Kanal")], "Block Q": [(1, 900, "1 Kanal")], "Block R": [(1, 1050, "1 Kanal")], "Block S": [(1, 950, "1 Kanal")], "Block T": [(1, 1200, "1 Kanal")], "Block U": [(1, 1400, "1 Kanal")], "Block V": [(1, 1000, "1 Kanal")], "Block W": [(1, 1400, "10 Marla")], "Block X": [(1, 1300, "10 Marla")], "Block Y": [(1, 900, "5 Marla")], "Block Z": [(1, 1100, "5 Marla")], "Block Z-1": [(1, 800, "5 Marla")], "Block Z-2": [(1, 750, "5 Marla")]},
    "DHA Phase 8 (Proper)": {"Block A": [(1, 100, "2 Kanal"), (101, 550, "1 Kanal")], "Block B": [(1, 80, "2 Kanal"), (81, 500, "1 Kanal")], "Block C": [(1, 70, "2 Kanal"), (71, 480, "1 Kanal")], "Block D": [(1, 600, "1 Kanal")], "Block E": [(1, 550, "1 Kanal")], "Block F": [(1, 500, "1 Kanal")], "Block G": [(1, 520, "1 Kanal")], "Block H": [(1, 480, "1 Kanal")], "Block J": [(1, 510, "1 Kanal")], "Block K": [(1, 560, "1 Kanal")], "Block L": [(1, 620, "1 Kanal")], "Block M": [(1, 580, "1 Kanal")], "Block N": [(1, 610, "1 Kanal")], "Block P": [(1, 640, "1 Kanal")], "Block Q": [(1, 590, "1 Kanal")], "Block R": [(1, 630, "1 Kanal")], "Block S": [(1, 750, "10 Marla")], "Block T": [(1, 800, "10 Marla"), (801, 1300, "5 Marla")], "Block U": [(1, 900, "5 Marla")], "Block V": [(1, 850, "5 Marla")], "Block W": [(1, 700, "8 Marla")], "Block X": [(1, 750, "8 Marla")], "Block Y": [(1, 800, "8 Marla")]},
    "DHA Phase 8 (Ivy Green / Sector Z)": {"Block Z-1": [(1, 700, "5 Marla")], "Block Z-2": [(1, 800, "5 Marla")], "Block Z-3": [(1, 900, "5 Marla")], "Block Z-4": [(1, 750, "5 Marla")], "Block Z-5": [(1, 650, "5 Marla")], "Block Z-6": [(1, 600, "5 Marla")]},
    "DHA Phase 8 (Park View)": {"Block A": [(1, 500, "2 Kanal"), (501, 1200, "1 Kanal")], "Block B": [(1, 400, "2 Kanal"), (401, 1100, "1 Kanal")], "Block C": [(1, 1000, "1 Kanal")], "Block D": [(1, 950, "1 Kanal")], "Block E": [(1, 900, "1 Kanal")], "Block F": [(1, 850, "1 Kanal")], "Block G": [(1, 800, "1 Kanal")], "Block H": [(1, 750, "1 Kanal")], "Block J": [(1, 1200, "10 Marla")], "Block K": [(1, 1100, "10 Marla")]},
    "DHA Phase 8 (Air Avenue / Sector AA)": {"Block L": [(1, 800, "1 Kanal")], "Block M": [(1, 850, "1 Kanal")], "Block N": [(1, 900, "1 Kanal")], "Block P": [(1, 1100, "10 Marla")], "Block Q": [(1, 1200, "10 Marla")], "Block R": [(1, 1400, "5 Marla")]},
    "DHA Phase 9 Prism": {"Block A": [(1, 600, "1 Kanal")], "Block B": [(1, 550, "1 Kanal")], "Block C": [(1, 700, "1 Kanal")], "Block D": [(1, 650, "1 Kanal")], "Block E": [(1, 500, "1 Kanal")], "Block F": [(1, 700, "1 Kanal")], "Block G": [(1, 600, "1 Kanal")], "Block H": [(1, 650, "1 Kanal")], "Block J": [(1, 1200, "10 Marla")], "Block K": [(1, 1100, "10 Marla")], "Block L": [(1, 1300, "10 Marla")], "Block M": [(1, 1250, "10 Marla")], "Block N": [(1, 1150, "10 Marla")], "Block P": [(1, 1400, "5 Marla")], "Block Q": [(1, 1600, "5 Marla")], "Block R": [(1, 1800, "5 Marla")]},
    "DHA Phase 9 Town": {"Block A": [(1, 900, "5 Marla")], "Block B": [(1, 950, "5 Marla")], "Block C": [(1, 1100, "8 Marla")], "Block D": [(1, 850, "8 Marla")], "Block E": [(1, 700, "10 Marla")]},
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": {"Sector 1": [(1, 600, "5 Marla")], "Sector 2": [(1, 700, "5 Marla")], "Sector 2 Extension": [(1, 500, "5 Marla")], "Sector 3": [(1, 800, "5 Marla")], "Sector 4": [(1, 900, "5 Marla")], "Sector 5": [(1, 1000, "10 Marla")]},
    "DHA Phase 12 (EME Sector)": {"Block A": [(1, 500, "2 Kanal"), (501, 1000, "1 Kanal")], "Block B": [(1, 800, "1 Kanal")], "Block C": [(1, 900, "1 Kanal")], "Block D": [(1, 750, "1 Kanal")], "Block E": [(1, 850, "10 Marla")], "Block F": [(1, 950, "10 Marla")], "Block G": [(1, 1100, "5 Marla")], "Block H": [(1, 1200, "5 Marla")], "Block J": [(1, 1050, "5 Marla")]}
}

# Complete DHA Phases & Block Tabs Catalog
DHA_PHASE_BLOCK_CATALOG = {
    "DHA Phase 1": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P"], "commercial": ["Block F Commercial", "Block G Commercial", "Block H Commercial", "Block J Commercial", "Block M Commercial", "Sector Shops"]},
    "DHA Phase 2": {"residential": ["Block Q", "Block R", "Block S", "Block T", "Block U", "Block V"], "commercial": ["Commercial CCA", "Block R Commercial", "Block T Commercial", "Sector Shops"]},
    "DHA Phase 3": {"residential": ["Block W", "Block X", "Block Y", "Block Z", "Block XX"], "commercial": ["Y Block Commercial", "Z Block Commercial", "W Block Commercial", "Sector Shops"]},
    "DHA Phase 4": {"residential": ["Block AA", "Block BB", "Block CC", "Block DD", "Block EE", "Block GG", "Block JJ", "Block KK"], "commercial": ["CCA 1 Commercial", "CCA 2 Commercial", "Block DD Commercial", "Sector Shops"]},
    "DHA Phase 5": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M"], "commercial": ["CCA 1 Commercial", "CCA 2 Commercial", "Sector Shops"]},
    "DHA Phase 6": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N"], "commercial": ["Main Boulevard (MB) Commercial", "CCA 1 Commercial", "CCA 2 Commercial", "Sector Shops"]},
    "DHA Phase 7": {"residential": ["Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y", "Block Z", "Block Z-1", "Block Z-2"], "commercial": ["CCA 1 Commercial", "CCA 2 Commercial", "CCA 3 Commercial", "CCA 4 Commercial", "Sector Y Commercial", "Sector Shops"]},
    "DHA Phase 8 (Proper)": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y"], "commercial": ["Broadway Commercial", "Commercial CCA 1", "Commercial CCA 2", "Commercial CCA 3", "Sector Shops"]},
    "DHA Phase 8 (Ivy Green / Sector Z)": {"residential": ["Block Z-1", "Block Z-2", "Block Z-3", "Block Z-4", "Block Z-5", "Block Z-6"], "commercial": ["Commercial CCA Sector Z", "Sector Shops"]},
    "DHA Phase 8 (Park View)": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K"], "commercial": ["Commercial Zone Park View", "Sector Shops"]},
    "DHA Phase 8 (Air Avenue / Sector AA)": {"residential": ["Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"], "commercial": ["Commercial CCA Air Avenue"]},
    "DHA Phase 9 Prism": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"], "commercial": ["Zone 1 Commercial", "Zone 2 Commercial", "Zone 3 Commercial", "Main Oval Commercial", "Prism Direct MB Commercial"]},
    "DHA Phase 9 Town": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E"], "commercial": ["Commercial CCA Phase 9 Town", "Sector Shops"]},
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": {"residential": ["Sector 1", "Sector 2", "Sector 2 Extension", "Sector 3", "Sector 4", "Sector 5"], "commercial": ["Rahbar CCA 1", "Rahbar CCA 2", "Rahbar Sector 5 Commercial", "Sector Shops"]},
    "DHA Phase 12 (EME Sector)": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J"], "commercial": ["Civic Centre EME", "Block D Commercial", "Block H Commercial", "Sector Shops"]}
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

# Modals & Dialogs
@st.dialog("🔗 Backend Google Sheets Connection Details", width="large")
def show_backend_connection_dialog(selected_phase, selected_block, target_url):
    st.markdown(f"#### 🏢 Google Sheets Connection Architecture: [{selected_phase}]")
    st.markdown(f"""
        <div class="backend-info-card">
            <b>🔑 Service Account:</b> <code>dha-bot@dha-property-sync.iam.gserviceaccount.com</code><br>
            <b>🌐 Active Spreadsheet Target:</b> <a href="{target_url}" target="_blank">{selected_phase} Database</a><br>
            <b>🧱 Target Tab Attached:</b> <code>{selected_block}</code><br>
            <b>⚡ Sync Protocols:</b> 500-Row Chunked Append with Exponential Backoff (Quota 429 Protection)<br>
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
        contact = str(item.get("Contact No", "")).strip()
        dealer_name = str(item.get("Seller / Dealer Name", "")).strip()
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
        st.dataframe(summary_group, height=260, use_container_width=True)
        st.markdown("##### 🔍 Detailed Listing Records per Dealer:")
        st.dataframe(df_dealers, height=220, use_container_width=True)

@st.dialog("📈 Price Trend Analytics", width="large")
def show_price_analytics_dialog(payloads):
    st.markdown("### 📊 DHA Price Demand Trends & Block Analytics")
    if not payloads:
        st.info("No property records available for price analytics.")
        return
    clean_records = []
    for item in payloads:
        price_str = str(item.get("Demand / Price", "")).upper().strip()
        phase = str(item.get("Phase", "Unknown"))
        block = str(item.get("Block", "Unknown"))
        size = str(item.get("Size", "Unknown"))
        lac_val = 0.0
        match_lac = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:LAC|LACS)', price_str)
        match_cr = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:CRORE|CR)', price_str)
        if match_cr:
            lac_val = float(match_cr.group(1)) * 100.0
        elif match_lac:
            lac_val = float(match_lac.group(1))
        if lac_val > 0:
            clean_records.append({
                "Phase": phase,
                "Block": block,
                "Size": size,
                "Price (Lacs)": lac_val,
                "Raw Demand": price_str
            })
    if clean_records:
        df_analytics = pd.DataFrame(clean_records)
        summary_analytics = df_analytics.groupby(["Phase", "Block", "Size"]).agg(
            Total_Options=("Price (Lacs)", "count"),
            Avg_Price_Lacs=("Price (Lacs)", lambda x: round(x.mean(), 1)),
            Min_Price_Lacs=("Price (Lacs)", "min"),
            Max_Price_Lacs=("Price (Lacs)", "max")
        ).reset_index().sort_values(by="Total_Options", ascending=False)
        st.markdown(f"**Calculated from `{len(clean_records)}` listings with explicit pricing:**")
        st.dataframe(summary_analytics, height=350, use_container_width=True)
    else:
        st.warning("No listings with standard Lac/Crore price formats detected yet.")

@st.dialog("📱 Client-Ready WhatsApp Broadcast Generator", width="large")
def show_whatsapp_share_dialog(df_share):
    st.markdown("### 📱 Formatted Client Broadcast")
    if df_share.empty:
        st.warning("No records selected for broadcast.")
        return
    broadcast_lines = [
        f"🏢 *{st.session_state['office_name']}* - Available Inventory Update",
        f"📅 Date: {datetime.now().strftime('%d-%b-%Y')}",
        "----------------------------------------"
    ]
    for idx, (_, row) in enumerate(df_share.iterrows(), 1):
        p_str = f"*{row.get('Phase', '')} - {row.get('Block No', '')}*"
        plt = row.get('Plot No', '')
        sz = row.get('Size', '')
        dem = row.get('Price', 'Call for Price')
        feat = row.get('Plot Features', '')
        line = f"📍 {p_str} | {plt} ({sz})\n   💰 Demand: *{dem}* | Feature: {feat}"
        broadcast_lines.append(line)
    broadcast_lines.append("----------------------------------------")
    broadcast_lines.append("📞 For Deals & Inquiries: Direct Message or Call.")
    final_text = "\n\n".join(broadcast_lines)
    st.text_area("📋 Copy Broadcast Text Directly:", value=final_text, height=260)
    encoded_text = urllib.parse.quote(final_text)
    wa_url = f"https://api.whatsapp.com/send?text={encoded_text}"
    st.link_button("📲 Open in WhatsApp Web / App ↗", url=wa_url)

@st.dialog("📄 Generate Printable PDF / HTML Catalog", width="large")
def show_pdf_catalog_dialog(df_cat):
    st.markdown("### 📄 Property Catalog Preview")
    if df_cat.empty:
        st.warning("No records selected for catalog.")
        return
    now_str = datetime.now().strftime("%d %B, %Y - %H:%M")
    html_preview = f"""
    <div style="background:#FFFFFF; border:1px solid #CBD5E1; padding:24px; border-radius:8px; font-family:'Inter', sans-serif;">
        <div style="border-bottom:2px solid #00113A; padding-bottom:12px; margin-bottom:16px;">
            <h2 style="color:#00113A; margin:0;">🏢 {st.session_state['office_name']}</h2>
            <div style="color:#64748B; font-size:13px;">Official Property Inventory & Deal Options • Generated on: {now_str}</div>
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
            <thead>
                <tr style="background:#F1F5F9; border-bottom:1px solid #CBD5E1;">
                    <th style="padding:8px;">#</th>
                    <th style="padding:8px;">Date / Timestamp</th>
                    <th style="padding:8px;">Phase</th>
                    <th style="padding:8px;">Block No</th>
                    <th style="padding:8px;">Plot No</th>
                    <th style="padding:8px;">Size</th>
                    <th style="padding:8px;">Features</th>
                    <th style="padding:8px;">Price</th>
                    <th style="padding:8px;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    for idx, (_, row) in enumerate(df_cat.iterrows(), 1):
        html_preview += f"""
            <tr style="border-bottom:1px solid #E2E8F0;">
                <td style="padding:8px;">{idx}</td>
                <td style="padding:8px;">{row.get('Date / Timestamp', '')}</td>
                <td style="padding:8px; font-weight:600;">{row.get('Phase', '')}</td>
                <td style="padding:8px;">{row.get('Block No', '')}</td>
                <td style="padding:8px; font-weight:600; color:#00113A;">{row.get('Plot No', '')}</td>
                <td style="padding:8px;">{row.get('Size', '')}</td>
                <td style="padding:8px;">{row.get('Plot Features', '')}</td>
                <td style="padding:8px; font-weight:600; color:#006B5E;">{row.get('Price', '')}</td>
                <td style="padding:8px;">{row.get('Status', 'Available')}</td>
            </tr>
        """
    html_preview += "</tbody></table></div>"
    st.markdown(html_preview, unsafe_allow_html=True)
    st.caption("ℹ️ Use Browser Print (Ctrl + P / Cmd + P) to Save as PDF.")

# File Parsers & Readers
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

# Message Boundary Chunker
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
        chunks.append("\n\n===WHATSAPP_MESSAGE_START===\n" + "\n\n===WHATSAPP_MESSAGE_START===\n".join(chunk_batch))
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
            return response.read().decode('utf-8', errors='ignore')
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
            return f"[Source: {url_in}]\n" + re.sub(r'\s+', ' ', text_only).strip()[:30000]
    except Exception as e:
        return f"[Error connecting to Portal URL: {e}]"

def clean_line_from_artifacts(l):
    return re.sub(r'[\*\_~`]', ' ', l).strip()

def detect_phase_from_header(line_up):
    # Strictly ignore generic broad titles
    if "ALL DHA" in line_up or "DHA LAHORE" in line_up or "HOT DEALS" in line_up or "AVAILABLE PLOTS" in line_up:
        return None
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

# High-Precision WhatsApp Fallback Parser
def smart_accurate_rule_parser(chunk_text):
    raw_messages = chunk_text.split("===WHATSAPP_MESSAGE_START===")
    results = []
    FORBIDDEN_BLOCK_WORDS = {
        "PHASE", "PH", "SECTOR", "DHA", "CCA", "COMMERCIAL", "PAIR", "DEMAND", "ASKING",
        "OFFER", "FINAL", "DIRECT", "MEETING", "COMPLETE", "FILE", "PAPER", "CORNER", "PARK",
        "ROAD", "FACING", "POSSESSION", "RS", "LAC", "LACS", "CRORE", "CR", "KANAL", "MARLA",
        "MAIN", "NEAR", "BOULEVARD", "ZONE", "SE", "CA", "TH", "ST", "ND", "RD"
    }
    
    for msg in raw_messages:
        m_clean = msg.strip()
        if not m_clean:
            continue
        
        ts_match = re.search(r'(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4},?\s+\d{1,2}:\d{2})', m_clean)
        msg_timestamp = ts_match.group(1) if ts_match else datetime.now().strftime("%Y-%m-%d %H:%M")
        
        phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', m_clean)
        main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else ""
        
        # Initial phase state: None (No auto-assignment from UI dropdown)
        active_phase = detect_phase_from_header(m_clean.upper())
        lines = [clean_line_from_artifacts(l) for l in m_clean.splitlines() if clean_line_from_artifacts(l)]
        
        for line in lines:
            l_up = line.upper()
            ph_found = detect_phase_from_header(l_up)
            if ph_found:
                active_phase = ph_found
                continue
                
            cca_match = re.search(r'CCA\s*([0-9])?\s*([A-Z])?.*?(?:PLOT|NO|#)?\s*([0-9]{1,4})', l_up)
            p_match = re.search(r'(?:BLOCK\s+)?([A-Z]{1,2}[0-9]?)\s+(?:PLOT|NO|#)?\s*([0-9]{1,5}(?:[+/][0-9]{1,5})?)', l_up)
            
            prc_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(LAC|LACS|CRORE|CR)', l_up)
            prc_str = f"{prc_match.group(1)} {prc_match.group(2).capitalize()}" if prc_match else ""
            
            sz_str = ""
            if "1 KANAL" in l_up or "1K" in l_up: sz_str = "1 Kanal"
            elif "2 KANAL" in l_up or "2K" in l_up: sz_str = "2 Kanal"
            elif "10 MARLA" in l_up or "10M" in l_up: sz_str = "10 Marla"
            elif "5 MARLA" in l_up or "5M" in l_up: sz_str = "5 Marla"
            elif "4 MARLA" in l_up or "4M" in l_up: sz_str = "4 Marla"
            elif "8 MARLA" in l_up or "8M" in l_up: sz_str = "8 Marla"
            
            feat = "Corner" if "CORNER" in l_up else ("Facing Park" if "PARK" in l_up else ("Possession" if "POSSESSION" in l_up else "Standard Layout"))
            final_phase_str = active_phase if active_phase else "Unassigned Phase"
            
            if cca_match:
                cca_num = cca_match.group(1) or "1"
                blk_cca = f"CCA {cca_num} Commercial"
                plt_num = cca_match.group(3)
                results.append({
                    "Date / Timestamp": msg_timestamp,
                    "Category": "Selling",
                    "Phase": final_phase_str,
                    "Block": blk_cca,
                    "Plot No": f"Plot {plt_num}",
                    "Size": sz_str if sz_str else "4 Marla Commercial",
                    "Plot Features": "Commercial / CCA",
                    "Demand / Price": prc_str,
                    "Seller Type": "Authorized Dealer",
                    "Seller / Dealer Name": "",
                    "Contact No": main_phone,
                    "Office / Agency": st.session_state["office_name"],
                    "Deal Status": "Available",
                    "Last Conversation / Notes": "Direct Ingestion",
                    "Raw Listing & Source Material": m_clean
                })
            elif p_match:
                raw_b = p_match.group(1).strip()
                if raw_b not in FORBIDDEN_BLOCK_WORDS:
                    raw_p = p_match.group(2).strip()
                    blk_str = f"Block Z-{raw_b[1]}" if (raw_b.startswith("Z") and len(raw_b) == 2 and raw_b[1].isdigit()) else f"Block {raw_b}"
                    final_sz = sz_str if sz_str else (resolve_size_text_first_or_map(final_phase_str, blk_str, f"Plot {raw_p}", "") if final_phase_str != "Unassigned Phase" else "")
                    results.append({
                        "Date / Timestamp": msg_timestamp,
                        "Category": "Selling",
                        "Phase": final_phase_str,
                        "Block": blk_str,
                        "Plot No": f"Plot {raw_p}",
                        "Size": final_sz,
                        "Plot Features": feat,
                        "Demand / Price": prc_str,
                        "Seller Type": "Authorized Dealer",
                        "Seller / Dealer Name": "",
                        "Contact No": main_phone,
                        "Office / Agency": st.session_state["office_name"],
                        "Deal Status": "Available",
                        "Last Conversation / Notes": "Direct Ingestion",
                        "Raw Listing & Source Material": m_clean
                    })
    return results

# Gemini 2.5 Flash Dedicated Parser
def process_single_chunk_via_gemini(chunk_text):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    now_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    system_prompt = f"""You are the Master DHA Lahore Real Estate Data Pipeline Architect & Forensic Text Parsing Specialist.
Your explicit objective is to ingest WhatsApp export files, chats, spreadsheets, notebooks, and extract EVERY PROPERTY LISTING into a structured JSON array with 100% precision.

### STRICT PHASE DETECTION & UNASSIGNED RULE:
1. STRICT DETECTION: Extract the Phase name ONLY if explicitly written in the message (e.g. 'Phase 9 Prism', 'Ph 6', 'Phase 8 Proper').
2. UNASSIGNED PHASE FLAG: If NO DHA phase is specified anywhere in the message context, you MUST set "Phase": "Unassigned Phase". DO NOT GUESS OR DEFAULT TO ANY PHASE.
3. DYNAMIC INHERITANCE: If a phase header is present, all subsequent plots inherit it until a new phase header is encountered.
4. GENERIC HEADERS: Ignore generic headers like 'ALL DHA LAHORE', 'HOT DEALS'. Look for specific phase indicators.

### LOCAL MARKET VOCABULARY NORMALIZATION:
- '1k', '1kanal' -> '1 Kanal'
- '10m', '10marla' -> '10 Marla'
- '5m', '5marla' -> '5 Marla'
- '4cca', '4m comm' -> '4 Marla Commercial'
- 'cnr' -> 'Corner'
- 'pk fcg', 'facing park' -> 'Facing Park'
- 'posn', 'pos' -> 'Possession'
- 'mb', 'main blvd' -> 'Main Boulevard (MB)'
- 'cr', 'crore' -> 'Crore' (e.g. '3.5 Crore')
- 'lac', 'lacs' -> 'Lac' (e.g. '425 Lac')

### STRICT 15-COLUMN CANONICAL CRM SCHEMA:
1. "Date / Timestamp": Exact timestamp from WhatsApp (or "{now_timestamp}")
2. "Category": 'Selling'
3. "Phase": Explicitly detected DHA Phase name OR "Unassigned Phase"
4. "Block": Canonical Block / CCA name (e.g. 'Block A', 'Block J', 'CCA 1 Commercial')
5. "Plot No": Extracted isolated plot identifier (e.g. 'Plot 125', 'Plot 450', 'Plot 18')
6. "Size": Strict normalized cutting size ('1 Kanal', '10 Marla', '5 Marla', '4 Marla Commercial')
7. "Plot Features": 'Corner', 'Facing Park', 'Main Boulevard (MB)', 'Possession', or 'Standard Layout'
8. "Demand / Price": Normalized asking rate in 'X Lac' or 'X Crore' (e.g. '425 Lac', '3.5 Crore')
9. "Seller Type": 'Authorized Dealer'
10. "Seller / Dealer Name": Extracted dealer name if mentioned, else ""
11. "Contact No": Clean Pakistani phone format ('03XXXXXXXXX' or '+923XXXXXXXXX')
12. "Office / Agency": "{st.session_state['office_name']}"
13. "Deal Status": 'Available'
14. "Last Conversation / Notes": 'Direct Ingestion'
15. "Raw Listing & Source Material": Full original WhatsApp message unit

OFFICIAL DHA CATALOG:
{catalog_json_str}

INPUT WHATSAPP STREAM:
{chunk_text}

OUTPUT: Return ONLY a valid JSON array of objects. No markdown code ticks (```json), no explanations.
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
                    if "Date / Timestamp" not in item or not item["Date / Timestamp"]:
                        item["Date / Timestamp"] = now_timestamp
                    blk = str(item.get("Block", "")).strip()
                    plt = str(item.get("Plot No", "")).strip()
                    sz = str(item.get("Size", "")).strip()
                    ph = item.get("Phase", "Unassigned Phase")
                    if plt and plt.lower() != "general option / portfolio" and ph != "Unassigned Phase":
                        item["Size"] = resolve_size_text_first_or_map(ph, blk, plt, sz)
                return parsed_json
        except Exception:
            pass
    return smart_accurate_rule_parser(chunk_text)

# Login & SSO Screen
if not st.session_state["authenticated"]:
    st.markdown("""
        <div style="background:#FFFFFF; border-bottom:1px solid #C5C6D0; padding:12px 24px; display:flex; justify-content:space-between; align-items:center; border-radius:12px; margin-bottom:20px;">
            <div style="font-family:'Manrope',sans-serif; font-weight:700; font-size:18px; color:#00113A; display:flex; align-items:center; gap:8px;">
                <span class="material-symbols-outlined" style="color:#00113A; font-size:24px;">dataset</span>
                <span>DHA Property Search Engine</span>
            </div>
            <div style="color:#757682; font-size:13px; font-weight:500;">
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
                <div style="color:#757682; font-size:13px; margin-top:4px;">Property Search Engine & CRM</div>
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

# Main Application Dashboard
else:
    gc_client = get_gspread_client()
    
    # 1. Header Banner
    col_h1, col_h2 = st.columns([2.6, 1.4])
    with col_h1:
        st.markdown(f"""
            <div class="header-banner">
                <div>
                    <h1 class="header-title">🏢 DHA Property Search Engine</h1>
                    <div class="header-subtitle">Live Streaming AI Ingestion & Multi-Phase Pipeline (Active: {st.session_state['user_email']})</div>
                </div>
                <span class="office-badge">📍 {st.session_state['office_name']}</span>
            </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
        col_hb1, col_hb2 = st.columns(2)
        with col_hb1:
            if st.button("👥 Dealer Ledger", use_container_width=True):
                show_dealer_ledger_dialog(st.session_state.get("parsed_payloads", []))
        with col_hb2:
            if st.button("📈 Analytics", use_container_width=True):
                show_price_analytics_dialog(st.session_state.get("parsed_payloads", []))

    # 2. Selectors & Direct Block Ribbon
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

    # Realigned Table Data Preparation with Bottom-Sorting for Unassigned Phase
    total_parsed_now = len(st.session_state["parsed_payloads"])
    if total_parsed_now > 0:
        base_data = []
        for item in st.session_state["parsed_payloads"]:
            ph_val = str(item.get("Phase", "Unassigned Phase"))
            base_data.append({
                "Date / Timestamp": str(item.get("Date / Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))),
                "Phase": ph_val,
                "Block No": str(item.get("Block", "Block A")),
                "Plot No": str(item.get("Plot No", "")),
                "Size": str(item.get("Size", "")),
                "Price": str(item.get("Demand / Price", "")),
                "Contact No": str(item.get("Contact No", "")),
                "Plot Features": str(item.get("Plot Features", "Standard Layout")),
                "Source Data": str(item.get("Raw Listing & Source Material", "")),
                "Status": str(item.get("Deal Status", "Available")),
                "_sort_key": 1 if ph_val == "Unassigned Phase" else 0
            })
        df_all_live = pd.DataFrame(base_data)
        df_all_live = df_all_live.sort_values(by=["_sort_key", "Date / Timestamp"], ascending=[True, False]).drop(columns=["_sort_key"])
    else:
        df_all_live = pd.DataFrame(columns=[
            "Date / Timestamp", "Phase", "Block No", "Plot No", "Size",
            "Price", "Contact No", "Plot Features", "Source Data", "Status"
        ])

    # Filter Bar
    col_sc1, col_sc2, col_sc3, col_sc4 = st.columns([1.2, 1.4, 1.4, 1.2])
    with col_sc1:
        edit_summary_mode = st.toggle("✏️ Edit Mode (ON / OFF)", value=False, key="toggle_summary_edit_mode")
        highlight_incomplete = st.toggle("⚠️ Incomplete Flags", value=False, key="toggle_incomplete_flags")
        
    all_dha_phases_summary = ["All Phases (Everything)", "⚠️ Unassigned Phase Only"] + list(DHA_PHASE_BLOCK_CATALOG.keys())
    with col_sc2:
        selected_summary_phase = st.selectbox("📍 Filter / Target Phase:", options=all_dha_phases_summary, index=0, key="summary_target_phase_select")

    if selected_summary_phase == "All Phases (Everything)":
        available_summary_tabs = ["All Block Tabs / CCAs"] + (sorted(list(df_all_live["Block No"].unique())) if total_parsed_now > 0 else [])
        df_filtered_summary_phase = df_all_live
    elif selected_summary_phase == "⚠️ Unassigned Phase Only":
        df_filtered_summary_phase = df_all_live[df_all_live["Phase"] == "Unassigned Phase"] if total_parsed_now > 0 else df_all_live
        available_summary_tabs = ["All Block Tabs / CCAs"] + (sorted(list(df_filtered_summary_phase["Block No"].unique())) if not df_filtered_summary_phase.empty else [])
    else:
        p_data = DHA_PHASE_BLOCK_CATALOG.get(selected_summary_phase, {})
        full_catalog_blocks = p_data.get("residential", []) + p_data.get("commercial", [])
        available_summary_tabs = ["All Block Tabs / CCAs"] + full_catalog_blocks
        df_filtered_summary_phase = df_all_live[df_all_live["Phase"] == selected_summary_phase] if total_parsed_now > 0 else df_all_live

    with col_sc3:
        selected_summary_block = st.selectbox("🧱 Filter / Target Block:", options=available_summary_tabs, index=0, key="summary_target_block_select")

    if selected_summary_block != "All Block Tabs / CCAs" and not df_filtered_summary_phase.empty:
        df_final_summary_display = df_filtered_summary_phase[df_filtered_summary_phase["Block No"] == selected_summary_block]
    else:
        df_final_summary_display = df_filtered_summary_phase

    # Global Search
    search_query = st.text_input("🔍 Global Search Across Listings (Plot No, Phone, Demand, Features):", placeholder="Type anything to search...", key="global_search_input")
    if search_query.strip() and not df_final_summary_display.empty:
        q = search_query.strip().lower()
        mask = df_final_summary_display.apply(lambda row: row.astype(str).str.lower().str.contains(q).any(), axis=1)
        df_final_summary_display = df_final_summary_display[mask]

    if highlight_incomplete and not df_final_summary_display.empty:
        inc_mask = (df_final_summary_display["Price"] == "") | (df_final_summary_display["Contact No"] == "")
        df_final_summary_display = df_final_summary_display[inc_mask]

    with col_sc4:
        st.metric(label="📊 Plots In View", value=f"{len(df_final_summary_display)}", delta=f"{total_parsed_now} Total Extracted")

    # KPI Summary Strip with Unassigned Counting Metric
    num_selected_live = len(df_final_summary_display)
    unique_tabs_count_live = df_final_summary_display[["Phase", "Block No"]].drop_duplicates().shape[0] if num_selected_live > 0 else 0
    with_demand_count_live = df_final_summary_display[df_final_summary_display["Price"] != ""].shape[0] if num_selected_live > 0 else 0
    unassigned_count_live = df_all_live[df_all_live["Phase"] == "Unassigned Phase"].shape[0] if total_parsed_now > 0 else 0

    st.markdown(f"""
        <div class="summary-card">
            <span class="stat-pill">📊 <b>Selected View:</b> {num_selected_live} Plots</span>
            <span class="stat-pill">📁 <b>Target Tabs:</b> {unique_tabs_count_live} Tabs</span>
            <span class="stat-pill">💰 <b>Prices Identified:</b> {with_demand_count_live}</span>
            <span class="stat-pill" style="background:{'#FEE2E2' if unassigned_count_live > 0 else '#ECEEF0'}; color:{'#991B1B' if unassigned_count_live > 0 else '#191C1E'};">⚠️ <b>Phase Not Detected:</b> {unassigned_count_live} Plots</span>
            <span class="stat-pill" style="background:#E0F2FE; color:#0369A1;">⚡ <b>Live Extracted:</b> {total_parsed_now} Listings</span>
        </div>
    """, unsafe_allow_html=True)

    # 3. Stitch 2-Column Split Dashboard (Left Ingestion Box + Right Extracted Table)
    col_stitch_left, col_stitch_right = st.columns([1.1, 2.9])

    with col_stitch_left:
        st.markdown("""
            <div class="stitch-card-container">
                <h4 style="font-family:'Manrope',sans-serif; color:#00113A; margin:0 0 6px 0; font-size:16px;">🧠 Ingestion Engine</h4>
                <p style="font-size:12px; color:#64748B; margin-bottom:10px;">Paste WhatsApp chats, exports, portal feeds, or upload files.</p>
            </div>
        """, unsafe_allow_html=True)
        default_box_value = st.session_state.get("extracted_file_text", "")
        raw_text = st.text_area(
            "Live Stream Input:",
            value=default_box_value,
            height=300,
            placeholder="Paste WhatsApp messages or ads here...",
            label_visibility="collapsed"
        )
        
        with st.expander("➕ Attach Sources (Files, Drive, OCR, Zameen, News)", expanded=False):
            tab_upload, tab_gdrive, tab_camera, tab_direct, tab_zameen, tab_news = st.tabs([
                "📎 Files", "☁️ Drive", "📸 OCR", "📋 Text", "🌐 Portal", "📰 News"
            ])
            with tab_upload:
                uploaded_file = st.file_uploader("Upload File:", type=["txt", "xlsx", "xls", "json", "csv", "pdf", "png", "jpg", "jpeg", "webp"], key="inner_file_uploader")
                if uploaded_file is not None:
                    try:
                        extracted_content = extract_text_from_any_file_or_image(uploaded_file, is_camera=False)
                        if extracted_content:
                            st.session_state["uploaded_temp_text"] = extracted_content
                            st.success("File ready!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                if st.session_state.get("uploaded_temp_text", ""):
                    if st.button("📥 Push to Box", key="btn_push_file_to_box"):
                        st.session_state["extracted_file_text"] = st.session_state["uploaded_temp_text"]
                        st.session_state["uploaded_temp_text"] = ""
                        st.rerun()
            with tab_gdrive:
                gdrive_url_in = st.text_input("G-Drive Link:", placeholder="[https://drive.google.com/](https://drive.google.com/)...", key="inner_gdrive_in")
                if st.button("📥 Load Drive", key="btn_push_gdrive_inner"):
                    if gdrive_url_in.strip():
                        gdrive_content = fetch_content_from_gdrive_url(gdrive_url_in.strip())
                        st.session_state["extracted_file_text"] = gdrive_content
                        st.rerun()
            with tab_camera:
                camera_photo = st.camera_input("Camera OCR:", key="inner_cam_in")
                if camera_photo is not None:
                    camera_text = extract_text_from_any_file_or_image(camera_photo, is_camera=True)
                    if st.button("📥 Load OCR", key="btn_push_cam_inner"):
                        st.session_state["extracted_file_text"] = camera_text
                        st.rerun()
            with tab_direct:
                pasted_txt = st.text_area("Direct Text:", height=80, key="inner_paste_in")
                if st.button("📥 Load Text", key="btn_push_direct_inner"):
                    st.session_state["extracted_file_text"] = pasted_txt.strip()
                    st.rerun()
            with tab_zameen:
                portal_url = st.text_input("Zameen URL:", placeholder="[https://www.zameen.com/](https://www.zameen.com/)...", key="inner_portal_in")
                if st.button("🌐 Load Portal", key="btn_push_portal_inner"):
                    portal_raw = fetch_text_from_portal_url(portal_url.strip())
                    st.session_state["extracted_file_text"] = portal_raw
                    st.rerun()
            with tab_news:
                st.markdown("""
                    <b>📰 Quick Access to Newspaper Portals:</b><br>
                    <a href="[https://classified.jang.com.pk](https://classified.jang.com.pk)" target="_blank" class="news-badge">📰 Daily Jang ↗</a>
                    <a href="[https://classifieds.dawn.com](https://classifieds.dawn.com)" target="_blank" class="news-badge">📰 Daily Dawn ↗</a>
                    <a href="[https://express.pk/epaper](https://express.pk/epaper)" target="_blank" class="news-badge">📰 Daily Express ↗</a>
                    <a href="[https://e.thenews.com.pk](https://e.thenews.com.pk)" target="_blank" class="news-badge">📰 The News ↗</a>
                    <a href="[https://epaper.nawaiwaqt.com.pk](https://epaper.nawaiwaqt.com.pk)" target="_blank" class="news-badge">📰 Daily Nawa-i-Waqt ↗</a>
                    <a href="[https://e.dunya.com.pk](https://e.dunya.com.pk)" target="_blank" class="news-badge">📰 Daily Dunya ↗</a>
                """, unsafe_allow_html=True)
                news_txt = st.text_area("Paste News Text:", height=80, key="inner_news_in")
                if st.button("📥 Load News", key="btn_push_news_inner"):
                    st.session_state["extracted_file_text"] = news_txt.strip()
                    st.rerun()

        col_in_btn1, col_in_btn2 = st.columns([2, 1])
        with col_in_btn1:
            if not st.session_state["extraction_active"]:
                if st.button("🚀 Extract Data", key="btn_run_stream_inner", use_container_width=True):
                    final_input_text = raw_text.strip()
                    if final_input_text:
                        chunks = split_raw_into_message_chunks(final_input_text, messages_per_chunk=100)
                        st.session_state["all_chunks"] = chunks
                        st.session_state["current_chunk_idx"] = 0
                        st.session_state["parsed_payloads"] = []
                        st.session_state["extraction_active"] = True
                        st.session_state["extraction_paused"] = False
                        st.rerun()
                    else:
                        st.warning("Please paste listings or attach files.")
        with col_in_btn2:
            if not st.session_state["extraction_active"]:
                if st.button("🗑️ Clear", key="btn_clear_ingestion_stream_box", use_container_width=True):
                    st.session_state["extracted_file_text"] = ""
                    st.session_state["uploaded_temp_text"] = ""
                    st.rerun()

    with col_stitch_right:
        # Table Header & Integrated Action Ribbon
        col_th_title, col_th_actions = st.columns([1.1, 2.9])
        with col_th_title:
            st.markdown("<h4 style='font-family:\"Manrope\",sans-serif; color:#00113A; margin:4px 0 0 0; font-size:16px;'>⚡ Extracted Inventory</h4>", unsafe_allow_html=True)
        
        # Valid Pushable Count (Excludes Unassigned Phase)
        df_valid_to_push = df_final_summary_display[df_final_summary_display["Phase"] != "Unassigned Phase"] if not df_final_summary_display.empty else pd.DataFrame()
        final_sync_count_live = len(df_valid_to_push)
        
        with col_th_actions:
            col_a_push, col_a_csv, col_a_xlsx, col_a_wa, col_a_pdf, col_a_clr = st.columns([1.8, 1, 1, 1.2, 1, 1.2])
            with col_a_push:
                if st.button(f"🚀 Push ({final_sync_count_live}) Sheets", disabled=(final_sync_count_live == 0), use_container_width=True):
                    if not gc_client:
                        st.error("GCP credentials not configured.")
                    else:
                        now_dt = datetime.now()
                        now_str = now_dt.strftime("%Y-%m-%d %H:%M")
                        grouped_data = {}
                        for _, row in df_valid_to_push.iterrows():
                            target_phase = str(row.get("Phase", "")).strip()
                            target_block = str(row.get("Block No", "Block A")).strip()
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
                            status_placeholder_sync.markdown(f"⏳ **Syncing:** `[{phase} ➔ {block}]` — ({idx+1}/{total_groups})")
                            if phase not in workbook_cache:
                                wb = get_phase_workbook(gc_client, phase)
                                workbook_cache[phase] = wb
                            
                            wb = workbook_cache[phase]
                            ws = get_or_create_clean_tab_exact(wb, block)
                            
                            rows_to_append = []
                            for row in rows_list:
                                plot_val = str(row.get("Plot No", "")).strip()
                                row_data = [
                                    str(row.get("Date / Timestamp", now_str)), "Selling", str(phase), str(block),
                                    str(plot_val), str(row.get("Size", "")), str(row.get("Plot Features", "Standard Layout")),
                                    str(row.get("Price", "")), "Authorized Dealer", "", str(row.get("Contact No", "")),
                                    str(st.session_state['office_name']), str(row.get("Status", "Available")), "Direct Ingestion",
                                    f"[AI Ingest] {str(row.get('Source Data', ''))}"
                                ]
                                rows_to_append.append(row_data)
                            
                            BULK_SLICE_SIZE = 500
                            for i in range(0, len(rows_to_append), BULK_SLICE_SIZE):
                                chunk_slice = rows_to_append[i:i + BULK_SLICE_SIZE]
                                safe_gspread_call(ws.append_rows, chunk_slice, value_input_option="USER_ENTERED")
                                saved_count += len(chunk_slice)
                                time.sleep(0.8)
                            
                            progress_bar_sync.progress((idx + 1) / total_groups)
                        
                        status_placeholder_sync.empty()
                        progress_bar_sync.empty()
                        st.success(f"🎉 Saved {saved_count} listings directly to Google Sheets!")
                        st.balloons()
            
            with col_a_csv:
                if not df_final_summary_display.empty:
                    st.download_button(label="CSV", data=df_final_summary_display.to_csv(index=False).encode('utf-8-sig'), file_name="DHA_Export.csv", mime="text/csv", use_container_width=True)
                else:
                    st.button("CSV", disabled=True, use_container_width=True)
            with col_a_xlsx:
                if not df_final_summary_display.empty:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_final_summary_display.to_excel(writer, sheet_name="DHA Listings", index=False)
                    st.download_button(label="Excel", data=excel_buffer.getvalue(), file_name="DHA_Export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.button("Excel", disabled=True, use_container_width=True)
            with col_a_wa:
                if st.button("WhatsApp", disabled=df_final_summary_display.empty, use_container_width=True):
                    show_whatsapp_share_dialog(df_final_summary_display)
            with col_a_pdf:
                if st.button("PDF", disabled=df_final_summary_display.empty, use_container_width=True):
                    show_pdf_catalog_dialog(df_final_summary_display)
            with col_a_clr:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state["parsed_payloads"] = []
                    st.session_state["extraction_active"] = False
                    st.session_state["extraction_paused"] = False
                    st.rerun()

        # Table Display Container (Height: 520px)
        if not df_final_summary_display.empty:
            if edit_summary_mode:
                final_summary_df = st.data_editor(
                    df_final_summary_display,
                    num_rows="dynamic",
                    height=520,
                    use_container_width=True,
                    key="summary_active_infinite_editor"
                )
            else:
                st.dataframe(df_final_summary_display, height=520, use_container_width=True)
        else:
            st.dataframe(df_final_summary_display, height=360, use_container_width=True)

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🧹 Remove Duplicates", disabled=df_final_summary_display.empty, use_container_width=True):
                initial_len = len(st.session_state["parsed_payloads"])
                df_temp = pd.DataFrame(st.session_state["parsed_payloads"])
                if not df_temp.empty:
                    df_dedup = df_temp.groupby(["Date / Timestamp", "Phase", "Block", "Plot No"], as_index=False).agg({
                        "Size": "first",
                        "Plot Features": lambda x: ", ".join(set([str(v) for v in x if str(v).strip()])),
                        "Demand / Price": "last",
                        "Seller Type": "first",
                        "Seller / Dealer Name": "first",
                        "Contact No": lambda x: " / ".join(set([str(v) for v in x if str(v).strip()])),
                        "Office / Agency": "first",
                        "Deal Status": "first",
                        "Last Conversation / Notes": "first",
                        "Raw Listing & Source Material": lambda x: " | ".join(set([str(v) for v in x if str(v).strip()]))
                    })
                    st.session_state["parsed_payloads"] = df_dedup.to_dict(orient="records")
                    st.success(f"Removed {initial_len - len(st.session_state['parsed_payloads'])} duplicates!")
                    st.rerun()
        with col_act2:
            if st.button("🏷️ Mark Visible Plots as Sold", disabled=df_final_summary_display.empty, use_container_width=True):
                plots_to_mark = set(df_final_summary_display["Plot No"].tolist())
                for item in st.session_state["parsed_payloads"]:
                    if item.get("Plot No") in plots_to_mark:
                        item["Deal Status"] = "Sold"
                st.success(f"Marked {len(plots_to_mark)} plots as SOLD!")
                st.rerun()

    # Active Live Streaming Loop (100-Message Chunker)
    if st.session_state["extraction_active"]:
        chunks = st.session_state["all_chunks"]
        curr_idx = st.session_state["current_chunk_idx"]
        total_chunks = len(chunks)
        
        st.markdown(f"""
            <div class="control-panel-box">
                <div style="font-size: 15px; font-weight: 700; color: #00113A; margin-bottom: 8px;">
                    ⚡ Live AI Streaming: Processing Chunk {curr_idx + 1} of {total_chunks} (100 msgs/chunk) • Streamed: {total_parsed_now} Listings into Summary
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
            with st.spinner(f"🧠 Processing Chunk {curr_idx + 1} of {total_chunks} (100 msgs)..."):
                chunk_to_process = chunks[curr_idx]
                new_listings = process_single_chunk_via_gemini(chunk_to_process)
                st.session_state["parsed_payloads"].extend(new_listings)
                st.session_state["current_chunk_idx"] += 1
                
                if st.session_state["current_chunk_idx"] >= total_chunks:
                    st.session_state["extraction_active"] = False
                    st.session_state["extraction_paused"] = False
                    st.rerun()
                else:
                    st.rerun()
