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
    page_title="DHA Enterprise Master CRM & AI Engine",
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

# 2. Strict Gemini Key Resolver
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
        st.session_state["gemini_last_error"] = "Missing GEMINI_API_KEY in Secrets."

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
    .stitch-avatar { width: 60px; height: 60px; border-radius: 50%; background-color: #D6E2FF; border: 1px solid #B3C5FF; display: inline-flex; align-items: center; justify-content: center; color: #00113A; margin-bottom: 12px; }
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
    "DHA Phase 1": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P"], "commercial": ["Block F Commercial", "Block G Commercial", "Block H Commercial"]},
    "DHA Phase 2": {"residential": ["Block Q", "Block R", "Block S", "Block T", "Block U", "Block V"], "commercial": ["Commercial CCA"]},
    "DHA Phase 3": {"residential": ["Block W", "Block X", "Block Y", "Block Z", "Block XX"], "commercial": ["Y Block Commercial", "Z Block Commercial"]},
    "DHA Phase 4": {"residential": ["Block AA", "Block BB", "Block CC", "Block DD", "Block EE", "Block FF", "Block GG", "Block JJ", "Block KK"], "commercial": ["CCA 1 Commercial"]},
    "DHA Phase 5": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M"], "commercial": ["CCA 1 Commercial"]},
    "DHA Phase 6": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N"], "commercial": ["Main Boulevard (MB) Commercial", "CCA 1 Commercial", "CCA 2 Commercial"]},
    "DHA Phase 7": {"residential": ["Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y", "Block Z", "Block Z-1", "Block Z-2"], "commercial": ["CCA 1 Commercial", "CCA 2 Commercial"]},
    "DHA Phase 8 (Proper)": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y"], "commercial": ["Broadway Commercial"]},
    "DHA Phase 8 (Ivy Green / Sector Z)": {"residential": ["Block Z-1", "Block Z-2", "Block Z-3", "Block Z-4", "Block Z-5", "Block Z-6"], "commercial": ["Commercial CCA Sector Z"]},
    "DHA Phase 8 (Park View)": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K"], "commercial": ["Commercial Zone Park View"]},
    "DHA Phase 8 (Air Avenue / Sector AA)": {"residential": ["Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"], "commercial": ["Commercial CCA Air Avenue"]},
    "DHA Phase 9 Prism": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R"], "commercial": ["Zone 1 Commercial", "Zone 2 Commercial"]},
    "DHA Phase 9 Town": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E"], "commercial": ["Commercial CCA Phase 9 Town"]},
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": {"residential": ["Sector 1", "Sector 2", "Sector 2 Extension", "Sector 3", "Sector 4", "Sector 5"], "commercial": ["Rahbar CCA 1"]},
    "DHA Phase 12 (EME Sector)": {"residential": ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J"], "commercial": ["Civic Centre EME"]}
}

def clean_and_validate_block_name(phase_name, raw_block_str):
    if not raw_block_str:
        return "Block A"
    b_clean = str(raw_block_str).strip()
    if not b_clean.lower().startswith("block ") and not b_clean.lower().startswith("sector ") and not "commercial" in b_clean.lower():
        b_clean = f"Block {b_clean.upper()}"
    return b_clean

def clean_plot_number(plot_val):
    if not plot_val:
        return ""
    p_str = str(plot_val).strip()
    p_clean = re.sub(r'(?i)^plot\s*', '', p_str).strip()
    digits_only = re.sub(r'[^0-9A-Za-z-]', '', p_clean)
    return f"Plot {digits_only}" if digits_only else p_str

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
                    contents=["Extract all DHA Lahore property listings from this image:", img]
                )
                return res.text.strip()
            except Exception as e:
                return f"[Image OCR error: {e}]"
    
    fname = file_obj.name.lower() if hasattr(file_obj, 'name') else "file.txt"
    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        try:
            return pd.read_excel(io.BytesIO(file_bytes)).to_string(index=False)
        except Exception as e:
            return f"[Error reading Excel: {e}]"
    elif fname.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes)).to_string(index=False)
        except Exception as e:
            return f"[Error reading CSV: {e}]"
    elif fname.endswith(".pdf") and HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        except Exception as e:
            return f"[Error reading PDF: {e}]"
    return file_bytes.decode('utf-8', errors='ignore')

