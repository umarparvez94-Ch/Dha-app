import streamlit as st
import gspread
import re
import json
import io
import pandas as pd
from datetime import datetime
from PIL import Image

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Property CRM & Multimodal Data Systems",
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

# Setup Official Google Gemini AI Engine
if HAS_GENAI and "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass

# 2. CSS Injection
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
    .ai-badge { background: #EEF2FF; border: 1px solid #C7D2FE; color: #3730A3; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px; display: inline-block; margin-bottom: 8px; }
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

def extract_text_from_any_file_or_image(file_obj, is_camera=False):
    if file_obj is None:
        return ""
    
    file_bytes = file_obj.getvalue()
    
    if is_camera or (hasattr(file_obj, 'name') and any(file_obj.name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])):
        if HAS_GENAI and "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                img = Image.open(io.BytesIO(file_bytes))
                res = model.generate_content([
                    "You are a real estate OCR assistant. Transcribe and extract all property listing text, prices, phases, blocks, plot numbers, features, and phone numbers from this image clearly as readable text:",
                    img
                ])
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
        try:
            return file_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"[Error reading Text file: {e}]"

    return ""

def parse_multimodal_gemini(raw_text, default_phase):
    catalog_json_str = json.dumps(DHA_PHASE_BLOCK_CATALOG)
    
    prompt = f"""You are an expert DHA Lahore Real Estate CRM extraction engine.
Parse the provided real estate text/data into a clean JSON list of individual property listings.

CRITICAL DISAMBIGUATION RULES:
1. DHA Lahore phases share common block letters (e.g. Block A is in Phase 1, Phase 5, Phase 6, Phase 8, Phase 9 Prism, Phase 9 Town, Phase 12 EME).
2. NEVER mix up Block A of Phase 1 with Block A of Phase 5 or Phase 6. Maintain strict contextual parent Phase hierarchy.
3. Official Phase Names: 'DHA Phase 1', 'DHA Phase 2', 'DHA Phase 3', 'DHA Phase 4', 'DHA Phase 5', 'DHA Phase 6', 'DHA Phase 7', 'DHA Phase 8 (Proper)', 'DHA Phase 8 (Ivy Green / Sector Z)', 'DHA Phase 8 (Park View)', 'DHA Phase 8 (Air Avenue / Sector AA)', 'DHA Phase 9 Prism', 'DHA Phase 9 Town', 'DHA Phase 11 (Rahbar 1 to 4 & Sec 5)', 'DHA Phase 12 (EME Sector)'.
4. If Phase is not mentioned in a local group, use active context or fallback to default: '{default_phase}'.
5. Block names MUST strictly match catalog: {catalog_json_str}.
6. Extract Size, Plot No, Features (Corner, Park Facing, Pair, 60ft/100ft road, NDC Ready, Direct Owner), Demand / Price with unit (e.g. 550 Lac, 6.25 Crore), Contact No, Dealer/Agency Name.

Input Raw Text:
{raw_text}

Return ONLY a valid JSON Array:
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
    "Last Conversation / Notes": "Parsed via Google Gemini Multimodal",
    "Raw Listing & Source Material": "398 U 720 Lac 28 Marla"
  }}
]"""

    if HAS_GENAI and "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            parsed = json.loads(response.text)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed
        except Exception:
            pass

    return parse_fallback_heuristic(raw_text, default_phase)

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
 
