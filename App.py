import streamlit as st
import gspread
import re
import pandas as pd

st.set_page_config(page_title="DHA AI Property Hub", layout="wide", page_icon="🏠")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { background-color: #059669; color: white; border-radius: 8px; height: 3em; font-weight: bold; }
    .stButton>button:hover { background-color: #047857; color: white; }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Connection
@st.cache_resource
def get_google_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url).sheet1

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"Sheet Connection Error: {e}")
    st.stop()

# Helper Rule-based AI Parser
def parse_property_text(text):
    text_upper = text.upper()
    
    # 1. Determine Category
    category = "General / Uncategorized"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED", "REQUIRE"]):
        category = "Buying / Requirement"
    elif any(w in text_upper for w in ["FOR SALE", "AVAILABLE", "SELLING", "DIRECT", "URGENT SALE", "OFFER"]):
        category = "Selling / Inventory"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"
        
    # 2. Extract Phase
    phase_match = re.search(r'(PHASE|PH|P)[\s:-]*(\d+|[A-Z]+)', text_upper)
    phase = phase_match.group(0) if phase_match else "N/A"
    
    # 3. Extract Size
    size_match = re.search(r'(\d+)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    size = size_match.group(0) if size_match else "N/A"
    
    return category, phase, size

# Application Header
st.title("🏠 DHA AI Property Management Portal")
st.caption("انٹیلیجنٹ رئیل اسٹیٹ ڈیش بورڈ - واٹس ایپ اور اخبار کا ڈیٹا خودکار الگ اور محفوظ کریں")

# Navigation Tabs
tab1, tab2 = st.tabs(["📝 Smart Data Entry", "🔍 View & Search Inventory"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        source = st.selectbox("📌 Data Source", ["WhatsApp Group", "Newspaper / Classified", "Direct Client", "Facebook", "Other"])
        raw_text = st.text_area("📋 Paste Raw Property Text (WhatsApp / Newspaper / Post)", height=220, placeholder="یہاں اپنا خام ٹیکسٹ پیسٹ کریں، مثلاً: DHA Phase 6 Block M 1 Kanal plot for urgent sale demand 4.5 crore...")
        
    with col2:
        st.markdown("### 🤖 Live AI Parsing Preview")
        if raw_text.strip():
            auto_cat, auto_phase, auto_size = parse_property_text(raw_text)
            st.info(f"**Detected Category:** {auto_cat}")
            st.success(f"**Extracted Phase:** {auto_phase}")
            st.warning(f"**Extracted Size:** {auto_size}")
        else:
            st.write("ٹیکسٹ پیسٹ کرتے ہی AI اس میں سے فیز اور معلومات الگ دکھائے گا...")

    st.markdown("---")
    if st.button("💾 Save to Google Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, phase, size = parse_property_text(raw_text)
                # Appending Structured Row: [Source, Category, Phase, Size, Raw Text]
                sheet.append_row([source, cat, phase, size, raw_text])
                st.success("✅ ڈیٹا کامیابی سے تجزیہ (Parse) ہو کر گوگل شیٹ میں محفوظ ہو گیا ہے!")
                st.balloons()
            except Exception as e:
                st.error(f"Error saving data: {e}")
        else:
            st.warning("براہِ کرم پہلے کچھ ٹیکسٹ پیسٹ کریں۔")

with tab2:
    st.subheader("📊 Stored Property Records")
    if st.button("🔄 Refresh Data"):
        st.rerun()
        
    try:
        data = sheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=["Source", "Category", "Phase", "Size", "Raw Text"])
            
            # Quick Filters
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                cat_filter = st.multiselect("Filter by Category", options=df["Category"].unique())
            with col_f2:
                search_query = st.text_input("Search Keyword (Phase, Block, Price, etc.)")
                
            filtered_df = df.copy()
            if cat_filter:
                filtered_df = filtered_df[filtered_df["Category"].isin(cat_filter)]
            if search_query:
                filtered_df = filtered_df[filtered_df["Raw Text"].str.contains(search_query, case=False, na=False)]
                
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.write("شیٹ میں فی الحال صرف بنیادی ریکارڈز موجود ہیں...")
    except Exception as e:
        st.error(f"Could not load records: {e}")
