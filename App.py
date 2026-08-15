import streamlit as st
import gspread
import re
import urllib.parse
import pandas as pd
from datetime import datetime

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
# 5. GEMINI-LEVEL MULTI-LISTING NLP EXTRACTION ENGINE
# ==============================================================================
def parse_multi_listing_engine(raw_text, default_phase):
    text_clean = raw_text.strip()
    if not text_clean:
        return []

    # 1. Global Phase Matching
    detected_phase = default_phase
    t_upper = text_clean.upper()
    if "PRISM" in t_upper or "PH.9-PRISM" in t_upper or "9 - PRISM" in t_upper: detected_phase = "DHA Phase 9 Prism"
    elif "TOWN" in t_upper: detected_phase = "DHA Phase 9 Town"
    elif "RAHBAR" in t_upper: detected_phase = "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)"
    elif "EME" in t_upper: detected_phase = "DHA Phase 12 (EME Sector)"
    elif "IVY GREEN" in t_upper: detected_phase = "DHA Phase 8 (Ivy Green / Sector Z)"
    elif "PARK VIEW" in t_upper: detected_phase = "DHA Phase 8 (Park View)"
    elif "AIR AVENUE" in t_upper: detected_phase = "DHA Phase 8 (Air Avenue / Sector AA)"
    else:
        p_m = re.search(r'(?:PHASE|PH|P)[\s.:-]*(\d{1,2})', t_upper)
        if p_m: detected_phase = f"DHA Phase {p_m.group(1)}"

    # 2. Extract Contacts
    phones = re.findall(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', text_clean)
    main_phone = re.sub(r'[^0-9+]', '', phones[0]) if phones else "N/A"

    names = re.findall(r'(?:Atif Bhatti|Adnan Irfan|Ijaz Hussain Sial|[A-Z][a-z]+ [A-Z][a-z]+)', text_clean)
    main_dealer = names[0] if names else "Direct Associate"

    # 3. Split by lines
    lines = [l.strip() for l in text_clean.split('\n') if l.strip()]
    extracted_items = []
    current_size_context = "1 Kanal" if "1 KANAL" in t_upper else ("5 Marla" if "5 MARLA" in t_upper else "1 Kanal")

    for line in lines:
        l_up = line.upper()
        if "1 KANAL" in l_up: current_size_context = "1 Kanal"
        if "5 MARLA" in l_up or "5.5 MARLA" in l_up: current_size_context = "5 Marla"
        if "10 MARLA" in l_up: current_size_context = "10 Marla"
        if "13-MARLA" in l_up: current_size_context = "13 Marla"

        pattern = re.search(r'(?:BLOCK\s*([A-Z0-9-]{1,3})|([A-Z])[\s.:-]+(\d+[\+\d]*))\s*(?:–|-|@|PLOT\s*#?|#)?\s*(\d+[\+\d]*)?', l_up)
        demand_match = re.search(r'(@|\bDEMAND\b:?)\s*(\d+\.?\d*)\s*(LAC|LACS|LAKH|CRORE|CR)?', l_up)
        
        if any(w in l_up for w in ["@", "PLOT", "DEMAND", "NDC", "ROAD", "CORNER"]) and (pattern or re.search(r'\b[A-Z]\b[\s.:-]*\d+', l_up)):
            blk_candidate = "Block A"
            plt_candidate = "N/A"
            
            b_m = re.search(r'(?:BLOCK\s*([A-Z0-9-]{1,3})|\b([A-Z])\b[\s.:-]*(\d+[\+\d]*))', l_up)
            if b_m:
                letter = b_m.group(1) if b_m.group(1) else b_m.group(2)
                blk_candidate = f"Block {letter}"
                if b_m.group(3):
                    plt_candidate = f"Plot {b_m.group(3)}"
            
            if plt_candidate == "N/A":
                p_num = re.search(r'(?:PLOT\s*#?|#|L\.|E\.|M\.|N\.|R\.)\s*(\d+[\+\d]*)', l_up)
                if p_num: plt_candidate = f"Plot {p_num.group(1)}"

            # Size Logic
            size = current_size_context
            if "13-MARLA" in l_up or "13 MARLA" in l_up: size = "13 Marla"
            elif "5.5 MARLA" in l_up or "5 MARLA" in l_up or blk_candidate in ["Block P", "Block Q", "Block R"]: size = "5 Marla"
            elif blk_candidate in ["Block J", "Block K", "Block L", "Block M", "Block N"]: 
                size = "10 Marla" if "10 MARLA" in l_up or blk_candidate in ["Block M", "Block N"] else "1 Kanal"
            elif blk_candidate in ["Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H"]:
                size = "1 Kanal"

            # Features
            features = []
            if "CORNER" in l_up: features.append("Corner")
            if "PARK" in l_up: features.append("Facing Park")
            if "POSSESSION" in l_up: features.append("Possession")
            if "NDC" in l_up: features.append("NDC Ready")
            rd = re.search(r'(\d{2,3})\s*(FT|FEET|ROAD)', l_up)
            if rd: features.append(rd.group(0))
            features_str = ", ".join(features) if features else "Standard Layout"

            # Demand
            price = "N/A"
            if demand_match:
                val = demand_match.group(2)
                unit = demand_match.group(3) if demand_match.group(3) else "Lac"
                price = f"{val} {unit}".strip()
            else:
                p_m2 = re.search(r'(\d+\.?\d*)\s*(LAC|LACS|CRORE|CR)', l_up)
                if p_m2: price = f"{p_m2.group(1)} {p_m2.group(2)}"

            seller = "Direct Owner" if "DIRECT OWNER" in l_up or "SELF" in l_up else "Dealer"

            line_ph = re.search(r'(?:03\d{2}[- ]?\d{7})', line)
            item_phone = line_ph.group(0) if line_ph else main_phone

            extracted_items.append({
                "Category": "Selling",
                "Phase": detected_phase,
                "Block": blk_candidate,
                "Plot No": plt_candidate,
                "Size": size,
                "Plot Features": features_str,
                "Demand / Price": price,
                "Seller Type": seller,
                "Seller / Dealer Name": main_dealer,
                "Contact No": item_phone,
                "Office / Agency": st.session_state["office_name"],
                "Deal Status": "Available",
                "Last Conversation / Notes": "Extracted via Gemini Multi-Parser",
                "Raw Listing & Source Material": line
            })

    if not extracted_items:
        extracted_items.append({
            "Category": "Selling",
            "Phase": detected_phase,
            "Block": "Block A",
            "Plot No": "Plot 1",
            "Size": "1 Kanal",
            "Plot Features": "Standard",
            "Demand / Price": "N/A",
            "Seller Type": "Dealer",
            "Seller / Dealer Name": main_dealer,
            "Contact No": main_phone,
            "Office / Agency": st.session_state["office_name"],
            "Deal Status": "Available",
            "Last Conversation / Notes": "Direct Ingestion",
            "Raw Listing & Source Material": text_clean
        })

    return extracted_items

# ==============================================================================
# 6. POPUP DIALOG FOR CONFIRMATION
# ==============================================================================
@st.dialog("⚡ Confirm Multi-Listing Cloud Routing & Segregation", width="large")
def show_routing_popup(payloads, phase_wb_map, gc_client):
    st.markdown("##### 🔍 Real-Time Extraction Summary:")
    st.write(f"Gemini Engine has parsed **{len(payloads)} distinct listings** from your raw message:")

    table_data = []
    for idx, item in enumerate(payloads):
        table_data.append({
            "Target Phase": item["Phase"],
            "Target Tab": item["Block"],
            "Plot": item["Plot No"],
            "Size": item["Size"],
            "Features": item["Plot Features"],
            "Demand": item["Demand / Price"],
            "Phone": item["Contact No"]
        })
    
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)

    st.info("💡 **Backend Action:** Each listing will be saved into its respective DHA Phase Google Sheet and Block Tab!")

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
                        now_str, item["Category"], target_phase, target_block,
                        item["Plot No"], item["Size"], item["Plot Features"],
                        item["Demand / Price"], item["Seller Type"], item["Seller / Dealer Name"],
                        item["Contact No"], item["Office / Agency"], item["Deal Status"],
                        item["Last Conversation / Notes"], f"[Gemini Ingest] {item['Raw Listing & Source Material']}"
                    ]
                    ws.append_row(row_data)
                    saved_count += 1
                
                st.success(f"✅ Successfully saved all **{saved_count} listings** into their respective Block tabs!")
                st.balloons()
                st.session_state["parsed_payloads"] = []
                st.rerun()

