import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime
import gspread
from google.oauth2 import service_account
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# ---------------------------------------------------------
# PAGE SETUP & BRANDING
# ---------------------------------------------------------
st.set_page_config(
    page_title="DHA CRM & AI Engine | Wali Muhammad Associates",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 DHA Enterprise Multi-Workbook CRM & Live AI Engine")
st.caption("Automated WhatsApp Ingestion & Phase/Block Sync | Wali Muhammad Associates")

CANONICAL_COLUMNS = [
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

DHA_PHASES = [
    "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", 
    "Phase 6", "Phase 7", "Phase 8", "Phase 9 Town", "Phase 9 Prism", 
    "Phase 10", "Phase 11 Rahbar", "Phase 12 EME", "Other Projects"
]

# ---------------------------------------------------------
# STRUCTURED PYDANTIC SCHEMA
# ---------------------------------------------------------
class PropertyListing(BaseModel):
    category: str = Field(description="'Selling' or 'Dealer Lead'")
    phase: str = Field(description="Normalized DHA Phase e.g. 'Phase 6', 'Phase 9 Prism', 'Phase 8', 'Phase 7', 'Phase 5', 'Phase 4', 'Phase 9 Town', 'Phase 11 Rahbar', 'Other Projects'")
    block: str = Field(description="Block name/letter without 'Block' prefix e.g. 'C', 'KK', 'Z5', 'CCA', 'Broadway', 'Zone 3'")
    plot_no: str = Field(description="Plot number or pair e.g. '858', '1964+1965', '1122/1-3', 'N/A'")
    size: str = Field(description="Standard size: '5 Marla', '10 Marla', '1 Kanal', '2 Kanal', '4 Marla Commercial', '8 Marla Commercial', etc.")
    plot_features: str = Field(description="Details like 'Corner', '150ft Road', 'Facing Park', 'Possession', 'DP Pole Clear', 'Pair'")
    demand_price: str = Field(description="Standard price e.g. '485 Lac', '3.25 Cr', '7 Crore', 'Offer Req'")
    seller_type: str = Field(description="Direct Owner, Dealer, Investor, or Unknown")
    seller_name: str = Field(description="Dealer / sender name if found")
    contact_no: str = Field(description="Extracted WhatsApp / phone number(s)")
    office_agency: str = Field(description="Agency name mentioned e.g. 'Brothers Estate', 'R&R Properties', 'Skyy Real Estate'")
    deal_status: str = Field(default="Available")
    notes: str = Field(description="Additional remarks, file status, meeting terms")
    raw_listing: str = Field(description="Original snippet for audit")

class ExtractionResult(BaseModel):
    listings: List[PropertyListing]

# ---------------------------------------------------------
# GCP SERVICE ACCOUNT AUTHENTICATION
# ---------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    try:
        service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ GCP Auth Error: {str(e)}")
        return None

# ---------------------------------------------------------
# PRE-SANITIZATION & GEMINI EXTRACTION
# ---------------------------------------------------------
def sanitize_whatsapp_text(raw_text: str) -> str:
    """Strips WhatsApp system lines, timestamps, and media placeholders."""
    lines = raw_text.splitlines()
    cleaned = []
    for line in lines:
        if "<Media omitted>" in line or "security code changed" in line or "Messages and calls are end-to-end" in line:
            continue
        cleaned_line = re.sub(r"^\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*-\s*", "", line)
        if cleaned_line.strip():
            cleaned.append(cleaned_line)
    return "\n".join(cleaned)

def parse_with_gemini(raw_text: str) -> pd.DataFrame:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
    
    cleaned_input = sanitize_whatsapp_text(raw_text)

    system_instruction = (
        "You are an expert DHA Lahore real estate cataloger for Wali Muhammad Associates. "
        "Extract raw text into structured JSON listings strictly matching the canonical schema. "
        "RULES: "
        "1. Break every individual plot from broadcast messages into its own row. "
        "2. Keep dealer names, agency names, and contact numbers attached to all plots in their respective message blocks. "
        "3. Accurately detect DHA Phases: Phase 1 to Phase 12 EME, Phase 9 Prism, Phase 9 Town, Phase 11 Rahbar. "
        "4. Non-DHA properties (e.g. Gujranwala, Saddat Town, HBFC, Sui Gas) must be assigned Phase 'Other Projects'. "
        "5. Correctly capture sub-blocks: Ivy Green (Z5, Z6), Phase 4 (KK), Commercials (CCA, Broadway, Air Avenue). "
        "6. Never hallucinate block names. If only a dealer contact is posted without a plot, categorize as 'Dealer Lead'."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Extract and structure every property listing from this cleaned real estate chat stream:\n\n{cleaned_input}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ExtractionResult,
            temperature=0.1
        )
    )

    parsed_obj = json.loads(response.text)
    items = parsed_obj.get("listings", [])
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_rows = []

    for item in items:
        row = {
            "Date / Timestamp": timestamp,
            "Category": item.get("category", "Selling"),
            "Phase": item.get("phase", "Phase 6"),
            "Block": str(item.get("block", "General")).upper().replace("BLOCK", "").strip(),
            "Plot No": str(item.get("plot_no", "N/A")),
            "Size": item.get("size", "N/A"),
            "Plot Features": item.get("plot_features", "Normal"),
            "Demand / Price": str(item.get("demand_price", "N/A")),
            "Seller Type": item.get("seller_type", "Dealer"),
            "Seller / Dealer Name": item.get("seller_name", "Unknown"),
            "Contact No": str(item.get("contact_no", "")),
            "Office / Agency": item.get("office_agency", "Direct / Unknown"),
            "Deal Status": item.get("deal_status", "Available"),
            "Last Conversation / Notes": item.get("notes", ""),
            "Raw Listing & Source Material": item.get("raw_listing", "")
        }
        formatted_rows.append(row)

    return pd.DataFrame(formatted_rows)

# ---------------------------------------------------------
# MULTI-WORKBOOK GOOGLE SHEETS SYNC
# ---------------------------------------------------------
def sync_to_multi_workbooks(gc, df: pd.DataFrame):
    logs = []
    grouped_by_phase = df.groupby("Phase")

    for phase_name, phase_df in grouped_by_phase:
        workbook_title = f"DHA {phase_name.strip()}"
        
        # 1. Open or create target phase workbook
        try:
            sh = gc.open(workbook_title)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(workbook_title)
            logs.append(f"📁 Created Workbook: **{workbook_title}**")

        # 2. Group by Block inside this Phase
        grouped_by_block = phase_df.groupby("Block")
        for block_name, block_df in grouped_by_block:
            tab_name = str(block_name).strip().upper() if str(block_name).strip() else "GENERAL"

            try:
                ws = sh.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title=tab_name, rows=200, cols=len(CANONICAL_COLUMNS))
                ws.append_row(CANONICAL_COLUMNS)
                logs.append(f"📄 Created Tab `{tab_name}` in `{workbook_title}`")

            # Push all rows for this block at once
            rows_data = block_df[CANONICAL_COLUMNS].values.tolist()
            ws.append_rows(rows_data)
            logs.append(f"✅ Synced **{len(rows_data)} listing(s)** to `{workbook_title}` ➔ Tab `{tab_name}`")

    return logs

