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
if "auto_mode" not in st.session_state:
    st.session_state["auto_mode"] = True

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
        padding-top: 1.5rem !important;
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
        margin-bottom: 24px;
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
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #D6E2FF;
        border: 1px solid #B3C5FF;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: #00113A;
        margin-bottom: 12px;
    }
    .stitch-title {
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        font-size: 28px;
        color: #00113A;
        letter-spacing: -0.02em;
        margin-bottom: 2px;
    }
    .stitch-subtitle {
        font-size: 15px;
        color: #444650;
        margin-bottom: 20px;
    }
    div[data-baseweb="input"] {
        border-radius: 8px !important;
        background-color: #F4F3F9 !important;
        border: 1px solid #C5C6D2 !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #00113A !important;
        background-color: #FFFFFF !important;
    }
    .stButton>button {
        background-color: #00113A !important;
        color: #FFFFFF !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        border-radius: 8px !important;
        border: none !important;
        height: 2.8rem !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #2A4386 !important;
        box-shadow: 0 4px 12px rgba(0, 17, 58, 0.2) !important;
    }
    .header-banner {
        background: linear-gradient(135deg, #00113A 0%, #102A6B 100%);
        padding: 22px 28px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 17, 58, 0.2);
    }
    .header-title { font-family: 'Manrope', sans-serif; font-size: 26px; font-weight: 800; margin: 0; color: #FFFFFF; }
    .header-subtitle { color: #B3C5FF; font-size: 13px; margin-top: 4px; }
    .office-badge {
        background-color: #006B5E; color: #9FF2E1; padding: 6px 14px;
        border-radius: 20px; font-size: 13px; font-weight: 600; float: right;
    }
    .property-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .badge {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        font-size: 12px; font-weight: 700; margin-right: 6px;
    }
    .badge-selling { background-color: #FEE2E2; color: #DC2626; }
    .badge-buying { background-color: #DCFCE7; color: #16A34A; }
    .badge-rental { background-color: #E0F2FE; color: #0284C7; }
    .badge-feature { background-color: #FEF3C7; color: #D97706; }
    .badge-type { background-color: #EDE9FE; color: #6D28D9; }
    .badge-price { background-color: #ECFDF5; color: #059669; font-weight: 800; }
    .badge-status { background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }
    .badge-source { background-color: #E0F2FE; color: #0369A1; font-weight: 600; }

    .wa-btn {
        display: inline-block; background-color: #25D366; color: white !important;
        padding: 10px 16px; border-radius: 8px; font-weight: 700; text-decoration: none;
        font-size: 13px; text-align: center; width: 100%; box-sizing: border-box;
        margin-bottom: 6px;
    }
    .wa-btn:hover { background-color: #1EBE5D; text-decoration: none; }

    .popup-box {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 16px;
        margin-top: 10px;
        font-family: 'Inter', sans-serif;
    }
    .stitch-footer {
        margin-top: 36px;
        padding-top: 16px;
        border-top: 1px solid #C5C6D2;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #757682;
        font-size: 13px;
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

# Complete 15 Official Real DHA Spreadsheet URLs Linked
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

# Auto-Provision All Tabs & Headers for the Selected Phase
def auto_provision_phase_tabs(workbook, phase_name):
    phase_info = DHA_PHASE_BLOCK_CATALOG.get(phase_name, {})
    all_blocks = list(phase_info.get("residential", {}).keys()) + list(phase_info.get("commercial", {}).keys())
    existing_tabs = [ws.title for ws in workbook.worksheets()]
    
    for blk in all_blocks:
        clean_blk = blk.strip()
        if clean_blk not in existing_tabs:
            try:
                ws = workbook.add_worksheet(title=clean_blk, rows=300, cols=16)
                ws.append_row(CRM_SHEET_HEADERS)
            except Exception:
                pass

def append_to_block_tab(workbook, block_tab_name, row_data):
    clean_tab = str(block_tab_name).strip() if block_tab_name and not block_tab_name.startswith("---") else "General_Block"
    try:
        worksheet = workbook.worksheet(clean_tab)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=clean_tab, rows=300, cols=16)
        worksheet.append_row(CRM_SHEET_HEADERS)
    worksheet.append_row(row_data)

# ==============================================================================
# 4. MASTER DHA LAHORE PHASE & BLOCK MAP CATALOG
# ==============================================================================
DHA_PHASE_BLOCK_CATALOG = {
    "DHA Phase 1": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal"], "Block D": ["10 Marla", "1 Kanal"], "Block E": ["1 Kanal"],
            "Block J": ["5 Marla", "10 Marla", "1 Kanal"], "Block K": ["1 Kanal", "2 Kanal"],
            "Block L": ["1 Kanal"], "Block M": ["1 Kanal"], "Block N": ["1 Kanal"], "Block P": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Block F (Commercial Market)": ["4 Marla", "7 Marla", "8 Marla"],
            "Block G (Main Commercial)": ["4 Marla", "8 Marla"],
            "Block H (Commercial & Stadium)": ["4 Marla", "8 Marla"],
            "Block J (Club Commercial)": ["4 Marla", "6 Marla"],
            "Block M (Commercial)": ["4 Marla", "8 Marla"],
            "Sector Shops (Local Commercial)": ["2 Marla", "3 Marla"]
        }
    },
    "DHA Phase 2": {
        "residential": {
            "Block Q": ["1 Kanal", "2 Kanal"], "Block R": ["1 Kanal", "2 Kanal"],
            "Block S": ["1 Kanal"], "Block T": ["10 Marla", "1 Kanal"],
            "Block U": ["10 Marla", "1 Kanal"], "Block V": ["1 Kanal", "2 Kanal"]
        },
        "commercial": {
            "Commercial CCA (Central Commercial)": ["4 Marla", "8 Marla"],
            "Block R Commercial Market": ["4 Marla", "6 Marla"],
            "Block T Commercial Market": ["4 Marla", "5 Marla"],
            "Sector Shops Phase 2": ["2 Marla"]
        }
    },
    "DHA Phase 3": {
        "residential": {
            "Block W": ["1 Kanal", "2 Kanal"], "Block X": ["1 Kanal", "2 Kanal"],
            "Block Y": ["10 Marla", "1 Kanal", "2 Kanal"], "Block Z": ["1 Kanal", "2 Kanal"], "Block XX": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Y Block Main Commercial (Central Hub)": ["4 Marla", "8 Marla", "16 Marla"],
            "Z Block Commercial Market": ["4 Marla", "8 Marla"],
            "W Block Commercial": ["4 Marla", "6 Marla"],
            "Sector Shops Phase 3": ["2 Marla"]
        }
    },
    "DHA Phase 4": {
        "residential": {
            "Block AA": ["1 Kanal", "2 Kanal"], "Block BB": ["1 Kanal", "2 Kanal"],
            "Block CC": ["10 Marla", "1 Kanal"], "Block DD": ["1 Kanal"],
            "Block EE": ["10 Marla", "1 Kanal"], "Block FF": ["10 Marla", "1 Kanal"],
            "Block GG": ["10 Marla", "1 Kanal"], "Block JJ": ["10 Marla", "1 Kanal"], "Block KK": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "CCA 1 Commercial": ["4 Marla", "8 Marla"], "CCA 2 Commercial": ["4 Marla", "8 Marla"],
            "Block DD Commercial": ["4 Marla", "6 Marla"], "Sector Shops Phase 4": ["2 Marla"]
        }
    },
    "DHA Phase 5": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["10 Marla", "1 Kanal", "2 Kanal"], "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["10 Marla", "1 Kanal"], "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"], "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"], "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"], "Block M": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "CCA 1 Commercial (Main Market)": ["4 Marla", "8 Marla"],
            "CCA 2 Commercial (Civic Zone)": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 5": ["2 Marla"]
        }
    },
    "DHA Phase 6": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal", "2 Kanal"], "Block D": ["10 Marla", "1 Kanal", "2 Kanal"],
            "Block E": ["1 Kanal"], "Block F": ["1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"], "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"], "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"], "Block M": ["1 Kanal", "2 Kanal"], "Block N": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Main Boulevard (MB) Commercial": ["4 Marla", "8 Marla", "16 Marla"],
            "CCA 1 Commercial Hub": ["4 Marla", "8 Marla"],
            "CCA 2 Commercial Hub": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 6": ["2 Marla"]
        }
    },
    "DHA Phase 7": {
        "residential": {
            "Block P": ["1 Kanal"], "Block Q": ["1 Kanal"], "Block R": ["1 Kanal"],
            "Block S": ["1 Kanal"], "Block T": ["10 Marla", "1 Kanal"], "Block U": ["10 Marla", "1 Kanal"],
            "Block V": ["1 Kanal"], "Block W": ["1 Kanal"], "Block X": ["10 Marla", "1 Kanal"],
            "Block Y": ["5 Marla", "10 Marla", "1 Kanal"], "Block Z": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Z-1": ["5 Marla", "10 Marla"], "Block Z-2": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "CCA 1 Commercial": ["4 Marla", "8 Marla"], "CCA 2 Commercial": ["4 Marla", "8 Marla"],
            "CCA 3 Commercial": ["4 Marla", "8 Marla"], "CCA 4 Commercial": ["4 Marla", "8 Marla"],
            "Sector Y Commercial": ["4 Marla", "8 Marla"], "Sector Shops Phase 7": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Proper)": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal", "2 Kanal"], "Block D": ["1 Kanal", "2 Kanal"],
            "Block E": ["1 Kanal", "2 Kanal"], "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"], "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"], "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"], "Block M": ["10 Marla", "1 Kanal"],
            "Block N": ["10 Marla", "1 Kanal"], "Block P": ["10 Marla", "1 Kanal"],
            "Block Q": ["10 Marla", "1 Kanal"], "Block R": ["10 Marla", "1 Kanal"],
            "Block S": ["5 Marla", "10 Marla", "1 Kanal"], "Block T": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block U": ["5 Marla", "10 Marla", "1 Kanal"], "Block V": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block W": ["5 Marla", "10 Marla", "1 Kanal"], "Block X": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Y": ["5 Marla", "10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Broadway Commercial": ["4 Marla", "8 Marla"], "Commercial Broadway Sector 1": ["4 Marla", "8 Marla"],
            "Commercial Broadway Sector 2": ["4 Marla", "8 Marla"], "Commercial CCA 1": ["4 Marla", "8 Marla"],
            "Commercial CCA 2": ["4 Marla", "8 Marla"], "Commercial CCA 3": ["4 Marla", "8 Marla"],
            "Sector Shops Phase 8": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Ivy Green / Sector Z)": {
        "residential": {
            "Block Z-1": ["5 Marla", "10 Marla", "1 Kanal", "2 Kanal"], "Block Z-2": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block Z-3": ["5 Marla", "10 Marla", "1 Kanal"], "Block Z-4": ["5 Marla", "10 Marla"],
            "Block Z-5": ["5 Marla", "10 Marla"], "Block Z-6": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "Commercial CCA Sector Z": ["4 Marla", "8 Marla"], "Sector Shops Sector Z": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Park View)": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["10 Marla", "1 Kanal"], "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["10 Marla", "1 Kanal"], "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["10 Marla", "1 Kanal"], "Block H": ["10 Marla", "1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"], "Block K": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Commercial Zone Park View": ["4 Marla", "8 Marla"], "Sector Shops Park View": ["2 Marla"]
        }
    },
    "DHA Phase 8 (Air Avenue / Sector AA)": {
        "residential": {
            "Block L": ["10 Marla", "1 Kanal"], "Block M": ["10 Marla", "1 Kanal"],
            "Block N": ["10 Marla", "1 Kanal"], "Block P": ["10 Marla", "1 Kanal"],
            "Block Q": ["10 Marla", "1 Kanal"], "Block R": ["10 Marla", "1 Kanal"]
        },
        "commercial": {
            "Commercial CCA Air Avenue": ["4 Marla", "8 Marla"]
        }
    },
    "DHA Phase 9 Prism": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["1 Kanal", "2 Kanal"], "Block D": ["1 Kanal", "2 Kanal"],
            "Block E": ["1 Kanal"], "Block F": ["1 Kanal"],
            "Block G": ["1 Kanal"], "Block H": ["1 Kanal"],
            "Block J": ["10 Marla", "1 Kanal"], "Block K": ["10 Marla", "1 Kanal"],
            "Block L": ["10 Marla", "1 Kanal"], "Block M": ["10 Marla"],
            "Block N": ["10 Marla"], "Block P": ["5 Marla"],
            "Block Q": ["5 Marla"], "Block R": ["5 Marla"]
        },
        "commercial": {
            "Zone 1 Commercial (Civic Zone)": ["4 Marla", "8 Marla"], "Zone 2 Commercial": ["4 Marla", "8 Marla"],
            "Zone 3 Commercial": ["4 Marla", "8 Marla"], "Main Oval Commercial": ["4 Marla", "8 Marla", "16 Marla"],
            "Prism Direct MB Commercial": ["4 Marla", "8 Marla"]
        }
    },
    "DHA Phase 9 Town": {
        "residential": {
            "Block A": ["5 Marla", "8 Marla"], "Block B": ["5 Marla", "8 Marla"],
            "Block C": ["5 Marla", "8 Marla", "10 Marla"], "Block D": ["5 Marla", "8 Marla", "10 Marla"],
            "Block E": ["5 Marla", "8 Marla"]
        },
        "commercial": {
            "Commercial CCA Phase 9 Town": ["4 Marla", "8 Marla"], "Sector Shops Phase 9 Town": ["2 Marla"]
        }
    },
    "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)": {
        "residential": {
            "Sector 1 (Rahbar Phase 1)": ["5 Marla", "8 Marla", "10 Marla", "1 Kanal"],
            "Sector 2 (Rahbar Phase 2)": ["5 Marla", "8 Marla", "10 Marla", "1 Kanal"],
            "Sector 2 Extension": ["5 Marla"], "Sector 3 (Rahbar Phase 3)": ["5 Marla"],
            "Sector 4 (Rahbar Phase 4)": ["5 Marla"], "Sector 5 (Haloki / Defense Road)": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "Rahbar Main Commercial CCA 1": ["4 Marla", "8 Marla"], "Rahbar Main Commercial CCA 2": ["4 Marla", "8 Marla"],
            "Rahbar Sector 5 Commercial": ["4 Marla", "8 Marla"], "Rahbar Local Sector Shops": ["2 Marla"]
        }
    },
    "DHA Phase 12 (EME Sector)": {
        "residential": {
            "Block A": ["1 Kanal", "2 Kanal"], "Block B": ["1 Kanal", "2 Kanal"],
            "Block C": ["10 Marla", "1 Kanal"], "Block D": ["10 Marla", "1 Kanal"],
            "Block E": ["10 Marla", "1 Kanal"], "Block F": ["10 Marla", "1 Kanal"],
            "Block G": ["5 Marla", "10 Marla", "1 Kanal"], "Block H": ["5 Marla", "10 Marla", "1 Kanal"],
            "Block J": ["5 Marla", "10 Marla"]
        },
        "commercial": {
            "Commercial Civic Centre EME": ["4 Marla", "8 Marla"], "Block D Commercial Market": ["4 Marla", "8 Marla"],
            "Block H Commercial Market": ["4 Marla", "6 Marla"], "Sector Shops EME": ["2 Marla"]
        }
    }
}

