import streamlit as st
import gspread
import re
import urllib.parse
import pandas as pd
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="DHA Smart Property Engine",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Custom Stitch CSS
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    .header-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 22px 26px; border-radius: 16px; color: white; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .header-title { font-size: 26px; font-weight: 800; margin: 0; color: #F8FAFC; }
    .office-badge {
        background-color: #10B981; color: white; padding: 5px 14px;
        border-radius: 20px; font-size: 13px; font-weight: 600; float: right;
    }
    .property-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 12px;
        padding: 16px; margin-bottom: 12px;
    }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; margin-right: 6px; }
    .badge-selling { background-color: #FEE2E2; color: #DC2626; }
    .badge-buying { background-color: #DCFCE7; color: #16A34A; }
    .badge-rental { background-color: #E0F2FE; color: #0284C7; }
    .badge-feature { background-color: #FEF3C7; color: #D97706; }
    .badge-type { background-color: #EDE9FE; color: #6D28D9; }
    .stButton>button {
        background: #059669 !important; color: white !important;
        border-radius: 8px !important; font-weight: 600 !important; border: none !important;
    }
    .wa-btn {
        display: inline-block; background-color: #25D366; color: white !important;
        padding: 8px 14px; border-radius: 8px; font-weight: 700; text-decoration: none;
        font-size: 13px; text-align: center; width: 100%; box-sizing: border-box;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Google Sheets Connection
@st.cache_resource
def get_google_workbook():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    return gc.open_by_url(sheet_url)

try:
    workbook = get_google_workbook()
except Exception as e:
    st.error(f"⚠️ Google Sheet Connection Error: {e}")
    st.stop()

def append_to_phase_sheet(workbook, phase_tab_name, row_data):
    clean_tab_title = str(phase_tab_name).strip() if phase_tab_name else "DHA Phase 1"
    try:
        worksheet = workbook.worksheet(clean_tab_title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=clean_tab_title, rows=300, cols=10)
        worksheet.append_row(["Timestamp", "Source", "Category", "Phase", "Block", "Property Type", "Size", "Features", "Raw Listing Text"])
    worksheet.append_row(row_data)

if "office_name" not in st.session_state:
    st.session_state["office_name"] = "Wali Muhammad Associates"

# 4. Standard DHA Phase to Block Mapping Directory (with Segregated Residential & Commercial)
DHA_PHASE_BLOCKS = {
    "DHA Phase 1": [
        "All Blocks",
        "--- 🏡 Residential Sectors ---",
        "Block A (Residential)",
        "Block B (Residential)",
        "Block C (Residential)",
        "Block D (Residential)",
        "Block E (Residential)",
        "Block J (Residential)",
        "Block K (Residential)",
        "Block L (Residential)",
        "Block M (Residential)",
        "Block N (Residential)",
        "Block P (Residential)",
        "--- 🏢 Commercial Hubs ---",
        "Block F (Commercial Market)",
        "Block G (Main Commercial)",
        "Block H (Commercial & Stadium)",
        "Block J (Club Commercial)",
        "Block M (Commercial)",
        "Sector Shops (Local Commercial)"
    ],
    "DHA Phase 2": ["All Blocks", "Block Q (Residential)", "Block R (Residential)", "Block S (Residential)", "Block T (Residential)", "Block U (Residential)", "Block V (Residential)", "Phase 2 Commercial CCA"],
    "DHA Phase 3": ["All Blocks", "Block W (Residential)", "Block X (Residential)", "Block Y (Residential)", "Block Z (Residential)", "Y Block Commercial (Main Hub)", "Z Block Commercial"],
    "DHA Phase 4": ["All Blocks", "Block AA (Residential)", "Block BB (Residential)", "Block CC (Residential)", "Block DD (Residential)", "Block EE (Residential)", "Block FF (Residential)", "Block GG (Residential)", "Block JJ (Residential)", "Block KK (Residential)", "Phase 4 CCA Commercial"],
    "DHA Phase 5": ["All Blocks", "Block A (Residential)", "Block B (Residential)", "Block C (Residential)", "Block D (Residential)", "Block E (Residential)", "Block F (Residential)", "Block G (Residential)", "Block H (Residential)", "Block J (Residential)", "Block K (Residential)", "Block L (Residential)", "Block M (Residential)", "Phase 5 CCA 1", "Phase 5 CCA 2"],
    "DHA Phase 6": ["All Blocks", "Block A (Residential)", "Block B (Residential)", "Block C (Residential)", "Block D (Residential)", "Block E (Residential)", "Block F (Residential)", "Block G (Residential)", "Block H (Residential)", "Block J (Residential)", "Block K (Residential)", "Block L (Residential)", "Block M (Residential)", "Block N (Residential)", "Main MB Commercial", "CCA 1 Commercial", "CCA 2 Commercial"],
    "DHA Phase 7": ["All Blocks", "Block P (Residential)", "Block Q (Residential)", "Block R (Residential)", "Block S (Residential)", "Block T (Residential)", "Block U (Residential)", "Block V (Residential)", "Block W (Residential)", "Block X (Residential)", "Block Y (Residential)", "Block Z (Residential)", "Phase 7 CCA Commercial"],
    "DHA Phase 8": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R", "Block S", "Block T", "Block U", "Block V", "Block W", "Block X", "Block Y", "Block Z", "Broadway Commercial", "CCA 1", "CCA 2"],
    "DHA Phase 9 Prism": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Block K", "Block L", "Block M", "Block N", "Block P", "Block Q", "Block R", "Zone 1 Commercial", "Zone 2 Commercial", "Zone 3 Commercial", "Main Oval Commercial"],
    "DHA Phase 9 Town": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Block E", "Commercial CCA"],
    "DHA Phase 10": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Block E", "Main Commercial"],
    "DHA Phase 11 (Rahwali)": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Main Commercial"],
    "DHA Phase 12 (EME)": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Block E", "Block F", "Block G", "Block H", "Block J", "Commercial Market"],
    "DHA Phase 13": ["All Blocks", "Block A", "Block B", "Block C", "Block D", "Block E"]
}

# 5. Smart Extractor
def parse_property_text(text, current_selected_phase, current_selected_block):
    text_upper = text.upper()
    category = "Selling"
    if any(w in text_upper for w in ["REQUIRED", "WANTED", "BUYING", "PURCHASE", "NEED"]):
        category = "Buying"
    elif any(w in text_upper for w in ["RENT", "TO LET", "TENANT"]):
        category = "Rental"

    prop_type = "Residential"
    if any(w in text_upper for w in ["COMMERCIAL", "COMM", "SHOP", "PLAZA", "OFFICE", "CCA", "BOUTIQUE", "RESTAURANT", "BANK"]):
        prop_type = "Commercial"
    elif "COMMERCIAL" in str(current_selected_block).upper():
        prop_type = "Commercial"

    phase = current_selected_phase
    p_match = re.search(r'(?:PHASE|PH|P)[\s:-]*(\d{1,2}|I{1,3}|IV|V|VI|VII|VIII|IX|X)', text_upper)
    if p_match:
        val = p_match.group(1)
        phase = f"DHA Phase {val}"
    if "PRISM" in text_upper:
        phase = "DHA Phase 9 Prism"

    block = current_selected_block if (current_selected_block != "All Blocks" and not current_selected_block.startswith("---")) else "Block A"
    b_match = re.search(r'(?:BLOCK|BLK)\s*[:.-]?\s*([A-Z]{1,2})', text_upper)
    if b_match:
        block = f"Block {b_match.group(1)}"
    else:
        b_fallback = re.search(r'\b([A-Z]{1,2})\s*(BLOCK|BLK|CCA)', text_upper)
        if b_fallback:
            block = f"Block {b_fallback.group(1)}"

    size = "1 Kanal"
    s_match = re.search(r'(\d+\.?\d*)\s*(MARLA|KANAL|SQFT|YARD)', text_upper)
    if s_match:
        size = f"{s_match.group(1)} {s_match.group(2)}"

    features = []
    if "CORNER" in text_upper: features.append("Corner")
    if "PARK" in text_upper or "FACING PARK" in text_upper: features.append("Park Facing")
    if "MAIN" in text_upper or "BOULEVARD" in text_upper or "MB" in text_upper: features.append("Main Boulevard")
    if "EXCESS" in text_upper: features.append("Excess Land")
    road_match = re.search(r'(\d{2,3})\s*(FT|FEET|ROAD)', text_upper)
    if road_match: features.append(f"{road_match.group(0)} Road")
    feature_str = ", ".join(features) if features else "Standard Layout"

    return category, phase, block, prop_type, size, feature_str

def create_wa_link(row_dict):
    msg = f"""🏢 *{st.session_state['office_name']}*
📍 *DHA Property Update*
• *Phase:* {row_dict.get('Phase', 'N/A')}
• *Block:* {row_dict.get('Block', 'N/A')}
• *Type:* {row_dict.get('Property Type', 'Residential')}
• *Size:* {row_dict.get('Size', 'N/A')}
• *Category:* {row_dict.get('Category', 'N/A')}
• *Features:* {row_dict.get('Features', 'Standard')}
📝 *Details:* {row_dict.get('Raw Listing Text', row_dict.get('Raw Listing', ''))}"""
    return f"https://wa.me/?text={urllib.parse.quote(msg)}"

# 6. UI Layout
st.markdown(f"""
    <div class="header-banner">
        <span class="office-badge">📍 {st.session_state['office_name']}</span>
        <h1 class="header-title">🏢 DHA Smart Property Engine</h1>
        <div style="color: #94A3B8; font-size: 13px; margin-top: 4px;">Segregated Residential & Commercial Phase-Wise Inventory Engine</div>
    </div>
""", unsafe_allow_html=True)

with st.expander("⚙️ Settings (Change Agency Name)"):
    new_office = st.text_input("Agency Name", value=st.session_state["office_name"])
    if st.button("Update"):
        st.session_state["office_name"] = new_office
        st.rerun()

st.markdown("### 🔍 Supreme Global Property Search")
search_query = st.text_input("Search anything", placeholder="e.g. DHA Phase 1 Block G Commercial, Block A Corner 1 Kanal, Main Boulevard...", label_visibility="collapsed")

st.markdown("---")

# Cascading Phase & Block Selection Row
col_city, col_phase, col_block = st.columns([1.2, 1.8, 1.8])
with col_city:
    selected_city = st.selectbox("🏙️ City", ["Lahore", "Karachi", "Islamabad", "Gujranwala", "Multan", "Bahawalpur", "Quetta", "Peshawar"])
with col_phase:
    selected_phase = st.selectbox("📍 DHA Phase", list(DHA_PHASE_BLOCKS.keys()), index=0)
with col_block:
    available_blocks = DHA_PHASE_BLOCKS.get(selected_phase, ["All Blocks", "Block A (Residential)"])
    selected_block = st.selectbox(f"🧱 Block List ({selected_phase})", available_blocks)

st.markdown("---")

clean_filter_block = selected_block.replace("---", "").strip()

# 7. Ingestion Panel
st.subheader(f"📥 Add Property Listing ({selected_phase})")
tab_text, tab_camera = st.tabs(["📝 Text & File Entry", "📸 Camera Scanner"])

with tab_text:
    c_in1, c_in2 = st.columns([2, 1])
    with c_in1:
        source = st.selectbox("Source", ["WhatsApp Group", "Newspaper Classified", "Direct Client", "Facebook"])
        placeholder_blk = clean_filter_block if clean_filter_block != "All Blocks" else "Block A"
        raw_text = st.text_area("Paste Listing Text", height=130, placeholder=f"Example: {selected_phase} {placeholder_blk} 1 Kanal plot for sale...")
        up_file = st.file_uploader("Upload .txt file", type=["txt"])
        if up_file: raw_text = str(up_file.read(), "utf-8")
    with c_in2:
        st.markdown("#### ⚡ Auto Extraction Preview")
        if raw_text.strip():
            cat, ph, blk, p_type, sz, feat = parse_property_text(raw_text, selected_phase, clean_filter_block)
            st.write(f"**Target Phase:** `{ph}`")
            st.write(f"**Category:** `{cat}`")
            st.write(f"**Block:** `{blk}`")
            st.write(f"**Property Type:** `{p_type}`")
            st.write(f"**Size:** `{sz}`")
            st.write(f"**Features:** `{feat}`")
        else:
            st.info(f"Select block & enter listing for {selected_phase}...")

    if st.button(f"💾 Save Listing to [{selected_phase}] Sheet", use_container_width=True):
        if raw_text.strip():
            try:
                cat, ph, blk, p_type, sz, feat = parse_property_text(raw_text, selected_phase, clean_filter_block)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                row_payload = [now_str, source, cat, ph, blk, p_type, sz, feat, raw_text]
                append_to_phase_sheet(workbook, ph, row_payload)
                
                st.success(f"✅ Saved into Google Sheet Tab: **[{ph}]** under **[{blk}]** ({p_type})!")
                st.balloons()
            except Exception as e:
                st.error(f"Save Error: {e}")
        else:
            st.warning("Please paste listing text first.")

with tab_camera:
    img = st.camera_input("Scan Ad / Business Card")
    if img: st.success("Photo captured!")

st.markdown("---")

# 8. Live 3-Sheet Inventory Tabs
st.subheader(f"📊 Live Inventory: [{selected_phase}] — [{clean_filter_block}]")
try:
    try:
        data = workbook.worksheet(selected_phase).get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        data = []

    if len(data) > 1:
        headers = ["Timestamp", "Source", "Category", "Phase", "Block", "Property Type", "Size", "Features", "Raw Listing Text"]
        df = pd.DataFrame(data[1:], columns=headers[:len(data[1])])
        
        if clean_filter_block != "All Blocks" and not clean_filter_block.startswith("---"):
            core_block_letter = re.search(r'Block\s*([A-Z0-9]+)', clean_filter_block)
            search_token = core_block_letter.group(0) if core_block_letter else clean_filter_block
            df = df[df["Block"].str.contains(search_token, case=False, na=False) |
                    df["Raw Listing Text"].str.contains(search_token, case=False, na=False)]
            
        if search_query:
            df = df[df["Raw Listing Text"].str.contains(search_query, case=False, na=False) |
                    df["Features"].str.contains(search_query, case=False, na=False) |
                    df["Block"].str.contains(search_query, case=False, na=False)]

        ts, tb, tr = st.tabs(["🔴 Selling", "🟢 Buying", "🔵 Rental"])
        def display_listings(filt_df, badge_c):
            if filt_df.empty:
                st.info(f"No records found for this category.")
                return
            for _, r in filt_df.iterrows():
                wa = create_wa_link(r.to_dict())
                c1, c2 = st.columns([4, 1.2])
                with c1:
                    p_type_val = r.get('Property Type', 'Residential')
                    st.markdown(f"""
                        <div class="property-card">
                            <span class="badge {badge_c}">{r.get('Category', '')}</span>
                            <span class="badge badge-type">{p_type_val}</span>
                            <span class="badge badge-feature">{r.get('Features', '')}</span>
                            <b>{r.get('Phase', '')} {r.get('Block', '')} — {r.get('Size', '')}</b>
                            <p style="margin: 6px 0 0 0; color:#475569; font-size:14px;">{r.get('Raw Listing Text', '')}</p>
                            <small style="color:#94A3B8;">Source: {r.get('Source', '')} | Added: {r.get('Timestamp', '')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<a href="{wa}" target="_blank" class="wa-btn">📲 WhatsApp</a>', unsafe_allow_html=True)

        with ts: display_listings(df[df["Category"] == "Selling"] if "Category" in df.columns else df, "badge-selling")
        with tb: display_listings(df[df["Category"] == "Buying"] if "Category" in df.columns else df, "badge-buying")
        with tr: display_listings(df[df["Category"] == "Rental"] if "Category" in df.columns else df, "badge-rental")
    else:
        st.info(f"Google Sheet tab **[{selected_phase}]** is active. Add entries for {clean_filter_block} above!")
except Exception as e:
    st.error(f"Load Error: {e}")
