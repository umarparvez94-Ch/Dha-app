import streamlit as st
import gspread
import re
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime
import io

# ---------------------------------------------------------
# 1. Page Configuration (Stitch UI Theme)
# ---------------------------------------------------------
st.set_page_config(
    page_title="DHA Property Hub | Stitch UI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Local data storage configuration
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOCAL_CSV_PATH = os.path.join(LOCAL_DATA_DIR, "properties.csv")
SECRETS_DIR = os.path.join(os.path.dirname(__file__), ".streamlit")
SECRETS_PATH = os.path.join(SECRETS_DIR, "secrets.toml")

os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
os.makedirs(SECRETS_DIR, exist_ok=True)

CSV_COLUMNS = [
    "Timestamp", "Source", "Category", "Property Type", 
    "Phase", "Block", "Size", "Price", "Phone", "Tags", "Raw Listing Text"
]

# ---------------------------------------------------------
# 2. Advanced Stitch Styling CSS
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Global Styling */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Header Banner */
    .header-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 24px 30px;
        border-radius: 16px;
        color: white;
        margin-bottom: 22px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .header-title {
        font-size: 28px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-subtitle {
        color: #94A3B8;
        font-size: 14px;
        margin-top: 6px;
        font-weight: 400;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        padding: 16px 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        transition: transform 0.2s ease;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Auto Detection Preview Box */
    .preview-box {
        background: white;
        border-radius: 14px;
        padding: 20px;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #0EA5E9;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
    }
    
    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 3px 4px 3px 0;
    }
    .badge-cat-buying { background-color: #FEF3C7; color: #B45309; }
    .badge-cat-selling { background-color: #DCFCE7; color: #15803D; }
    .badge-cat-rental { background-color: #F3E8FF; color: #7E22CE; }
    .badge-phase { background-color: #E0F2FE; color: #0369A1; }
    .badge-block { background-color: #EDE9FE; color: #6D28D9; }
    .badge-type { background-color: #FEE2E2; color: #B91C1C; }
    .badge-size { background-color: #F1F5F9; color: #334155; }
    .badge-price { background-color: #ECFDF5; color: #047857; font-weight: 700; }
    .badge-phone { background-color: #E0F2FE; color: #0284C7; }
    .badge-tag { background-color: #F8FAFC; color: #475569; border: 1px solid #CBD5E1; }
    
    /* WhatsApp Button Style */
    .wa-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #25D366;
        color: white !important;
        padding: 10px 18px;
        border-radius: 10px;
        font-weight: 600;
        text-decoration: none;
        margin-top: 10px;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
        transition: all 0.2s ease;
    }
    .wa-btn:hover {
        background-color: #1EBE5D;
        text-decoration: none;
        transform: translateY(-1px);
    }
    
    /* Primary action buttons */
    .stButton>button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. Google Sheet Connection & Local Storage
# ---------------------------------------------------------
@st.cache_resource
def get_google_sheet():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets not configured (missing 'gcp_service_account')"
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
        sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
        return gc.open_by_url(sheet_url).sheet1, None
    except Exception as e:
        return None, str(e)

sheet, sheet_err = get_google_sheet()

def load_local_data():
    if os.path.exists(LOCAL_CSV_PATH):
        try:
            return pd.read_csv(LOCAL_CSV_PATH)
        except Exception:
            return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.DataFrame(columns=CSV_COLUMNS)

def save_local_data(df):
    df.to_csv(LOCAL_CSV_PATH, index=False)

def save_property_entry(source, cat, p_type, phase, block, size, price, phone, tags_str, raw_text):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = {
        "Timestamp": now_str,
        "Source": source,
        "Category": cat,
        "Property Type": p_type,
        "Phase": phase,
        "Block": block,
        "Size": size,
        "Price": price,
        "Phone": phone,
        "Tags": tags_str,
        "Raw Listing Text": raw_text
    }
    
    # 1. Save to Local CSV
    df = load_local_data()
    df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)
    save_local_data(df)
    
    # 2. Save to Google Sheets if connected
    sheet_synced = False
    if sheet is not None:
        try:
            sheet.append_row([
                now_str, source, cat, p_type, phase, block, size, price, phone, tags_str, raw_text
            ])
            sheet_synced = True
        except Exception as e:
            sheet_synced = False
            
    return True, sheet_synced

# ---------------------------------------------------------
# 4. Advanced Smart Regex Parser Engine
# ---------------------------------------------------------
def parse_property_text(text):
    text_clean = text.strip()
    text_upper = text_clean.upper()
    
    # --- A. Category ---
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED", "DEMANDING CLIENT", "LOOKING FOR"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT", "OFFICE RENT", "HOUSE RENT", "SHOP RENT"]):
        category = "Rental"
    elif any(w in text_upper for w in ["FOR SALE", "AVAILABLE", "SELLING", "DIRECT", "OFFER", "DEMAND"]):
        category = "Selling"
        
    # --- B. Property Type ---
    prop_type = "Plot"
    if any(w in text_upper for w in ["COMMERCIAL", "SHOP", "PLAZA", "OFFICE", "HALL", "BUILDING", "CCA"]):
        prop_type = "Commercial"
    elif any(w in text_upper for w in ["HOUSE", "VILLA", "BUNGALOW", "PORTION", "STOREY", "BEDROOM", "BATH", "BRAND NEW HOUSE"]):
        prop_type = "House"
    elif any(w in text_upper for w in ["APARTMENT", "FLAT", "PENTHOUSE", "STUDIO"]):
        prop_type = "Apartment"
    elif any(w in text_upper for w in ["FILE", "AFFIDAVIT", "ALLOCATION", "INTIQAL", "BALLOT", "OPEN FILE"]):
        prop_type = "File / Affidavit"
    elif any(w in text_upper for w in ["PLOT", "RESIDENTIAL PLOT"]):
        prop_type = "Plot"

    # --- C. Phase Detection ---
    phase = "N/A"
    # Matches "Phase 5", "Phase VI", "Ph 9 Prism", "Phase 9 Town", "DHA Rahbar", "DHA Gujranwala", etc.
    if "PRISM" in text_upper:
        phase = "Phase 9 Prism"
    elif "9 TOWN" in text_upper or "PHASE 9 TOWN" in text_upper:
        phase = "Phase 9 Town"
    elif "RAHBAR" in text_upper:
        phase = "DHA Rahbar"
    elif "GUJRANWALA" in text_upper:
        phase = "DHA Gujranwala"
    elif "MULTAN" in text_upper:
        phase = "DHA Multan"
    elif "BAHAWALPUR" in text_upper:
        phase = "DHA Bahawalpur"
    elif "VALLEY" in text_upper:
        phase = "DHA Valley"
    else:
        phase_pattern = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)\b', text_upper)
        if phase_pattern:
            phase = f"Phase {phase_pattern.group(1)}"

    # --- D. Block Detection ---
    block = "N/A"
    b_match = re.search(r'(?:BLOCK|BLK|SECTOR|SEC)[\s:.-]*([A-Z]{1,2}(?:\d)?)\b', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    elif "CCA-1" in text_upper or "CCA 1" in text_upper:
        block = "CCA 1"
    elif "CCA-2" in text_upper or "CCA 2" in text_upper:
        block = "CCA 2"
    elif "CCA" in text_upper:
        block = "CCA"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(?:BLOCK|BLK)\b', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    # --- E. Size Detection ---
    size = "N/A"
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(MARLA|KANAL|SQFT|SQ FT|SQFT\.|SQ YARD|YARD|ACRE)', text_upper)
    if size_match:
        val = size_match.group(1)
        unit = size_match.group(2).replace("SQ FT", "Sqft").title()
        size = f"{val} {unit}"

    # --- F. Price / Demand / Budget Detection ---
    price = "N/A"
    # Matches: Demand 4.5 Crore, 4.5 Cr, 85 Lacs, 350 Lac, 50k, Demand: 3.25 Cr, etc.
    price_match = re.search(r'(?:DEMAND|BUDGET|PRICE|ASKING|RENT|DEMANDING|COST)?[\s:.-]*(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*(CRORE|CR|CRORES|LACS?|LAKH|LACS|COROR|MILLION|K|THOUSAND)\b', text_upper)
    if price_match:
        p_val = price_match.group(1)
        p_unit = price_match.group(2)
        if p_unit in ["CRORE", "CR", "CRORES", "COROR"]:
            price = f"{p_val} Crore"
        elif p_unit in ["LAC", "LACS", "LAKH"]:
            price = f"{p_val} Lacs"
        elif p_unit in ["K", "THOUSAND"]:
            price = f"{p_val}k"
        elif p_unit == "MILLION":
            price = f"{p_val} Million"
        else:
            price = f"{p_val} {p_unit.title()}"
    else:
        # Check for numeric pattern like "Demand 450" (assuming lacs)
        demand_num = re.search(r'(?:DEMAND|BUDGET)[\s:.-]*(\d+(?:\.\d+)?)\b', text_upper)
        if demand_num:
            price = f"{demand_num.group(1)} (Numeric)"

    # --- G. Phone Number Detection ---
    phone = "N/A"
    phone_clean = ""
    # Matches Pakistani mobile numbers: 03001234567, 0300-1234567, +923001234567, 0300 1234567
    phone_match = re.search(r'(?:\+?92|0092|0)?[\s-]*(3\d{2})[\s-]*(\d{7})\b', text)
    if phone_match:
        code = phone_match.group(1)
        num = phone_match.group(2)
        phone = f"0{code}-{num}"
        phone_clean = f"92{code}{num}"

    # --- H. Smart Tags / Features Extraction ---
    tags = []
    if "CORNER" in text_upper:
        tags.append("Corner")
    if "PARK FACING" in text_upper or "PARK FACE" in text_upper or "FACING PARK" in text_upper:
        tags.append("Park Facing")
    if any(w in text_upper for w in ["MAIN BOULEVARD", "MAIN BLVD", "MB", "150 FT ROAD", "100 FT ROAD", "80 FT ROAD", "60 FT ROAD"]):
        tags.append("Main Boulevard / Wide Road")
    if "POSSESSION" in text_upper and "NON" not in text_upper:
        tags.append("Possession")
    elif "NON POSSESSION" in text_upper or "NON-POSSESSION" in text_upper:
        tags.append("Non-Possession")
    if "URGENT" in text_upper or "URGENT SALE" in text_upper or "DISTRESS" in text_upper:
        tags.append("Urgent Deal")
    if "DIRECT" in text_upper or "DIRECT OWNER" in text_upper or "DIRECT CLIENT" in text_upper:
        tags.append("Direct Deal")
    if "PAIR" in text_upper or "PAIR PLOT" in text_upper:
        tags.append("Pair Plots")
    if "FACING COMMERCIAL" in text_upper or "COMMERCIAL FACING" in text_upper:
        tags.append("Facing Commercial")
    if "HOT LOCATION" in text_upper or "PRIME LOCATION" in text_upper:
        tags.append("Prime Location")

    return category, prop_type, phase, block, size, price, phone, phone_clean, tags

# ---------------------------------------------------------
# 5. Header Banner Layout & Statistics
# ---------------------------------------------------------
all_properties_df = load_local_data()

st.markdown("""
    <div class="header-banner">
        <div class="header-title">🏢 DHA Property Hub <span style="font-size: 14px; background: #0284C7; padding: 4px 10px; border-radius: 20px; font-weight: 600;">v2.0 Pro</span></div>
        <div class="header-subtitle">AI-Powered Real Estate Auto-Extraction, WhatsApp CRM & Inventory Management</div>
    </div>
""", unsafe_allow_html=True)

# Top Fast Stats Bar
c1, c2, c3, c4, c5 = st.columns(5)
total_count = len(all_properties_df)
selling_count = len(all_properties_df[all_properties_df["Category"] == "Selling"]) if total_count > 0 and "Category" in all_properties_df.columns else 0
buying_count = len(all_properties_df[all_properties_df["Category"] == "Buying"]) if total_count > 0 and "Category" in all_properties_df.columns else 0
rental_count = len(all_properties_df[all_properties_df["Category"] == "Rental"]) if total_count > 0 and "Category" in all_properties_df.columns else 0

with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Total Listings</div><div class="metric-value">{total_count}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">For Sale</div><div class="metric-value" style="color:#15803D;">{selling_count}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Wanted / Buying</div><div class="metric-value" style="color:#B45309;">{buying_count}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Rental</div><div class="metric-value" style="color:#7E22CE;">{rental_count}</div></div>', unsafe_allow_html=True)
with c5:
    status_color = "#15803D" if sheet is not None else "#D97706"
    status_text = "🟢 Cloud Synced" if sheet is not None else "🟡 Local Storage"
    st.markdown(f'<div class="metric-card"><div class="metric-label">Storage Mode</div><div class="metric-value" style="color:{status_color}; font-size: 16px; margin-top: 4px;">{status_text}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. Sidebar Navigation
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/real-estate.png", width=60)
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Select View", ["➕ New Property Entry", "📊 Inventory Database", "⚙️ System Status & Settings"])

# ---------------------------------------------------------
# VIEW 1: ➕ NEW PROPERTY ENTRY
# ---------------------------------------------------------
if menu == "➕ New Property Entry":
    col1, col2 = st.columns([1.1, 1.1])
    
    with col1:
        st.subheader("📝 Property Input Portal")
        
        # Sample buttons for rapid testing
        st.markdown("**⚡ Quick Test Samples:**")
        s_col1, s_col2, s_col3 = st.columns(3)
        sample_text = ""
        if s_col1.button("📋 Sample: Sale Plot", use_container_width=True):
            sample_text = "DHA Phase 6 Block M 1 Kanal plot for urgent sale. Demand 4.5 crore. Prime location, park facing. Contact 0300-1234567"
        if s_col2.button("📋 Sample: Buying House", use_container_width=True):
            sample_text = "Required 10 Marla brand new double storey house in DHA Phase 5 Block C. Budget 4.25 Crore direct client. Call 0321-7654321"
        if s_col3.button("📋 Sample: Commercial Rent", use_container_width=True):
            sample_text = "Available 4 Marla commercial plaza in DHA Phase 8 CCA 1 for rent. Corner building on 80 ft road. Rent 3.5 Lacs. 0333-8889990"
        
        source = st.selectbox("📌 Data Source", ["WhatsApp Group", "Direct Client", "Facebook Group", "Newspaper Advert", "Estate Agent Colleague", "Other"])
        
        initial_val = sample_text if sample_text else ""
        raw_text = st.text_area(
            "📋 Paste Raw Listing Text", 
            value=initial_val, 
            height=200, 
            placeholder="Paste any message from WhatsApp, e.g.:\nDHA Phase 6 Block M 1 Kanal plot for urgent sale demand 4.5 crore corner park facing contact 0300-1234567..."
        )
        
    with col2:
        st.subheader("⚡ Smart Extraction Preview")
        if raw_text.strip():
            cat, p_type, phase, block, size, price, phone, phone_clean, tags = parse_property_text(raw_text)
            
            badge_cat_class = f"badge-cat-{cat.lower()}"
            tags_html = "".join([f'<span class="badge badge-tag">🏷️ {t}</span>' for t in tags]) if tags else '<span style="color:#94A3B8; font-size:12px;">None detected</span>'
            
            st.markdown(f"""
                <div class="preview-box">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span class="badge {badge_cat_class}" style="font-size:14px; padding: 6px 16px;">📂 {cat}</span>
                        <span class="badge badge-type" style="font-size:13px;">🏡 {p_type}</span>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                        <div><small style="color:#64748B;">Phase:</small><br><span class="badge badge-phase">{phase}</span></div>
                        <div><small style="color:#64748B;">Block / Sector:</small><br><span class="badge badge-block">{block}</span></div>
                        <div><small style="color:#64748B;">Property Size:</small><br><span class="badge badge-size">📏 {size}</span></div>
                        <div><small style="color:#64748B;">Demand / Budget:</small><br><span class="badge badge-price">💰 {price}</span></div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <small style="color:#64748B;">Contact Phone:</small><br>
                        <span class="badge badge-phone">📞 {phone}</span>
                    </div>
                    <div style="margin-bottom: 12px;">
                        <small style="color:#64748B;">Auto-Detected Tags & Features:</small><br>
                        {tags_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # WhatsApp Action Button if phone detected
            if phone_clean:
                inquiry_msg = f"Assalam-o-Alaikum! I am inquiring regarding your listing for {size} {p_type} in {phase} {block} (Price: {price}). Is it still available?"
                encoded_msg = urllib.parse.quote(inquiry_msg)
                wa_url = f"https://wa.me/{phone_clean}?text={encoded_msg}"
                
                st.markdown(f"""
                    <div style="margin-top: 12px;">
                        <a href="{wa_url}" target="_blank" class="wa-btn">
                            💬 Open Direct WhatsApp Chat ({phone})
                        </a>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("💡 Paste any property listing on the left (or click one of the quick test buttons) to see instant auto-extraction in Stitch design!")

    st.markdown("---")
    
    # Save Action
    if st.button("💾 Save Property Entry to Inventory", use_container_width=True, type="primary"):
        if raw_text.strip():
            cat, p_type, phase, block, size, price, phone, phone_clean, tags = parse_property_text(raw_text)
            tags_str = ", ".join(tags) if tags else "N/A"
            
            success, sheet_synced = save_property_entry(
                source, cat, p_type, phase, block, size, price, phone, tags_str, raw_text
            )
            
            if success:
                if sheet_synced:
                    st.success(f"✅ Record Successfully Saved to **Local Database** & **Google Sheets**: {phase} | {block} | {cat} | {price}")
                else:
                    st.success(f"✅ Record Saved to **Local Inventory**: {phase} | {block} | {cat} | {price} *(Offline Mode)*")
                st.balloons()
        else:
            st.warning("⚠️ Please paste property listing text before saving!")

# ---------------------------------------------------------
# VIEW 2: 📊 INVENTORY DATABASE
# ---------------------------------------------------------
elif menu == "📊 Inventory Database":
    st.subheader("🔍 Smart Inventory Search & Multi-Filter")
    
    # Reload button
    top_col1, top_col2, top_col3 = st.columns([1, 1, 2])
    with top_col1:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
            
    df = load_local_data()
    
    if len(df) > 0:
        # Multi-Filters Bar
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            phases_list = [p for p in df["Phase"].dropna().unique() if str(p) != "nan"]
            selected_phase = st.multiselect("Filter Phase", options=phases_list)
        with f_col2:
            cats_list = [c for c in df["Category"].dropna().unique() if str(c) != "nan"]
            selected_cat = st.multiselect("Filter Category", options=cats_list)
        with f_col3:
            types_list = [t for t in df["Property Type"].dropna().unique() if str(t) != "nan"] if "Property Type" in df.columns else []
            selected_type = st.multiselect("Filter Property Type", options=types_list)
        with f_col4:
            search_term = st.text_input("🔎 Search Keyword / Block / Price", placeholder="e.g. Block M, 4.5, Corner...")
            
        filtered = df.copy()
        if selected_phase:
            filtered = filtered[filtered["Phase"].isin(selected_phase)]
        if selected_cat:
            filtered = filtered[filtered["Category"].isin(selected_cat)]
        if selected_type and "Property Type" in filtered.columns:
            filtered = filtered[filtered["Property Type"].isin(selected_type)]
        if search_term:
            filtered = filtered[
                filtered["Raw Listing Text"].str.contains(search_term, case=False, na=False) |
                filtered["Block"].str.contains(search_term, case=False, na=False) |
                filtered["Price"].str.contains(search_term, case=False, na=False) |
                filtered["Tags"].str.contains(search_term, case=False, na=False)
            ]
            
        st.markdown(f"**Showing {len(filtered)} of {len(df)} properties**")
        st.dataframe(filtered, use_container_width=True, height=350)
        
        # Action Buttons: Export & Sync
        st.markdown("---")
        exp_col1, exp_col2, exp_col3 = st.columns(3)
        
        with exp_col1:
            csv_data = filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export to CSV",
                data=csv_data,
                file_name=f"dha_properties_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        with exp_col2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                filtered.to_excel(writer, index=False, sheet_name='DHA_Properties')
            st.download_button(
                label="📊 Export to Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"dha_properties_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        with exp_col3:
            if sheet is not None:
                if st.button("☁️ Sync All to Google Sheets", use_container_width=True):
                    try:
                        with st.spinner("Syncing data to Google Sheets..."):
                            for idx, row in df.iterrows():
                                sheet.append_row(row.tolist())
                        st.success("✅ All local properties synced to Google Sheet!")
                    except Exception as e:
                        st.error(f"Sync error: {e}")
            else:
                st.button("☁️ Google Sheets Offline", disabled=True, use_container_width=True)
                
    else:
        st.info("📭 No property entries found in inventory yet. Use the 'New Property Entry' tab to add listings or try test samples!")

# ---------------------------------------------------------
# VIEW 3: ⚙️ SYSTEM STATUS & SETTINGS
# ---------------------------------------------------------
elif menu == "⚙️ System Status & Settings":
    st.subheader("⚙️ System Status & Storage Settings")
    
    status_c1, status_c2 = st.columns(2)
    
    with status_c1:
        st.markdown("### 📊 Database & Cloud Status")
        if sheet is not None:
            st.success("🟢 **Google Sheets Connection**: ACTIVE & CONNECTED")
            st.info("📋 **Target Spreadsheet**: `Dha_Master_data_app`")
        else:
            st.warning("🟡 **Google Sheets Connection**: OFFLINE / NOT CONFIGURED")
            if sheet_err:
                st.caption(f"Reason: {sheet_err}")
                
        st.success(f"🟢 **Local Storage (CSV)**: ACTIVE (`data/properties.csv` - {len(all_properties_df)} records)")
        st.success(f"🟢 **Regex Extraction Engine**: ACTIVE (v2.0 with Price, Phone, Tags)")

    with status_c2:
        st.markdown("### 🔑 Google Sheets Setup Manager")
        st.write("Google Sheets connect karne ke liye apna Google Cloud Service Account JSON yahan upload ya paste karein:")
        
        uploaded_file = st.file_uploader("Upload `service_account.json`", type=["json"])
        json_text = st.text_area("Or Paste Service Account JSON content here:", height=130, placeholder='{"type": "service_account", "project_id": "...", ...}')
        
        if st.button("💾 Save Credentials & Connect", use_container_width=True, type="primary"):
            creds_data = None
            if uploaded_file is not None:
                try:
                    creds_data = json.load(uploaded_file)
                except Exception as e:
                    st.error(f"Invalid JSON file: {e}")
            elif json_text.strip():
                try:
                    creds_data = json.loads(json_text)
                except Exception as e:
                    st.error(f"Invalid JSON text: {e}")
                    
            if creds_data:
                try:
                    secrets_content = f'[gcp_service_account]\n'
                    for k, v in creds_data.items():
                        if isinstance(v, str):
                            v_clean = v.replace('"', '\\"').replace('\n', '\\n')
                            secrets_content += f'{k} = "{v_clean}"\n'
                        else:
                            secrets_content += f'{k} = {json.dumps(v)}\n'
                            
                    with open(SECRETS_PATH, "w", encoding="utf-8") as f:
                        f.write(secrets_content)
                        
                    st.success("✅ Credentials saved to `.streamlit/secrets.toml`! Please click Reload below.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save secrets: {e}")
            else:
                st.warning("Please upload a file or paste JSON credentials first.")

    st.markdown("---")
    st.markdown("""
        ### 📖 Quick Setup Guide (Google Sheets)
        1. [Google Cloud Console](https://console.cloud.google.com/) par Service Account banayein aur **Google Sheets API** + **Google Drive API** enable karein.
        2. Service Account ki JSON Key download karein aur upar upload karein.
        3. Apni Google Sheet ko Service Account ke client email ke saath **Editor** access dekar share karein.
    """)