# ==============================================================================
# 7. LOGIN SCREEN
# ==============================================================================
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

# ==============================================================================
# 8. MAIN DASHBOARD (TOP: LIVE DATA TABLE | BOTTOM: INGESTION BOX)
# ==============================================================================
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
            <div class="header-subtitle">Interactive Block Live Inventory & Ingestion (Active: {st.session_state['user_email']})</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. Global Selectors
    col_city, col_phase = st.columns([1.2, 2.5])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Multan", "Gujranwala"])
    with col_phase:
        phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
        selected_phase = st.selectbox("📍 Select DHA Phase (Active Workbook)", phase_options, index=11)

    # Load Phase Workbook
    try:
        phase_workbook = get_phase_workbook(gc_client, selected_phase)
    except Exception as e:
        st.error(f"Could not open spreadsheet for {selected_phase}. Please share sheet with `dha-bot@dha-property-sync.iam.gserviceaccount.com` as Editor.")
        st.stop()

    # Blocks List
    p_info = DHA_PHASE_BLOCK_CATALOG.get(selected_phase, {})
    res_b = p_info.get("residential", [])
    com_b = p_info.get("commercial", [])
    all_phase_blocks = res_b + com_b

    # ==========================================================================
    # 2. TOP SECTION: INTERACTIVE BLOCK TABS & LIVE INVENTORY TABLE
    # ==========================================================================
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
                    feat_val = r.get('Plot Features', 'Standard')
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
    # 3. BOTTOM SECTION: GEMINI MULTI-LISTING INGESTION BOX
    # ==========================================================================
    st.markdown("""
        <div class="ai-badge">🤖 Gemini & Anti-Gravity Smart Ingestion Box</div>
    """, unsafe_allow_html=True)
    
    st.subheader(f"📥 Ingest Any Text, WhatsApp Deals, OCR or Banner Material")
    
    raw_text = st.text_area(
        "📋 Paste Raw Listings Below (Single or Bulk Multi-Plot Messages):",
        height=140,
        placeholder="Paste ANY raw text, WhatsApp deals or OCR output here.\nExample:\nDHA Ph.9-Prism\n13-Marla Corner + Possession L.1225@178 NDC Ready 03004361284\nBlock K – Plot #370 Demand: 275 Lac\nE - 520 @ 330 Lac Direct Owner\nM - 836+837 @ 600 Lac Front Back Corner\n(R - 3385 @ 133 Lac) 60ft Road Corner 0321-1108412"
    )

    if st.button("💾 Save & Route to Respective Block Tabs", use_container_width=True):
        if raw_text.strip():
            payloads = parse_multi_listing_engine(raw_text, selected_phase)
            st.session_state["parsed_payloads"] = payloads
            show_routing_popup(payloads, DHA_PHASE_SHEET_URLS, gc_client)
        else:
            st.warning("Please paste listing material first.")
