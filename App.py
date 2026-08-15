import streamlit as st
import gspread
import re
import json
import urllib.parse
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Property CRM & Data Systems",
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

# Setup Official Google Gemini AI Engine
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ==============================================================================
# 2. EXACT GOOGLE STITCH ROYAL BLUE CSS INJECTION
# ==============================================================================
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;600&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
    
    <style>
    #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }
    .stAppDeployButton { display: none !important; }
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }
    .stApp {
        background-color: #F8FAFB !important;
        font-family: 'Inter', sans-serif !important;
        color: #1A1B20 !important;
    }
    .stitch-navbar {
        background: #FAFAFF;
        border-bottom: 1px solid #C5C6D2;
        padding: 12px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0px 2px 6px rgba(0, 17, 58, 0.02);
    }
    .stitch-logo-text {
        font-family: 'Manrope', sans-serif;
        font-weight: 700;
        font-size: 20px;
        color: #00113A;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .header-banner {
        background: linear-gradient(135deg, #00113A 0%, #102A6B 100%);
        padding: 20px 24px;
        border-radius: 14px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 8px 20px -5px rgba(0, 17, 58, 0.2);
    }
    .header-title { font-family: 'Manrope', sans-serif; font-size: 24px; font-weight: 800; margin: 0; color: #FFFFFF; }
    .header-subtitle { color: #B3C5FF; font-size: 13px; margin-top: 4px; }
    .office-badge {
        background-color: #006B5E; color: #9FF2E1; padding: 5px 12px;
        border-radius: 16px; font-size: 12px; font-weight: 600; float: right;
    }
    .stitch-login-box {
        background: #FFFFFF;
        border: 1px solid rgba(197, 198, 210, 0.6);
        border-radius: 16px;
        box-shadow: 0px 8px 24px rgba(0, 17, 58, 0.04);
        padding: 32px 28px;
        margin-bottom: 16px;
        text-align: center;
    }
    .stitch-avatar {
        width: 60px; height: 60px; border-radius: 50%;
        background-color: #D6E2FF; border: 1px solid #B3C5FF;
        display: inline-flex; align-items: center; justify-content: center;
        color: #00113A; margin-bottom: 12px;
    }
    .property-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .badge {
        display: inline-block; padding: 3px 8px; border-radius: 5px;
        font-size: 11.5px; font-weight: 700; margin-right: 5px;
    }
    .badge-selling { background-color: #FEE2E2; color: #DC2626; }
    .badge-buying { background-color: #DCFCE7; color: #16A34A; }
    .badge-rental { background-color: #E0F2FE; color: #0284C7; }
    .badge-feature { background-color: #FEF3C7; color: #D97706; }
    .badge-price { background-color: #ECFDF5; color: #059669; font-weight: 800; }
    .ai-badge {
        background: #EEF2FF; border: 1px solid #C7D2FE; color: #3730A3;
        font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px; display: inline-block; margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. 15-COLUMN CRM HEADERS & COMPLETE 15-PHASE MASTER DIRECTORY
# ==============================================================================
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

# ==============================================================================
# 4. MASTER DHA LAHORE PHASE & MAP-MATCHED BLOCK CATALOG
# ==============================================================================
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

# ==============================================================================
# 5. GOOGLE GEMINI NATIVE MULTI-LISTING AI PARSER
# ==============================================================================
def parse_with_google_gemini(raw_text, default_phase):
    text_clean = raw_text.strip()
    if not text_clean:
        return []

    # Check if Gemini API key exists
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = f"""
            You are an expert DHA Lahore Real Estate CRM parser.
            Parse the following raw real estate text into a clean JSON list of individual property listings.
            
            Context Rules:
            1. Normalize Phase to official names like: "DHA Phase 1", "DHA Phase 2", "DHA Phase 3", "DHA Phase 4", "DHA Phase 5", "DHA Phase 6", "DHA Phase 7", "DHA Phase 8 (Proper)", "DHA Phase 8 (Ivy Green / Sector Z)", "DHA Phase 8 (Park View)", "DHA Phase 8 (Air Avenue / Sector AA)", "DHA Phase 9 Prism", "DHA Phase 9 Town", "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)", "DHA Phase 12 (EME Sector)".
            2. If Phase is missing for a line, inherit from previous lines context or default to: "{default_phase}".
            3. Normalize Block to format: "Block A", "Block B", "Block C", "Broadway Commercial", "CCA 1 Commercial", etc.
            4. Detect Size (e.g. 5 Marla, 10 Marla, 1 Kanal, 2 Kanal, 13 Marla, 4 Marla).
            5. Extract Plot No, Features (Corner, Facing Park, Pair, Direct Owner, etc), Demand / Price with unit (e.g. 600 Lac, 5.50 Crore), Contact Phone No, Dealer/Agency Name.
            6. Category must be one of: "Selling", "Buying", "Rental".
            
            Input Raw Text:
            \"\"\"{text_clean}\"\"\"

            Return ONLY valid JSON array with objects with keys:
            [
              {{
                "Category": "Selling",
                "Phase": "DHA Phase 6",
                "Block": "Block C",
                "Plot No": "Plot 845",
                "Size": "1 Kanal",
                "Plot Features": "Standard Layout",
                "Demand / Price": "600 Lac",
                "Seller Type": "Dealer",
                "Seller / Dealer Name": "Hunjra Real Estate",
                "Contact No": "03009550559",
                "Office / Agency": "Hunjra Real Estate",
                "Deal Status": "Available",
                "Last Conversation / Notes": "Parsed via Google Gemini AI",
                "Raw Listing & Source Material": "C-845@600.lac"
              }}
            ]
            """
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            parsed_data = json.loads(response.text)
            if isinstance(parsed_data, list) and len(parsed_data) > 0:
                return parsed_data
        except Exception as e:
            st.warning(f"Gemini API returned an error, falling back to heuristic engine: {e}")

    # Fallback heuristic parser
    return parse_fallback_heuristic(text_clean, default_phase)

def parse_fallback_heuristic(text_clean, default_phase):
    lines = [l.strip() for l in text_clean.split('\n') if l.strip()]
    phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', text_clean)
    main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else "N/A"
    
    current_phase = default_phase
    current_size = "1 Kanal"
    extracted = []
    
    for line in lines:
        l_up = line.upper()
        if "PHASE 6" in l_up: current_phase = "DHA Phase 6"; continue
        elif "PHASE 7" in l_up: current_phase = "DHA Phase 7"; continue
        elif "PHASE 9 PRISM" in l_up or "9-PRISM" in l_up: current_phase = "DHA Phase 9 Prism"; continue
        elif "10 MARLA" in l_up: current_size = "10 Marla"; continue
        elif "5 MARLA" in l_up: current_size = "5 Marla"; continue
        
        m = re.search(r'([A-Z0-9-]{1,3})\s*[-.:/]\s*([0-9]{1,5}(?:[\+/][0-9A-Za-z]+)?)\s*(?:@|\bDEMAND\b:?)?\s*(\d+\.?\d*)\s*(?:[.]?(LAC|LACS|CRORE|CR))?', l_up)
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
                "Last Conversation / Notes": "Fallback Ingestion",
                "Raw Listing & Source Material": line
            })
    return extracted

# ==============================================================================
# 6. POPUP DIALOG FOR CONFIRMATION
# ==============================================================================
@st.dialog("⚡ Confirm Google AI Multi-Listing Cloud Routing", width="large")
def show_routing_popup(payloads, phase_wb_map, gc_client):
    st.markdown("##### 🤖 Google Gemini AI Extraction Summary:")
    st.write(f"Google AI Model has parsed **{len(payloads)} distinct listings** from your raw message:")

    table_data = []
    for idx, item in enumerate(payloads):
        table_data.append({
            "Target Phase": item["Phase"],
            "Target Tab": item["Block"],
            "Plot": item["Plot No"],
            "Size": item["Size"],
            "Features": item.get("Plot Features", "Standard"),
            "Demand": item["Demand / Price"],
            "Phone": item.get("Contact No", "N/A"),
            "Agency": item.get("Office / Agency", "N/A")
        })
    
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)

    st.info("💡 **Backend Google Action:** Each listing will be automatically saved into its respective DHA Phase Google Sheet and Block Tab!")

    col_btn1, col_btn2 = st.columns([1.5, 1])
    with col_btn1:
        if st.button("🚀 Confirm & Sync to Google Sheets", use_container_width=True):
            with st.spinner("Writing to Google Sheets..."):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                saved_count = 0
                for item in payloads:
                    target_phase = item["Phase"]
                    target_block = item["Block"]
                    wb = get_phase_workbook(gc_client, target_phase)
                    ws = get_or_create_clean_tab(wb, target_block)
                    
                    row_data = [
                        now_str, item.get("Category", "Selling"), target_phase, target_block,
                        item.get("Plot No", "N/A"), item.get("Size", "1 Kanal"), item.get("Plot Features", "Standard Layout"),
                        item.get("Demand / Price", "N/A"), item.get("Seller Type", "Dealer"), item.get("Seller / Dealer Name", "Direct Party"),
                        item.get("Contact No", "N/A"), item.get("Office / Agency", st.session_state['office_name']), item.get("Deal Status", "Available"),
                        i
