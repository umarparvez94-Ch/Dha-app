import streamlit as st
import gspread
import json

st.set_page_config(page_title="DHA Property Portal", layout="centered")

# Streamlit / GitHub Secrets se Credentials load karna
try:
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "GCP_SERVICE_ACCOUNT" in st.secrets:
        creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
    else:
        st.error("Secrets missing! Please check Streamlit/GitHub Secrets.")
        st.stop()

    # Google Sheets Connection
    gc = gspread.service_account_from_dict(creds_dict)
    SHEET_NAME = "Dha_Master_data_app"
    sh = gc.open(SHEET_NAME)
    worksheet = sh.sheet1

except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

st.title("🏡 DHA Property Entry Portal")

# 1. Source Select Option (WhatsApp Group / Facebook / Direct Client etc.)
source = st.selectbox(
    "📍 Select Data Source:",
    ["WhatsApp Group", "Direct Client", "Facebook Group", "Dealer Network", "Other"]
)

# 2. Raw Text Input Box
raw_text = st.text_area("📝 Paste Property Text / Message:", height=180)

# 3. Save Button & Confirmation Action
if st.button("💾 Save Data", type="primary", use_container_width=True):
    if raw_text.strip():
        try:
            # Selected Source and Raw Text added to sheet
            worksheet.append_row([source, raw_text])
            st.balloons()
            st.success(f"✅ Data successfully **{source}** کی شیٹ میں Save ہو گیا ہے!")
        except Exception as e:
            st.error(f"Save failed: {e}")
    else:
        st.warning("⚠️ پہلے کچھ raw text کاپی کر کے پیسٹ کریں!")