def segment_messages(raw_text):
    if not raw_text or not raw_text.strip():
        return []
    ts_split_regex = r'(?:\r?\n|^)(?=(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*-\s*[^:\n]+:|\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*-\s*[^:\n]+:))'
    raw_blocks = re.split(ts_split_regex, raw_text.strip())
    messages = []
    for block in raw_blocks:
        b_str = block.strip()
        if not b_str or "<Media omitted>" in b_str or "end-to-end encrypted" in b_str:
            continue
        all_phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', b_str)
        extracted_phone = re.sub(r'[^0-9+]', '', all_phones[0]) if all_phones else ""
        sender_name = ""
        header_match = re.search(r'-\s*([^:]+):', b_str)
        if header_match:
            raw_sender = header_match.group(1).strip()
            if not (raw_sender.startswith("+") or any(c.isdigit() for c in raw_sender)):
                sender_name = raw_sender
        cleaned_body = re.sub(r'^\s*\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*-\s*[^:\n]+:\s*', '', b_str).strip()
        messages.append({
            "full_message": cleaned_body if cleaned_body else b_str,
            "sender_name": sender_name,
            "contact_no": extracted_phone
        })
    return messages

# ==============================================================================
# PURE GEMINI AI PROMPT EXTRACTION ENGINE
# ==============================================================================
def process_message_batch_via_gemini(message_objects, default_phase):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    formatted_lines = [f"Sender: {m['sender_name']} | Phone: {m['contact_no']}\n{m['full_message']}" for m in message_objects]
    batch_text = "\n\n".join(formatted_lines)

    prompt = f"""You are the Master Real Estate Ingestion & Intelligence Engine powered by Gemini 2.5 Flash for Wali Muhammad Associates (DHA Lahore).
Analyze each broadcast or WhatsApp bundle and extract every individual property listing into a clean JSON array.

MASTER RULES:
1. PHASE & BLOCK: Detect the correct DHA Phase and Block matching catalog: {catalog_json_str}. Default phase if completely missing: '{default_phase}'.
2. MULTI-PLOT EXTRACTION: If a single message contains multiple plots/options, create a separate JSON object for each.
3. EXACT 12-COLUMN SCHEMA KEYS:
   - "Date / Timestamp": "{now_str}"
   - "Phase": Official DHA Phase name
   - "Block": Official Block Tab name
   - "Plot No": Plot Number (e.g. 'Plot 61')
   - "Size": Size of plot if mentioned
   - "Plot Features": 'Corner / Facing Park', 'Standard Layout', etc.
   - "Demand / Price": Standardized Price (e.g. '260 Lac')
   - "Seller / Dealer Name": Extracted dealer name or sender
   - "Contact No": Extracted phone number
   - "Office / Agency": Extracted agency or Wali Muhammad Associates
   - "Deal Status": 'Available'
   - "Last Conversation / Notes": 'Direct Ingestion'
   - "Source": Exact raw text snippet

Input Listings:
{batch_text}

Return ONLY a valid JSON Array:"""

    if gemini_active and gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            parsed_json = json.loads(response.text)
            if isinstance(parsed_json, list):
                cleaned = []
                for item in parsed_json:
                    tp = item.get("Phase", default_phase) or default_phase
                    item["Phase"] = tp
                    item["Block"] = clean_and_validate_block_name(tp, item.get("Block", "Block A"))
                    item["Plot No"] = clean_plot_number(item.get("Plot No", ""))
                    if not item.get("Date / Timestamp"):
                        item["Date / Timestamp"] = now_str
                    if not item.get("Office / Agency"):
                        item["Office / Agency"] = st.session_state["office_name"]
                    cleaned.append(item)
                return cleaned
            return []
        except Exception as e:
            st.error(f"⚠️ Gemini API Parsing Error: {str(e)}")
            return []
    else:
        st.error("⚠️ Gemini API is inactive. Please check your API Key in Streamlit Secrets.")
        return []

# Login Screen
if not st.session_state["authenticated"]:
    st.markdown("""
        <div class="stitch-navbar">
            <div class="stitch-logo-text">
                <span class="material-symbols-outlined" style="color:#00113A; font-size:26px;">dataset</span>
                <span>DHA Master Database Systems</span>
            </div>
            <div style="color: #757682; font-size: 13px; font-weight: 500;">Secure Access</div>
        </div>
    """, unsafe_allow_html=True)

    col_l1, col_center, col_l2 = st.columns([1, 1.3, 1])
    with col_center:
        st.markdown("""
            <div class="stitch-login-box">
                <div class="stitch-avatar"><span class="material-symbols-outlined" style="font-size:30px;">apartment</span></div>
                <div style="font-size:20px; font-weight:700; color:#00113A;">Welcome to DHA</div>
            </div>
        """, unsafe_allow_html=True)
        with st.form("stitch_login_form"):
            email_in = st.text_input("WORK EMAIL ADDRESS", placeholder="name@wali-associates.pk")
            pass_in = st.text_input("PASSWORD", type="password", placeholder="••••••••")
            if st.form_submit_button("SIGN IN →"):
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_in if email_in.strip() else "agent@dha.pk"
                st.rerun()