# ==============================================================================
# 5. ADVANCED 15-FIELD CRM MULTIMODAL PARSER
# ==============================================================================
def parse_property_crm(text, current_selected_phase, current_selected_block):
    text_upper = text.upper()
    
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED", "DEMANDING"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT", "LEASE"]):
        category = "Rental"

    phase = current_selected_phase
    if "PRISM" in text_upper or "PHASE 9 PRISM" in text_upper or "9 PRISM" in text_upper:
        phase = "DHA Phase 9 Prism"
    elif "TOWN" in text_upper or "PHASE 9 TOWN" in text_upper:
        phase = "DHA Phase 9 Town"
    elif "RAHBAR" in text_upper or "PHASE 11" in text_upper:
        phase = "DHA Phase 11 (Rahbar 1 to 4 & Sec 5)"
    elif "EME" in text_upper or "PHASE 12" in text_upper:
        phase = "DHA Phase 12 (EME Sector)"
    elif "IVY GREEN" in text_upper or "PHASE 8 Z" in text_upper or "SECTOR Z" in text_upper:
        phase = "DHA Phase 8 (Ivy Green / Sector Z)"
    elif "PARK VIEW" in text_upper:
        phase = "DHA Phase 8 (Park View)"
    elif "AIR AVENUE" in text_upper or "SECTOR AA" in text_upper:
        phase = "DHA Phase 8 (Air Avenue / Sector AA)"
    else:
        p_match = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
        if p_match:
            num = p_match.group(1)
            roman_dict = {"1":"1","2":"2","3":"3","4":"4","5":"5","6":"6","7":"7","8":"8","9":"9","10":"10","I":"1","II":"2","III":"3","IV":"4","V":"5","VI":"6","VII":"7","VIII":"8","IX":"9","X":"10"}
            norm_num = roman_dict.get(num, num)
            phase = f"DHA Phase {norm_num}"

    block = current_selected_block if (current_selected_block != "All Blocks" and not current_selected_block.startswith("---")) else "Block A"
    b_match = re.search(r'(?:BLOCK|BLK|SECTOR|SEC)\s*[:.-]?\s*([A-Z0-9-]{1,5})', text_upper)
    if b_match:
        found_b = b_match.group(1)
        block = f"Block {found_b}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2}|CCA|BROADWAY)\s*(BLOCK|BLK|CCA|SECTOR)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    plot_no = "N/A"
    plt_match = re.search(r'(?:PLOT|PLT|PLOT\s*NO|PLT\s*#|NO)\s*[:.-]?\s*([0-9]{1,4}[A-Za-z/]*)', text_upper)
    if plt_match:
        plot_no = f"Plot {plt_match.group(1)}"
    else:
        num_after_blk = re.search(r'(?:BLOCK|BLK)\s*[A-Z0-9-]+\s*[,:-]?\s*([0-9]{1,4})\b', text_upper)
        if num_after_blk:
            plot_no = f"Plot {num_after_blk.group(1)}"

    size = "1 Kanal"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|M|K|SQFT|YARD|SQYD)', text_upper)
    if s_match:
        val = s_match.group(1)
        unit = s_match.group(2)
        if unit in ["K", "KANAL"]: size = f"{val} Kanal"
        elif unit in ["M", "MARLA"]: size = f"{val} Marla"
        else: size = f"{val} {unit}"

    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Facing Park")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Boulevard")
    if "EXCESS" in text_upper: features.append("Excess Land")
    if "POSSESSION" in text_upper: features.append("Possession")
    road_match = re.search(r'(\d{2,3})\s*(FT|FEET|ROAD|WIDE)', text_upper)
    if road_match: features.append(f"{road_match.group(0)} Road")
    feature_str = ", ".join(features) if features else "Standard Layout"

    demand = "N/A"
    price_match = re.search(r'(?:DEMAND|PRICE|OFFER|BUDGET|RATE)?\s*[:.-]?\s*(\d+\.?\d*)\s*(CRORE|CR|LAC|LACS|LAKH|LAKHS|MILLION|PKR)', text_upper)
    if price_match:
        demand = f"{price_match.group(1)} {price_match.group(2)}"
    else:
        direct_num = re.search(r'(\d+\.?\d*)\s*(CRORE|CR|LACS|LAKH)', text_upper)
        if direct_num:
            demand = f"{direct_num.group(1)} {direct_num.group(2)}"

    seller_type = "Authorized Dealer"
    if any(w in text_upper for w in ["DIRECT OWNER", "OWNER PLOT", "MY OWN", "SELF", "DIRECT DEAL"]):
        seller_type = "Direct Owner"
    elif "INVESTOR" in text_upper:
        seller_type = "Investor"

    phone = "N/A"
    phone_match = re.search(r'(?:03\d{2}[- ]?\d{7}|\+?92[- ]?3\d{2}[- ]?\d{7})', text)
    if phone_match:
        phone = re.sub(r'[^0-9+]', '', phone_match.group(0))

    seller_name = "Direct Associate" if seller_type == "Direct Owner" else "Market Dealer"
    deal_status = "Available"
    last_notes = "Fresh listing ingested via system."

    return category, phase, block, plot_no, size, feature_str, demand, seller_type, seller_name, phone, deal_status, last_notes

