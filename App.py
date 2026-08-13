import streamlit as st
import gspread
import re
import pandas as pd

# 1. Page Configuration (Stitch UI Theme)
st.set_page_config(
    page_title="DHA Property Hub | Stitch UI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Advanced Stitch Styling CSS
st.markdown("""
    <style>
    /* Global Styling */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .header-title {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        color: #F8FAFC;
    }
    .header-subtitle {
        color: #94A3B8;
        font-size: 14px;
        margin-top: 5px;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Auto Detection Preview Cards */
    .preview-box {
        background: #F1F5F9;
        border-radius: 12px;
        padding: 18px;
        border-left: 4px solid #0EA5E9;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 5px;
    }
    .badge-phase { background-color: #E0F2FE; color: #0369A1; }
    .badge-block { background-color: #FEF3C7; color: #B45309; }
    .badge-cat { background-color: #DCFCE7; color: #15803D; }
    
    /* Buttons */
    .stButton>button {
        background: #059669 !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2) !important;
    }
    .stButton>button:hover {
        background: #047857 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Google Sheet Connection
@st.cache_resource
def get_google_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url).sheet1

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"Sheet Connection Failed: {e}")
    st.stop()

# 4. Smart Regex Parser Engine
def parse_property_text(text):
    text_upper = text.upper()
    
    # Category
    category = "General"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED"]):
        category = "Buying"
    elif any(w in text_upper for w in ["FOR SALE", "AVAILABLE", "SELLING", "DIRECT", "DEMAND"]):
        category = "Selling"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"
        
    # Phase Detection
    phase = "N/A"
    phase_pattern = re.search(r'(PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
    if phase_pattern:
        phase = f"Phase {phase_pattern.group(2)}"

    # Block Detection
    block = "N/A"
    b_match = re.search(r'(?:BLOCK|BLK)\s*[:.-]?\s*([A-Z]{1,2})', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(BLOCK|BLK|CCA)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"
    
    # Size
    size = "N/A"
    size_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    if size_match:
        size = f"{size_match.group(1)} {size_match.group(2)}"
    
    return category, phase, block, size

# 5. Header Banner Layout
st.markdown("""
    <div class="header-banner">
        <h1 class="header-title">🏢 DHA Property Hub</h1>
        <div class="header-subtitle">Stitch-Style Smart Property Categorization & Management System</div>
    </div>
""", unsafe_allow_html=True)

# 6. Sidebar Navigation (Stitch Style)
st.sidebar.image("https://img.icons8.com/color/96/real-estate.png", width=60)
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Select View", ["➕ New Property Entry", "📊 Inventory Database", "⚙️ System Status"])

if menu == "➕ New Property Entry":
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Property Input Portal")
        source = st.selectbox("📌 Data Source", ["WhatsApp Group", "Newspaper Advert", "Direct Client", "Facebook", "Other"])
        raw_text = st.text_area("📋 Paste Raw Listing Text", height=220, placeholder="Example: DHA Phase 6 Block M 1 Kanal plot for urgent sale demand 4.5 crore...")
        
    with col2:
        st.subheader("⚡ Auto Extraction Preview")
        if raw_text.strip():
            cat, phase, block, size = parse_property_text(raw_text)
            
            st.markdown(f"""
                <div class="preview-box">
                    <p><b>Auto-Detected Details:</b></p>
                    <p><span class="badge badge-cat">{cat}</span></p>
                    <p><span class="badge badge-phase">{phase}</span></p>
                    <p><span class="badge badge-block">{block}</span></p>
                    <p><b>Size:</b> {size}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Paste any listing on the left to see instant auto-extraction in Stitch design!")

    st.markdown("---")
    if st.button("💾 Save Entry to Google Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, phase, block, size = parse_property_text(raw_text)
                sheet.append_row([source, cat, phase, block, size, raw_text])
                st.success(f"✅ Record Successfully Saved: {phase} | {block} | {cat}")
                st.balloons()
            except Exception as e:
                st.error(f"Error saving to Sheet: {e}")
        else:
            st.warning("Please paste raw property text first!")

elif menu == "📊 Inventory Database":
    st.subheader("🔍 Smart Inventory Search & Filtering")
    
    if st.button("🔄 Refresh Live Data"):
        st.rerun()
        
    try:
        data = sheet.get_all_values()
        if len(data) > 1:
            cols = ["Source", "Category", "Phase", "Block", "Size", "Raw Listing Text"]
            df = pd.DataFrame(data[1:], columns=cols[:len(data[1])])
            
            # Filters
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                selected_phase = st.multiselect("Filter Phase", options=df["Phase"].unique() if "Phase" in df.columns else [])
            with f_col2:
                selected_cat = st.multiselect("Filter Category", options=df["Category"].unique() if "Category" in df.columns else [])
            with f_col3:
                search_term = st.text_input("Search Keyword / Block")
                
            filtered = df.copy()
            if selected_phase and "Phase" in filtered.columns:
                filtered = filtered[filtered["Phase"].isin(selected_phase)]
            if selected_cat and "Category" in filtered.columns:
                filtered = filtered[filtered["Category"].isin(selected_cat)]
            if search_term:
                filtered = filtered[filtered["Raw Listing Text"].str.contains(search_term, case=False, na=False)]
                
            st.dataframe(filtered, use_container_width=True)
        else:
            st.info("No records found in sheet yet...")
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")

elif menu == "⚙️ System Status":
    st.subheader("⚙️ System Status & API Health")
    st.success("🟢 Google Sheet Connection: ACTIVE")
    st.success("🟢 Streamlit Secrets: LOADED")
    st.info(" Connected Sheet: Dha_Master_data_app")