# Main Master Sheet Dashboard with full City, Phase, Block selectors
else:
    try:
        gc_client = get_gspread_client()
    except Exception as e:
        st.error(f"⚠️ Google Sheets Connection Error: {str(e)}")
        st.stop()

    col_h1, col_h2 = st.columns([3, 1.2])
    with col_h1:
        st.markdown(f"""
            <div class="header-banner">
                <span class="office-badge">📍 {st.session_state['office_name']}</span>
                <h1 class="header-title">🏢 DHA Master Sheet & Pure AI Ingestion Engine</h1>
                <div class="header-subtitle">Active Agent: {st.session_state['user_email']}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_h2:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("👥 Dealer Ledger & Directory", use_container_width=True):
            pass

    col_city, col_phase = st.columns([1.2, 2.5])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Multan", "Gujranwala"])
    with col_phase:
        phase_options = list(DHA_PHASE_SHEET_URLS.keys())
        selected_phase = st.selectbox("📍 Select Default DHA Phase", phase_options, index=11)

    sheet_base_link = DHA_PHASE_SHEET_URLS.get(selected_phase, "")
    p_info = DHA_PHASE_BLOCK_CATALOG.get(selected_phase, {"residential": ["Block A"], "commercial": []})
    all_phase_blocks = p_info.get("residential", []) + p_info.get("commercial", [])

    st.markdown(f"##### 🧱 Choose Block Sheet Tab for **[{selected_phase}]**:")
    selected_active_block = st.radio("Direct Block Switcher:", options=all_phase_blocks, horizontal=True, key="block_feature_tab_bar")

    try:
        active_wb = get_phase_workbook(gc_client, selected_phase)
        exact_block_tab_url = get_specific_tab_url(active_wb, sheet_base_link, selected_active_block)
    except Exception:
        exact_block_tab_url = sheet_base_link

    col_btn_info, col_btn_sheet = st.columns([1.5, 2.5])
    with col_btn_info:
        if st.button("ℹ️ Connection Details", use_container_width=True):
            pass
    with col_btn_sheet:
        st.link_button(f"📑 Open [{selected_active_block}] Tab in Google Sheets ↗", url=exact_block_tab_url, use_container_width=True)

    st.markdown("---")

    # Ingestion Control Panel
    st.subheader("🧠 Multi-Source WhatsApp & Listing Ingestion")
    with st.expander("➕ **Attach Files, Drive, OCR, Zameen, or Classifieds**", expanded=False):
        tab_upload, tab_gdrive, tab_camera, tab_direct, tab_zameen = st.tabs([
            "📎 Files", "☁️ G-Drive", "📸 Camera", "📋 Direct Paste", "🌐 Zameen/Portal"
        ])
        with tab_upload:
            uploaded_file = st.file_uploader("Upload TXT, Excel, PDF, or Image:", type=["txt", "xlsx", "xls", "json", "csv", "pdf", "png", "jpg", "jpeg"])
            if uploaded_file is not None:
                st.session_state["extracted_file_text"] = extract_text_from_any_file_or_image(uploaded_file)
                st.success(f"✅ Loaded `{uploaded_file.name}` ready for ingestion!")
        with tab_gdrive:
            gdrive_url_in = st.text_input("Google Drive Link:")
            if st.button("Fetch G-Drive"):
                if gdrive_url_in.strip():
                    st.session_state["extracted_file_text"] = fetch_content_from_gdrive_url(gdrive_url_in.strip())
                    st.success("✅ G-Drive loaded!")
        with tab_camera:
            camera_photo = st.camera_input("Take photo:")
            if camera_photo is not None:
                st.session_state["extracted_file_text"] = extract_text_from_any_file_or_image(camera_photo, is_camera=True)
                st.success("✅ Camera OCR loaded!")
        with tab_direct:
            pasted_txt = st.text_area("Paste WhatsApp Broadcasts Here:", height=100)
            if st.button("Load Pasted Text"):
                if pasted_txt.strip():
                    st.session_state["extracted_file_text"] = pasted_txt.strip()
                    st.success("✅ Text loaded for ingestion!")
        with tab_zameen:
            portal_url = st.text_input("Zameen / Portal URL:")
            if st.button("Scrape Portal"):
                if portal_url.strip():
                    st.session_state["extracted_file_text"] = fetch_text_from_portal_url(portal_url.strip())
                    st.success("✅ Portal content fetched!")

    # Start Extraction Button
    col_run1, col_run2 = st.columns([2, 1])
    with col_run1:
        if not st.session_state["extraction_active"]:
            if st.button("🚀 ➔ Start AI Ingestion & Update Master Summary", type="primary", use_container_width=True):
                final_input_text = st.session_state.get("extracted_file_text", "").strip()
                if final_input_text:
                    discrete_msgs = segment_messages(final_input_text)
                    chunks = [discrete_msgs[i:i+25] for i in range(0, len(discrete_msgs), 25)]
                    st.session_state["all_chunks"] = chunks
                    st.session_state["current_chunk_idx"] = 0
                    st.session_state["parsed_payloads"] = []
                    st.session_state["extraction_active"] = True
                    st.session_state["extraction_default_phase"] = selected_phase
                    st.rerun()
                else:
                    st.warning("⚠️ Please attach a file, paste text, or load a source first.")
    with col_run2:
        if st.session_state["extraction_active"]:
            if st.button("⏹️ Stop Extraction", use_container_width=True):
                st.session_state["extraction_active"] = False
                st.rerun()

    # ==========================================================================
    # MASTER SUMMARY SHEET (Spreadsheet Grid View with Live Multi-Tab Push)
    # ==========================================================================
    st.markdown("---")
    st.subheader("📊 Master Summary Sheet (Live Spreadsheet View)")

    total_parsed_now = len(st.session_state["parsed_payloads"])

    if total_parsed_now > 0:
        df_master = pd.DataFrame(st.session_state["parsed_payloads"])
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            sel_phase_filter = st.selectbox("📍 Filter Phase:", ["All Phases"] + list(df_master["Phase"].unique()))
        with col_m2:
            blocks_avail = ["All Blocks"] + (list(df_master[df_master["Phase"] == sel_phase_filter]["Block"].unique()) if sel_phase_filter != "All Phases" else list(df_master["Block"].unique()))
            sel_block_filter = st.selectbox("🧱 Filter Block:", blocks_avail)
        with col_m3:
            st.metric(label="Total Plots in Master View", value=len(df_master))

        df_display = df_master.copy()
        if sel_phase_filter != "All Phases":
            df_display = df_display[df_display["Phase"] == sel_phase_filter]
        if sel_block_filter != "All Blocks":
            df_display = df_display[df_display["Block"] == sel_block_filter]

        edited_master_df = st.data_editor(df_display, use_container_width=True, height=350, key="master_spreadsheet_editor")

        if st.button(f"🚀 Push ({len(edited_master_df)} Plots) to Official Google Sheets Tabs", type="primary", use_container_width=True):
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            grouped_data = {}
            for _, row in edited_master_df.iterrows():
                tp = str(row.get("Phase", "DHA Phase 9 Prism")).strip()
                tb = str(row.get("Block", "Block A")).strip()
                if (tp, tb) not in grouped_data:
                    grouped_data[(tp, tb)] = []
                grouped_data[(tp, tb)].append(row)

            wb_cache = {}
            total_pushed = 0
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_groups = len(grouped_data)
            for idx, ((phase, block), rows) in enumerate(grouped_data.items()):
                status_text.text(f"Syncing [{phase} ➔ {block}] ({idx+1}/{total_groups})...")
                if phase not in wb_cache:
                    wb_cache[phase] = get_phase_workbook(gc_client, phase)
                wb = wb_cache[phase]
                ws = get_or_create_clean_tab_exact(wb, block)
                rows_to_push = []
                for r in rows:
                    rows_to_push.append([
                        str(r.get("Date / Timestamp", now_str)),
                        str(phase),
                        str(block),
                        str(r.get("Plot No", "")),
                        str(r.get("Size", "")),
                        str(r.get("Plot Features", "Standard Layout")),
                        str(r.get("Demand / Price", "")),
                        str(r.get("Seller / Dealer Name", "")),
                        str(r.get("Contact No", "")),
                        str(r.get("Office / Agency", st.session_state["office_name"])),
                        "Available",
                        "Direct Ingestion",
                        str(r.get("Source", ""))
                    ])
                if rows_to_push:
                    ws.append_rows(rows_to_push, value_input_option="USER_ENTERED")
                    total_pushed += len(rows_to_push)
                progress_bar.progress((idx + 1) / total_groups)
                time.sleep(0.3)
            
            status_text.empty()
            progress_bar.empty()
            st.success(f"🎉 Successfully pushed {total_pushed} records across respective Phase & Block tabs in Google Sheets!")
            st.balloons()
    else:
        st.info("ℹ️ Master Summary Sheet is empty. Load your text/files above and click **'Start AI Ingestion'**.")

    # Active Background Stream Loop
    if st.session_state["extraction_active"]:
        chunks = st.session_state["all_chunks"]
        curr_idx = st.session_state["current_chunk_idx"]
        if curr_idx < len(chunks):
            with st.spinner(f"🧠 Gemini AI Processing Chunk {curr_idx + 1} of {len(chunks)}..."):
                new_items = process_message_batch_via_gemini(chunks[curr_idx], selected_phase)
                st.session_state["parsed_payloads"].extend(new_items)
                st.session_state["current_chunk_idx"] += 1
                st.rerun()
        else:
            st.session_state["extraction_active"] = False
            st.success("🎉 Ingestion complete via Gemini AI! Review your Master Summary below.")
            st.rerun()