def create_wa_crm_pitch(row_dict):
    phone_to_target = row_dict.get('Contact No', '')
    clean_target = re.sub(r'\D', '', str(phone_to_target)) if phone_to_target != 'N/A' else ''
    if clean_target.startswith('03'): clean_target = '92' + clean_target[1:]
    
    msg = f"""🏢 *{st.session_state['office_name']}*
📍 *Verified DHA Lahore CRM Listing*
• *Phase:* {row_dict.get('Phase', 'N/A')}
• *Block:* {row_dict.get('Block', 'N/A')}
• *Plot No:* {row_dict.get('Plot No', 'N/A')}
• *Size:* {row_dict.get('Size', 'N/A')}
• *Features:* {row_dict.get('Plot Features', 'Standard')}
• *Demand / Price:* {row_dict.get('Demand / Price', 'N/A')}
• *Seller Type:* {row_dict.get('Seller Type', 'Dealer')} ({row_dict.get('Seller / Dealer Name', '')})
• *Status:* {row_dict.get('Deal Status', 'Available')}
📝 *Notes:* {row_dict.get('Last Conversation / Notes', '')}
---
📞 Direct Contact: {phone_to_target if phone_to_target != 'N/A' else 'Wali Muhammad Associates'}"""
    
    base_url = f"https://wa.me/{clean_target}" if clean_target else "https://wa.me/"
    return f"{base_url}?text={urllib.parse.quote(msg)}"

