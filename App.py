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

# Google GenAI SDK Setup
HAS_GENAI = False
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Enterprise Master Sheet & AI Engine",
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
if "gemini_last_error" not in st.session_state:
    st.session_state["gemini_last_error"] = ""

# Batch Processing State Machine
if "extraction_active" not in st.session_state:
    st.session_state["extraction_active"] = False
if "all_chunks" not in st.session_state:
    st.session_state["all_chunks"] = []
if "current_chunk_idx" not in st.session_state:
    st.session_state["current_chunk_idx"] = 0
if "extraction_default_phase" not in st.session_state:
    st.session_state["extraction_default_phase"] = "DHA Phase 9 Prism"

# 2. Strict Gemini 2.5 Multi-Source Key Resolver
gemini_client = None
gemini_active = False

api_key_val = (
    st.secrets.get("GEMINI_API_KEY") 
    or st.secrets.get("GOOGLE_API_KEY")
    or os.environ.get("GEMINI_API_KEY", "")
    or os.environ.get("GOOGLE_API_KEY", "")
)

if HAS_GENAI and api_key_val:
    try:
        gemini_client = genai.Client(api_key=str(api_key_val).strip())
        gemini_active = True
    except Exception as e:
        st.session_state["gemini_last_error"] = f"Client Init Error: {e}"
        gemini_active = False
else:
    if not HAS_GENAI:
        st.session_state["gemini_last_error"] = "google-genai SDK package missing."
    elif not api_key_val:
        st.session_state["gemini_last_error"] = "Missing GEMINI_API_KEY in Streamlit Secrets."

# 3. CSS Styling
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
    </style>
""", unsafe_allow_html=True)

CRM_SHEET_HEADERS = [
    "Date / Timestamp", "Phase", "Block", "Plot No", "Size", "Plot Features", 
    "Demand / Price", "Seller / Dealer Name", "Contact No", "Office / Agency", 
    "Deal Status", "Last Conversation / Notes", "Source"
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

DHA_PHASE_BLOCK_CATALOG = {
    "DHA Phase 6": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N"], "commercial": ["Main Boulevard (MB) Commercial", "CCA 1 Commercial", "CCA 2 Commercial"]},
    "DHA Phase 7": {"residential": ["Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y", "Block Z", "Block Z-1", "Block Z-2"], "commercial": ["CCA 1 Commercial", "CCA 2 Commercial"]},
    "DHA Phase 9 Prism": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"], "commercial": ["Zone 1 Commercial", "Zone 2 Commercial"]}
}

@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    return gspread.service_account_from_dict(creds_dict)

def get_phase_workbook(gc, phase_name):
    target_url = DHA_PHASE_SHEET_URLS.get(phase_name, DHA_PHASE_SHEET_URLS["DHA Phase 1"])
    return gc.open_by_url(target_url)

def get_or_create_clean_tab_exact(workbook, tab_title):
    clean_title = tab_title.strip()
    try:
        ws_list = workbook.worksheets()
        for w in ws_list:
            if w.title.strip().lower() == clean_title.lower():
                return w
        ws = workbook.add_worksheet(title=clean_title, rows=500, cols=16)
        ws.append_row(CRM_SHEET_HEADERS)
        return ws
    except Exception:
        return workbook.sheet1

def extract_text_from_file(file_obj):
    if file_obj is None:
        return ""
    return file_obj.getvalue().decode('utf-8', errors='ignore')

def segment_messages(raw_text):
    if not raw_text or not raw_text.strip():
        return []
    return [line.strip() for line in raw_text.split('\n') if line.strip()]

# ==============================================================================
# PURE GEMINI AI PROMPT EXTRACTION ENGINE
# ==============================================================================
def process_message_batch_via_gemini(message_lines, default_phase):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    batch_text = "\n".join(message_lines)

    prompt = f"""You are an Expert Real Estate Ingestion Engine powered by Gemini. 
Analyze the following raw WhatsApp text lines or broadcasts and extract every individual property listing.
Rely entirely on your intelligence to parse Phase, Block, Plot No, Size, Plot Features, Demand / Price, Seller / Dealer Name, Contact No, Office / Agency.
Default Phase if completely missing: {default_phase}

Input Text:
{batch_text}