# ---------------------------------------------------------
# LIVE WORKBOOK INVENTORY FETCHER
# ---------------------------------------------------------
def fetch_inventory(gc, phase: str, block: str = "ALL"):
    workbook_title = f"DHA {phase}"
    try:
        sh = gc.open(workbook_title)
    except gspread.SpreadsheetNotFound:
        return pd.DataFrame()

    all_data = []
    if block == "ALL":
        for ws in sh.worksheets():
            records = ws.get_all_records()
            all_data.extend(records)
    else:
        try:
            ws = sh.worksheet(block.strip().upper())
            all_data = ws.get_all_records()
        except gspread.WorksheetNotFound:
            return pd.DataFrame()

    return pd.DataFrame(all_data)

# ---------------------------------------------------------
# APPLICATION UI
# ---------------------------------------------------------
gc = get_gspread_client()

tab1, tab2 = st.tabs(["📥 Extract & Sync to Workbooks", "📊 Live Inventory & Broadcast"])

# =========================================================
# TAB 1: EXTRACTION & AUTO SYNC
# =========================================================
with tab1:
    st.subheader("WhatsApp Chat Export Stream")
    chat_input = st.text_area(
        "Paste your exported WhatsApp chat text directly here:",
        height=220,
        placeholder="Paste full WhatsApp export messages here..."
    )

    c1, c2 = st.columns([1.5, 4])
    with c1:
        extract_btn = st.button("⚡ Extract & Arrange (Gemini 2.5)", type="primary", use_container_width=True)
    with c2:
        if st.button("🧹 Reset Data"):
            st.session_state.pop("structured_data", None)
            st.rerun()

    if extract_btn:
        if not chat_input.strip():
            st.warning("Please paste some WhatsApp text to extract.")
        else:
            with st.spinner("Sanitizing WhatsApp export & running Gemini 2.5 Flash Parser..."):
                try:
                    extracted_df = parse_with_gemini(chat_input)
                    st.session_state["structured_data"] = extracted_df
                    st.success(f"Successfully extracted {len(extracted_df)} clean listings across all Phases!")
                except Exception as e:
                    st.error(f"Extraction Error: {str(e)}")

    if "structured_data" in st.session_state:
        df_live = st.session_state["structured_data"]
        st.markdown("### 📋 Structured Listings Review")
        
        # Summary distribution metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Plots Extracted", len(df_live))
        col_m2.metric("Unique Phases Detected", df_live["Phase"].nunique())
        col_m3.metric("Unique Blocks Detected", df_live["Block"].nunique())

        editable_df = st.data_editor(df_live, num_rows="dynamic", use_container_width=True)

        if st.button("🚀 Push to Multi-Phase Workbooks", type="primary"):
            if gc is None:
                st.error("Google Sheets Service Account authentication is missing or invalid.")
            else:
                with st.spinner("Syncing to individual Phase Workbooks and creating dynamic Block tabs..."):
                    sync_logs = sync_to_multi_workbooks(gc, editable_df)
                    st.success("All records routed and saved to Google Sheets successfully!")
                    with st.expander("Detailed Sync Logs", expanded=True):
                        for log in sync_logs:
                            st.markdown(log)

