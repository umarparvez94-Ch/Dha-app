import streamlit as st
import gspread
import re
import json
import io
import os
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
    page_title="DHA Property CRM & AI Data Systems",
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
    .badge-buying { background-color: #DCFCE7; color: #16A34A; }
    .badge-rental { background-color: #E0F2FE; color: #0284C7; }
    .badge-feature { background-color: #FEF3C7; color: #D97706; }
    .badge-price { background-color: #ECFDF5; color: #059669; font-weight: 800; }
    .ai-badge-active { background: #DCFCE7; border: 1px solid #86EFAC; color: #15803D; font-size: 12.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }
    .ai-badge-inactive { background: #FEF3C7; border: 1px solid #FCD34D; color: #B45309; font-size: 12.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; display: inline-block; margin-bottom: 10px; }
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

@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    return gspread.service_account_from_dict(creds_dict)

def get_phase_workbook(gc, phase_name):
    target_url = DHA_PHASE_SHEET_URLS.get(phase_name)
    try:
        return gc.open_by_url(target_url)
    except Exception:
        return gc.open_by_url(DHA_PHASE_SHEET_URLS["DHA Phase 1"])

def get_or_create_clean_tab(workbook, tab_title):
    clean_title = tab_title.strip()
    try:
        ws = workbook.worksheet(clean_title)
    except gspread.exceptions.WorksheetNotFound:
        ws = workbook.add_worksheet(title=clean_title, rows=500, cols=16)
        ws.append_row(CRM_SHEET_HEADERS)
        return ws
    
    try:
        first_row = ws.row_values(1)
        if not first_row or len(first_row) < 3 or first_row[0] != CRM_SHEET_HEADERS[0]:
            ws.insert_row(CRM_SHEET_HEADERS, 1)
    except Exception:
        pass
    return ws

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
                        "You are a real estate OCR assistant. Transcribe and extract all property listing text, prices, phases, blocks, plot numbers, features, and phone numbers from this image clearly as readable text:",
                        img
                    ]
                )
                return res.text.strip()
            except Exception as e:
                return f"[Image OCR extraction error: {e}]"
        else:
            return "[Image loaded. Please configure GEMINI_API_KEY in secrets to extract live text.]"

    fname = file_obj.name.lower()
    
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
                pdf_text = []
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        pdf_text.append(txt)
                return "\n".join(pdf_text)
            except Exception as e:
                return f"[Error reading PDF: {e}]"
        else:
            return "[pypdf library not installed. Please add pypdf to requirements.txt]"

    elif fname.endswith(".txt"):
        return clean_whatsapp_chat_text(file_bytes)

    return ""

def parse_with_strict_gemini_schema(raw_text, default_phase):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    chunk_size = 12000
    text_chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]
    all_results = []

    for chunk in text_chunks:
        prompt = f"""You are an expert DHA Lahore Real Estate CRM extraction engine.
Parse the provided real estate text/data into a clean JSON list of individual property listings.

CRITICAL RULES:
1. Extract every single property listing into a separate dictionary.
2. Official Phase Names: 'DHA Phase 1', 'DHA Phase 2', 'DHA Phase 3', 'DHA Phase 4', 'DHA Phase 5', 'DHA Phase 6', 'DHA Phase 7', 'DHA Phase 8 (Proper)', 'DHA Phase 8 (Ivy Green / Sector Z)', 'DHA Phase 8 (Park View)', 'DHA Phase 8 (Air Avenue / Sector AA)', 'DHA Phase 9 Prism', 'DHA Phase 9 Town', 'DHA Phase 11 (Rahbar 1 to 4 & Sec 5)', 'DHA Phase 12 (EME Sector)'.
3. If Phase is not mentioned in a local group, use active context or fallback to default: '{default_phase}'.
4. Block names MUST strictly match catalog: {catalog_json_str}.
5. Extract Plot No, Size ('5 Marla', '10 Marla', '1 Kanal', '2 Kanal', etc.), Plot Features, Demand / Price, Contact No, Dealer Name.

Input Raw Text:
{chunk}

Return ONLY a valid JSON Array with format:
[
  {{
    "Category": "Selling",
    "Phase": "DHA Phase 7",
    "Block": "Block U",
    "Plot No": "Plot 398",
    "Size": "28 Marla",
    "Plot Features": "Standard Layout",
    "Demand / Price": "720 Lac",
    "Seller Type": "Dealer",
    "Seller / Dealer Name": "Direct Associate",
    "Contact No": "N/A",
    "Office / Agency": "Wali Muhammad Associates",
    "Deal Status": "Available",
    "Last Conversation / Notes": "Parsed via Google Gemini Strict Schema",
    "Raw Listing & Source Material": "398 U 720 Lac 28 Marla"
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
    main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else "N/A"
    
    current_phase = default_phase
    current_size = "1 Kanal"
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
        elif "10 MARLA" in l_up:
            current_size = "10 Marla"
            continue
        elif "5 MARLA" in l_up or "5.5 MARLA" in l_up:
            current_size = "5 Marla"
            continue
        elif "1 KANAL" in l_up:
            current_size = "1 Kanal"
            continue

        m = re.search(r'([A-Z0-9-]{1,3})\s*[-.:/ ]\s*([0-9]{1,5})\s*(?:@|\bDEMAND\b:?)?\s*(\d+\.?\d*)\s*(?:[.]?(LAC|LACS|CRORE|CR))?', l_up)
        if m:
            blk = f"Block {m.group(1).upper()}"
            plt = f"Plot {m.group(2)}"
            prc = f"{m.group(3)} {m.group(4) if m.group(4) else 'Lac'}".strip() if m.group(3) else "N/A"
            extracted.append({
                "Category": "Selling",
                "Phase": current_phase,
                "Block": blk,
                "Plot No": plt,
                "Size": current_size,
                "Plot Features": "Standard Layout",
                "Demand / Price": prc,
                "Seller Type": "Dealer",
                "Seller / Dealer Name": "Direct Associate",
                "Contact No": main_phone,
                "Office / Agency": st.session_state["office_name"],
                "Deal Status": "Available",
                "Last Conversation / Notes": "Fallback Local Engine",
                "Raw Listing & Source Material": line
            })
    return extracted

# 7. Popup Dialog
@st.dialog("⚡ Confirm Universal Multimodal Routing", width="large")
def show_routing_popup(payloads, phase_wb_map, gc_client):
    st.markdown("##### 🤖 Extraction Summary:")
    st.write(f"Parsed **{len(payloads)} distinct listings** from your input:")

    table_data = []
    for idx, item in enumerate(payloads):
        table_data.append({
            "Target Phase": item.get("Phase", "N/A"),
            "Target Tab": item.get("Block", "N/A"),
            "Plot": item.get("Plot No", "N/A"),
            "Size": item.get("Size", "1 Kanal"),
            "Features": item.get("Plot Features", "Standard Layout"),
            "Demand": item.get("Demand / Price", "N/A"),
            "Phone": item.get("Contact No", "N/A"),
            "Agency": item.get("Office / Agency", "N/A")
        })
    
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)
    st.info("💡 **Backend Action:** Each listing will be automatically segregated and saved into its respective DHA Phase Google Sheet and Block Tab!")

    col_btn1, col_btn2 = st.columns([1.5, 1])
    with col_btn1:
        if st.button("🚀 Confirm & Sync to Google Sheets", use_container_width=True):
            with st.spinner("Writing to Google Sheets..."):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                saved_count = 0
                for item in payloads:
                    target_phase = item.get("Phase", "DHA Phase 1")
                    target_block = item.get("Block", "Block A")
                    wb = get_phase_workbook(gc_client, target_phase)
                    ws = get_or_create_clean_tab(wb, target_block)
                    
                    row_data = [
                        now_str,
                        item.get("Category", "Selling"),
                        target_phase,
                        target_block,
                        item.get("Plot No", "N/A"),
                        item.get("Size", "1 Kanal"),
                        item.get("Plot Features", "Standard Layout"),
                        item.get("Demand / Price", "N/A"),
                        item.get("Seller Type", "Dealer"),
                        item.get("Seller / Dealer Name", "Direct Party"),
                        item.get("Contact No", "N/A"),
                        item.get("Office / Agency", st.session_state['office_name']),
                        item.get("Deal Status", "Available"),
                        item.get("Last Conversation / Notes", "Extracted via Multimodal AI"),
                        f"[AI Ingest] {item.get('Raw Listing & Source Material', '')}"
                    ]
                    ws.append_row(row_data)
                    saved_count += 1
                
                st.success(f"✅ Successfully saved all **{saved_count} listings** into their respective Block tabs!")
                st.balloons()
                st.session_state["parsed_payloads"] = []
                st.session_state["extracted_file_text"] = ""
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
            <div class="header-subtitle">AI Multi-Source Data Extraction Engine (Active: {st.session_state['user_email']})</div>
        </div>
    """, unsafe_allow_html=True)

    col_city, col_phase = st.columns([1.2, 2.5])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Multan", "Gujranwala"])
    with col_phase:
        phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
        selected_phase = st.selectbox("📍 Select DHA Phase (Active Workbook View)", phase_options, index=6)

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
        current_ws = get_or_create_clean_tab(phase_workbook, selected_active_block)
        records = current_ws.get_all_values()
        
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
                            current_ws.clear()
                            current_ws.update(updated_values)
                            st.success(f"✅ Google Sheet Tab **[{selected_active_block}]** successfully updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update error: {e}")
            else:
                st.dataframe(df, use_container_width=True, height=280)
                
                for idx, r in df.iterrows():
                    dem_val = r.get('Demand / Price', 'N/A')
                    phn_val = r.get('Contact No', 'N/A')
                    plt_val = r.get('Plot No', 'N/A')
                    sz_val = r.get('Size', 'N/A')
                    feat_val = r.get('Plot Features', 'Standard Layout')
                    cat_val = r.get('Category', 'Selling')
                    raw_val = r.get('Raw Listing & Source Material', '')

                    st.markdown(f"""
                        <div class="property-card">
                            <span class="badge badge-selling">{cat_val}</span>
                            <span class="badge badge-price">💰 {dem_val}</span>
                            <span class="badge badge-feature">⭐ {feat_val}</span>
                            <b>{selected_phase} {selected_active_block} — {plt_val} ({sz_val})</b>
                            <div style="margin-top: 5px; font-size: 13px; color: #475569;">📞 Contact: <b>{phn_val}</b> | Added: {r.get('Date / Timestamp', '')}</div>
                            <div style="margin-top: 4px; font-size: 12px; color: #64748B; background: #F8FAFC; padding: 5px 8px; border-radius: 6px;">📝 {raw_val}</div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Tab **[{selected_active_block}]** is active in Google Sheets. Currently 0 entries found. Add listings in the box below to see them appear here!")
    except Exception as e:
        st.error(f"Error connecting to Tab [{selected_active_block}]: {e}")

    st.markdown("---")

    # ==========================================================================
    # 3. BOTTOM SECTION: AI MULTI-SOURCE DATA EXTRACTION ENGINE
    # ==========================================================================
    if gemini_active:
        st.markdown('<div class="ai-badge-active">🟢 Google Gemini AI Extraction Engine: Connected & Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ai-badge-inactive">🟡 Gemini API Key Missing — Operating on Fallback Pattern Parser (Add GEMINI_API_KEY to Secrets for full AI power)</div>', unsafe_allow_html=True)

    st.subheader("🧠 AI Multi-Source Data Extraction Engine")
    
    col_u1, col_u2 = st.columns([1.6, 1.4])
    
    with col_u2:
        tab_upload, tab_camera, tab_direct = st.tabs(["📎 Upload File / Image", "📸 Live Camera", "📋 Direct Paste"])
        
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
        
        with tab_camera:
            camera_photo = st.camera_input("Take a photo of a property document / map / flyer:")
            if camera_photo is not None:
                with st.spinner("🧠 Scanning document via Google Vision OCR..."):
                    camera_text = extract_text_from_any_file_or_image(camera_photo, is_camera=True)
                    if camera_text:
                        st.session_state["extracted_file_text"] = camera_text
                        st.success("✅ Camera photo transcribed into the extraction box below!")

        with tab_direct:
            pasted_txt = st.text_area("Paste large WhatsApp exports or text blocks directly:", height=130, placeholder="Paste text here...")
            if st.button("📥 Load Pasted Text"):
                if pasted_txt.strip():
                    st.session_state["extracted_file_text"] = pasted_txt.strip()
                    st.success("✅ Text loaded into extraction box below!")

    with col_u1:
        default_box_value = st.session_state.get("extracted_file_text", "")
        
        raw_text = st.text_area(
            "📋 Raw Real Estate Data Ingestion (Ready for AI Processing):",
            value=default_box_value,
            height=220,
            placeholder="Data loaded from files, camera or copy-paste will appear here for processing..."
        )

    if st.button("🚀 Process, Segregate & Route to Block Tabs", use_container_width=True):
        final_input_text = raw_text.strip()
        if final_input_text:
            with st.spinner("🧠 AI Engine is segregating listings into respective DHA Phases & Blocks..."):
                payloads = parse_with_strict_gemini_schema(final_input_text, selected_phase)
                if payloads:
                    st.session_state["parsed_payloads"] = payloads
                    show_routing_popup(payloads, DHA_PHASE_SHEET_URLS, gc_client)
                else:
                    st.warning("No valid property listings could be identified in the text.")
        else:
            st.warning("Please provide listing text, take a camera photo, or upload a file.")