Return ONLY a valid JSON array of objects with these exact keys:
[
  {{
    "Date / Timestamp": "{now_str}",
    "Phase": "...",
    "Block": "...",
    "Plot No": "...",
    "Size": "...",
    "Plot Features": "...",
    "Demand / Price": "...",
    "Seller / Dealer Name": "...",
    "Contact No": "...",
    "Office / Agency": "Wali Muhammad Associates",
    "Deal Status": "Available",
    "Last Conversation / Notes": "Direct Ingestion",
    "Source": "..."
  }}
]"""

    if gemini_active and gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            parsed_json = json.loads(response.text)
            if isinstance(parsed_json, list):
                return parsed_json
            return []
        except Exception as e:
            st.error(f"⚠️ Gemini API Error: {str(e)}")
            return []
    else:
        st.error("⚠️ Gemini API is inactive. Please check your API Key in Streamlit Secrets.")
        return []

# Login Screen
if not st.session_state["authenticated"]:
    st.markdown("""
        <div class="stitch-navbar">
            <div class="stitch-logo-text"><span>DHA Master Database Systems</span></div>
        </div>
    """, unsafe_allow_html=True)
    with st.form("login"):
        email_in = st.text_input("EMAIL")
        if st.form_submit_button("SIGN IN"):
            st.session_state["authenticated"] = True
            st.rerun()
else:
    try:
        gc_client = get_gspread_client()
    except Exception as e:
        st.error(f"⚠️ Google Sheets Connection Error: {str(e)}")
        st.stop()

    st.title("🏢 DHA Master Sheet & Pure AI Ingestion")

    selected_phase = st.selectbox("📍 Select Default Phase", list(DHA_PHASE_SHEET_URLS.keys()), index=11)
    
    uploaded_file = st.file_uploader("Upload WhatsApp Text File:", type=["txt", "csv"])
    if uploaded_file is not None:
        st.session_state["extracted_file_text"] = extract_text_from_file(uploaded_file)
        st.success("File uploaded successfully!")

    if st.button("🚀 ➔ Start AI Ingestion & Update Master Summary", type="primary"):
        text_data = st.session_state.get("extracted_file_text", "")
        if text_data:
            lines = segment_messages(text_data)
            chunks = [lines[i:i+30] for i in range(0, len(lines), 30)]
            st.session_state["all_chunks"] = chunks
            st.session_state["current_chunk_idx"] = 0
            st.session_state["parsed_payloads"] = []
            st.session_state["extraction_active"] = True
            st.rerun()
        else:
            st.warning("Please upload a file first.")

    st.markdown("---")
    st.subheader("📊 Master Summary Sheet (Live Spreadsheet View)")
    
    if len(st.session_state["parsed_payloads"]) > 0:
        df_master = pd.DataFrame(st.session_state["parsed_payloads"])
        edited_df = st.data_editor(df_master, use_container_width=True, height=350, key="master_grid")

        if st.button("🚀 Push to Official Google Sheets Tabs", type="primary"):
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            grouped = {}
            for _, row in edited_df.iterrows():
                tp = str(row.get("Phase", "DHA Phase 9 Prism")).strip()
                tb = str(row.get("Block", "Block A")).strip()
                grouped.setdefault((tp, tb), []).append(row)

            wb_cache = {}
            total_pushed = 0
            for (phase, block), rows in grouped.items():
                if phase not in wb_cache:
                    wb_cache[phase] = get_phase_workbook(gc_client, phase)
                ws = get_or_create_clean_tab_exact(wb_cache[phase], block)
                rows_to_push = [[
                    str(r.get("Date / Timestamp", now_str)), str(phase), str(block),
                    str(r.get("Plot No", "")), str(r.get("Size", "")), str(r.get("Plot Features", "Standard Layout")),
                    str(r.get("Demand / Price", "")), str(r.get("Seller / Dealer Name", "")), str(r.get("Contact No", "")),
                    str(r.get("Office / Agency", "Wali Muhammad Associates")), "Available", "Direct Ingestion", str(r.get("Source", ""))
                ] for r in rows]
                if rows_to_push:
                    ws.append_rows(rows_to_push, value_input_option="USER_ENTERED")
                    total_pushed += len(rows_to_push)
            st.success(f"🎉 Successfully pushed {total_pushed} records to Google Sheets!")
            st.balloons()
    else:
        st.info("Master Summary Sheet is empty. Upload your file and click **'Start AI Ingestion'**.")

    if st.session_state.get("extraction_active", False):
        chunks = st.session_state["all_chunks"]
        idx = st.session_state["current_chunk_idx"]
        if idx < len(chunks):
            with st.spinner(f"🧠 Gemini AI Processing Chunk {idx+1} of {len(chunks)}..."):
                new_items = process_message_batch_via_gemini(chunks[idx], selected_phase)
                st.session_state["parsed_payloads"].extend(new_items)
                st.session_state["current_chunk_idx"] += 1
                st.rerun()
        else:
            st.session_state["extraction_active"] = False
            st.success("🎉 Ingestion complete via Gemini AI!")
            st.rerun()