# =========================================================
# TAB 2: LIVE INVENTORY & BROADCAST
# =========================================================
with tab2:
    st.subheader("Fetch Live Phase / Block Inventory")
    col_p, col_b, col_btn = st.columns([2, 2, 2])
    
    with col_p:
        selected_phase = st.selectbox("Select Phase Workbook:", DHA_PHASES)
    with col_b:
        selected_block = st.text_input("Filter by Block (or keep 'ALL'):", value="ALL")
    with col_btn:
        st.write("")
        st.write("")
        load_btn = st.button("🔍 Load Live Sheet Data", use_container_width=True)

    if load_btn:
        if gc is None:
            st.error("Google Sheets authentication failed.")
        else:
            with st.spinner(f"Reading data from 'DHA {selected_phase}'..."):
                inv_df = fetch_inventory(gc, selected_phase, selected_block)
                if inv_df.empty:
                    st.info(f"No records found in DHA {selected_phase} for Block: {selected_block}")
                else:
                    st.session_state["active_inventory"] = inv_df
                    st.success(f"Retrieved {len(inv_df)} verified entries.")

    if "active_inventory" in st.session_state:
        inv = st.session_state["active_inventory"]
        st.dataframe(inv, use_container_width=True)

        st.divider()
        st.subheader("📢 Ready-to-Send WhatsApp Broadcast")
        
        broadcast_text_list = [f"*--- DHA {selected_phase} AVAILABLE INVENTORY ---*"]
        for _, row in inv.iterrows():
            line = f"📍 *Block {row.get('Block', '')}* | {row.get('Size', '')} | Plot: {row.get('Plot No', '')} | Demand: {row.get('Demand / Price', '')} | Features: {row.get('Plot Features', 'Normal')} | Ph: {row.get('Contact No', '')}"
            broadcast_text_list.append(line)
        
        st.text_area("One-Click Broadcast Summary:", value="\n".join(broadcast_text_list), height=200)