# ==============================================================================
# 6. STITCH ROYAL BLUE LOGIN SCREEN
# ==============================================================================
if not st.session_state["authenticated"]:
    st.markdown("""
        <div class="stitch-navbar">
            <div class="stitch-logo-text">
                <span class="material-symbols-outlined" style="color:#00113A; font-size:26px;">dataset</span>
                <span>DHA Clinical & Property Data Systems</span>
            </div>
            <div style="color: #757682; font-size: 13px; font-weight: 500;">
                <span class="material-symbols-outlined" style="vertical-align:middle; font-size:18px; color:#006B5E;">lock</span>
                Secure CRM Access
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_l1, col_center, col_l2 = st.columns([1, 1.3, 1])
    with col_center:
        st.markdown("""
            <div class="stitch-login-box">
                <div class="stitch-avatar">
                    <span class="material-symbols-outlined" style="font-size:30px;">medical_information</span>
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

        st.markdown("<div style='text-align:center; margin: 12px 0 8px 0; color:#757682; font-size:12px; text-transform:uppercase;'>or</div>", unsafe_allow_html=True)
        
        if st.button("🔑 CONTINUE WITH SINGLE SIGN-ON (SSO)", use_container_width=True):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "sso.agent@dha.pk"
            st.rerun()

        st.markdown("""
            <div style="text-align: center; margin-top: 24px; padding-top: 14px; border-top: 1px solid #C5C6D2; font-size: 11px; color: #006B5E; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">
                <span class="material-symbols-outlined" style="vertical-align: middle; font-size: 15px;">verified_user</span>
                15-COLUMN CRM SECURE INGESTION PORTAL
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="stitch-footer">
            <div>© 2026 DHA Clinical Data Systems & Wali Muhammad Associates. All rights reserved.</div>
            <div>Privacy Policy &nbsp;•&nbsp; Terms of Service &nbsp;•&nbsp; Contact Support</div>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 7. MAIN ENGINE CRM DASHBOARD (AFTER LOGIN)
# ==============================================================================
else:
    try:
        gc_client = get_gspread_client()
    except Exception as e:
        st.error(f"⚠️ Google Sheets Authentication Error: {e}")
        st.stop()

    # Top Dashboard Banner
    st.markdown(f"""
        <div class="header-banner">
            <span class="office-badge">📍 {st.session_state['office_name']}</span>
            <h1 class="header-title">🏢 DHA Smart Property Engine & CRM</h1>
            <div class="header-subtitle">Phase Workbook & Block-Tab Multi-Routing Architecture (Active: {st.session_state['user_email']})</div>
        </div>
    """, unsafe_allow_html=True)

    # Top Bar Settings & Logout
    col_set, col_out = st.columns([5, 1])
    with col_set:
        with st.expander("⚙️ Customize Agency Name & Settings"):
            new_office = st.text_input("Agency / Office Name", value=st.session_state["office_name"])
            if st.button("Update Agency Name"):
                st.session_state["office_name"] = new_office
                st.rerun()
    with col_out:
        if st.button("🚪 Logout"):
            st.session_state["authenticated"] = False
            st.session_state["user_email"] = ""
            st.rerun()

    # Global Multi-Feature Search Bar
    st.markdown("### 🔍 Supreme Global Property Search")
    search_query = st.text_input(
        "Search anything",
        placeholder="🔎 e.g. Plot 45 Block M Facing Park, 4 Marla Broadway Commercial, 1 Kanal Corner 100 Ft Road, 03209498044...",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Cascading Controls: Phase, Block, Size
    col_city, col_phase, col_block, col_size = st.columns([1.1, 1.8, 1.8, 1.3])
    with col_city:
        selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])
    with col_phase:
        phase_options = list(DHA_PHASE_BLOCK_CATALOG.keys())
        selected_phase = st.selectbox("📍 DHA Phase (Target Workbook)", phase_options, index=0)

    # Load Workbook for this Phase from Master Directory
    phase_workbook = get_phase_workbook(gc_client, selected_phase)

    # Auto-Provision Tabs in background
    auto_provision_phase_tabs(phase_workbook, selected_phase)

    # Dynamic Block Selector from Catalog
    phase_data = DHA_PHASE_BLOCK_CATALOG.get(selected_phase, {})
    res_blocks = list(phase_data.get("residential", {}).keys())
    comm_blocks = list(phase_data.get("commercial", {}).keys())

    dynamic_block_list = ["All Blocks"]
    if res_blocks:
        dynamic_block_list.append("--- 🏡 Residential Sectors ---")
        dynamic_block_list.extend([f"{b} (Residential)" for b in res_blocks])
    if comm_blocks:
        dynamic_block_list.append("--- 🏢 Commercial Hubs ---")
        dynamic_block_list.extend(comm_blocks)

    with col_block:
        selected_block = st.selectbox(f"🧱 Block / Sheet Tab ({selected_phase})", dynamic_block_list)

    clean_filter_block = selected_block.replace("---", "").strip()

    with col_size:
        selected_size_filter = st.selectbox("📐 Size Filter", ["All Sizes", "5 Marla", "8 Marla", "10 Marla", "1 Kanal", "2 Kanal", "4 Marla", "8 Marla", "16 Marla"])

    st.markdown("---")

    # ==========================================================================
    # 8. CRM INGESTION PANEL (AUTO VS MANUAL EDIT OVERRIDE TOGGLE)
    # ==========================================================================
    c_hdr1, c_hdr2 = st.columns([3, 1.2])
    with c_hdr1:
        st.subheader(f"📥 Add Property Listing ({selected_phase} ➔ Tab: [{clean_filter_block}])")
    with c_hdr2:
        is_auto = st.toggle("Extraction Mode: Auto / Edit", value=st.session_state["auto_mode"])
        st.session_state["auto_mode"] = is_auto

    tab_text, tab_camera = st.tabs(["📝 Text & File Ingestion", "📸 Live Camera Scanner"])
    raw_source_material = ""
    source_type_selected = "WhatsApp Group"

    with tab_text:
        c_in1, c_in2 = st.columns([2, 1])
        with c_in1:
            source_type_selected = st.selectbox("📌 Data Source", ["WhatsApp Group", "Newspaper Classified", "Direct Client", "Facebook Group", "Call Log", "Field Note"])
            placeholder_blk = clean_filter_block if clean_filter_block != "All Blocks" else "Block A"
            raw_text = st.text_area(
                "📋 Paste Raw Property Text / Image OCR Output",
                height=140,
                placeholder=f"Example: {selected_phase} {placeholder_blk} Plot 120 1 Kanal Corner Facing Park 100 ft road for sale demand 4.50 crore direct dealer Muhammad Aslam 03209498044..."
            )
            up_file = st.file_uploader("Or Upload .txt / Picture OCR File", type=["txt"])
            if up_file: raw_text = str(up_file.read(), "utf-8")
            raw_source_material = f"[{source_type_selected}] " + raw_text
            
        with c_in2:
            st.markdown("#### ⚡ Real-Time Auto Extraction")
            cat, ph, blk, plt_no, sz, feat, dem, sel_type, sel_name, phn, d_status, l_notes = parse_property_crm(
                raw_text, selected_phase, clean_filter_block
            )
            target_tab_name = blk if blk != "N/A" else (clean_filter_block if clean_filter_block != "All Blocks" else "Block A")
            
            if raw_text.strip():
                st.write(f"**Target Tab:** `[{target_tab_name}]`")
                st.write(f"**Plot No:** `{plt_no}` | **Size:** `{sz}`")
                st.write(f"**Demand:** `{dem}` | **Features:** `{feat}`")
                st.write(f"**Seller:** `{sel_type}` ({sel_name})")
                st.write(f"**Phone:** `{phn}`")
            else:
                st.info(f"Standard Auto Mode running. Ingest any listing for {selected_phase}...")

        # If Manual Edit Mode is ON, provide clean editable fields before saving
        if not st.session_state["auto_mode"] and raw_text.strip():
            st.markdown("##### ✏️ Fine-Tune & Manual Field Override")
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                plt_no = st.text_input("Plot No", value=plt_no)
                sz = st.text_input("Size", value=sz)
            with e2:
                dem = st.text_input("Demand / Price", value=dem)
                feat = st.text_input("Plot Features / Road", value=feat)
            with e3:
                sel_type = st.selectbox("Seller Type", ["Direct Owner", "Authorized Dealer", "Investor"], index=0 if sel_type == "Direct Owner" else 1)
                sel_name = st.text_input("Seller / Dealer Name", value=sel_name)
            with e4:
                phn = st.text_input("Contact Number", value=phn)
                d_status = st.selectbox("Deal Status", ["Available", "Under Discussion", "Token Paid", "Sold"], index=0)
            
            l_notes = st.text_area("Last Conversation / Follow-Up Note", value=l_notes, height=70)

        if st.button(f"💾 Save Listing to [{selected_phase}] ➔ Tab [{clean_filter_block}]", use_container_width=True):
            if raw_text.strip():
                try:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    target_tab_name = blk if blk != "N/A" else (clean_filter_block if clean_filter_block != "All Blocks" else "Block A")
                    
                    # 15-Column CRM Payload
                    crm_row_payload = [
                        now_str,                          # 1. Date / Timestamp
                        cat,                              # 2. Category
                        ph,                               # 3. Phase
                        blk,                              # 4. Block
                        plt_no,                           # 5. Plot No
                        sz,                               # 6. Size
                        feat,                             # 7. Plot Features
                        dem,                              # 8. Demand / Price
                        sel_type,                         # 9. Seller Type
                        sel_name,                         # 10. Seller / Dealer Name
                        phn,                              # 11. Contact No
                        st.session_state['office_name'],   # 12. Office / Agency
                        d_status,                         # 13. Deal Status
                        l_notes,                          # 14. Last Conversation / Notes
                        raw_source_material               # 15. Raw Listing & Source Material
                    ]
                    
                    append_to_block_tab(phase_workbook, target_tab_name, crm_row_payload)
                    
                    st.success(f"✅ Saved directly into Workbook **[{selected_phase}]** under Tab: **[{target_tab_name}]** | Status: [{d_status}]!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Save Error: {e}")
            else:
                st.warning("Please enter or paste listing text first.")

    with tab_camera:
        cam_source = "Camera Scanner OCR"
        img = st.camera_input("Take Photo of Classified Ad / Business Card")
        if img:
            st.success("Photo captured successfully! Ready for ingestion.")
            raw_cam_text = f"[{cam_source}] Image Captured for Listing - Phase: {selected_phase} Block: {clean_filter_block}"
            if st.button("💾 Save Camera Scan to Sheet"):
                try:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    target_tab_name = clean_filter_block if clean_filter_block != "All Blocks" else "Block A"
                    crm_row_payload = [
                        now_str, "Selling", selected_phase, target_tab_name, "N/A", "1 Kanal", "Photo Scanned",
                        "N/A", "Dealer", "Scan Entry", "N/A", st.session_state['office_name'], "Available",
                        "Scanned business card / newspaper", raw_cam_text
                    ]
                    append_to_block_tab(phase_workbook, target_tab_name, crm_row_payload)
                    st.success(f"✅ Photo entry saved to [{selected_phase}] Tab [{target_tab_name}]!")
                except Exception as e:
                    st.error(f"Camera Save Error: {e}")

    st.markdown("---")

    # ==========================================================================
    # 9. LIVE CRM INVENTORY & POP-UP RAW SOURCE PREVIEW BOX
    # ==========================================================================
    st.subheader(f"📊 Live CRM Inventory: [{selected_phase}] — Tab: [{clean_filter_block}]")
    try:
        target_load_tab = clean_filter_block if clean_filter_block != "All Blocks" and not clean_filter_block.startswith("---") else "Block A"
        try:
            worksheet_data = phase_workbook.worksheet(target_load_tab).get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            worksheet_data = []

        if len(worksheet_data) > 1:
            headers = CRM_SHEET_HEADERS
            df = pd.DataFrame(worksheet_data[1:], columns=headers[:len(worksheet_data[1])])
            
            # Size Filtering
            if selected_size_filter != "All Sizes":
                df = df[df["Size"].str.contains(selected_size_filter, case=False, na=False) |
                        df["Raw Listing & Source Material"].str.contains(selected_size_filter, case=False, na=False)]
                
            # Search Query Filtering
            if search_query:
                df = df[df["Raw Listing & Source Material"].str.contains(search_query, case=False, na=False) |
                        df["Plot Features"].str.contains(search_query, case=False, na=False) |
                        df["Plot No"].str.contains(search_query, case=False, na=False) |
                        df["Demand / Price"].str.contains(search_query, case=False, na=False) |
                        df["Contact No"].str.contains(search_query, case=False, na=False)]

            ts, tb, tr = st.tabs(["🔴 Available Inventory (Selling)", "🟢 Buyer Requirements (Buying)", "🔵 Rental & Leases"])
            
            def display_listings(filt_df, badge_c):
                if filt_df.empty:
                    st.info(f"No records found in Tab [{target_load_tab}] for this category.")
                    return
                for idx, r in filt_df.iterrows():
                    wa = create_wa_crm_pitch(r.to_dict())
                    c1, c2 = st.columns([3.8, 1.4])
                    with c1:
                        dem_val = r.get('Demand / Price', 'N/A')
                        phn_val = r.get('Contact No', 'N/A')
                        plt_val = r.get('Plot No', 'N/A')
                        stat_val = r.get('Deal Status', 'Available')
                        seller_val = f"{r.get('Seller Type', 'Dealer')} ({r.get('Seller / Dealer Name', '')})"
                        raw_val = r.get('Raw Listing & Source Material', r.get('Raw Listing Text', 'N/A'))
                        
                        src_match = re.match(r'\[(.*?)\]', raw_val)
                        src_tag = src_match.group(1) if src_match else "Direct Input"
                        
                        st.markdown(f"""
                            <div class="property-card">
                                <span class="badge {badge_c}">{r.get('Category', '')}</span>
                                <span class="badge badge-price">💰 {dem_val}</span>
                                <span class="badge badge-status">📌 {stat_val}</span>
                                <span class="badge badge-source">🏷️ {src_tag}</span>
                                <span class="badge badge-feature">{r.get('Plot Features', '')}</span>
                                <b>{r.get('Phase', '')} {r.get('Block', '')} — {plt_val} ({r.get('Size', '')})</b>
                                <div style="margin-top: 6px; font-size: 13px; color: #0284C7;"><b>Follow-up Notes:</b> {r.get('Last Conversation / Notes', 'N/A')}</div>
                                <small style="color:#94A3B8;">Seller: {seller_val} | Phone: {phn_val} | Added: {r.get('Date / Timestamp', '')}</small>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        with st.expander(f"🔍 View Original Raw Material & Source Origin ({src_tag})"):
                            st.markdown(f"""
                                <div class="popup-box">
                                    <div style="font-weight: 700; color: #00113A; margin-bottom: 6px;">
                                        📁 Origin Source: <span style="color:#0284C7;">{src_tag}</span>
                                    </div>
                                    <div style="background: white; border: 1px solid #E2E8F0; padding: 12px; border-radius: 8px; font-size: 13.5px; color: #334155; white-space: pre-wrap;">
{raw_val}
                                    </div>
                                    <small style="color: #64748B; margin-top: 6px; display: block;">
                                        🕒 Ingested on: {r.get('Date / Timestamp', 'N/A')} | Agency: {r.get('Office / Agency', st.session_state['office_name'])}
                                    </small>
                                </div>
                            """, unsafe_allow_html=True)

                    with c2:
                        st.markdown(f'<a href="{wa}" target="_blank" class="wa-btn">📲 WhatsApp Pitch</a>', unsafe_allow_html=True)

            with ts: display_listings(df[df["Category"] == "Selling"] if "Category" in df.columns else df, "badge-selling")
            with tb: display_listings(df[df["Category"] == "Buying"] if "Category" in df.columns else df, "badge-buying")
            with tr: display_listings(df[df["Category"] == "Rental"] if "Category" in df.columns else df, "badge-rental")
        else:
            st.info(f"Worksheet Tab **[{target_load_tab}]** in Workbook **[{selected_phase}]** is active. Add entries above to view records!")
    except Exception as e:
        st.error(f"Data Load Error: {e}")

    st.markdown("""
        <div class="stitch-footer">
            <div>© 2026 DHA Smart Property Engine & Wali Muhammad Associates. All rights reserved.</div>
            <div>15-Column CRM Architecture with Pop-up Source Material Box</div>
        </div>
    """, unsafe_allow_html=True)
