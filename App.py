import streamlit as st
import json
import pandas as pd
from google.oauth2 import service_account
import google.generativeai as genai
import gspread

# --- 1. CONFIG & CREDENTIALS ---
st.set_page_config(page_title="DHA Enterprise Master CRM", layout="wide")

# Google Sheets & GCP Service Account Logic (Fixed for Secrets)
def get_sheets_client():
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
    }
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# Initialize Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. UI & INGESTION LOGIC ---
st.title("🚀 DHA Enterprise Master CRM & Data Compiler")

uploaded_file = st.file_uploader("Upload WhatsApp Chat Export (.txt)", type=["txt"])

if uploaded_file is not None:
    file_content = uploaded_file.getvalue().decode("utf-8")
    st.success(f"Loaded WhatsApp Chat ({len(file_content)} characters) ready for AI extraction!")
    
    if st.button("🚀 Start AI Ingestion & Update Master Summary"):
        # Yahan aapka wahi purana extraction aur sheet update ka logic ayega
        # Jo aap 5 bajy tak istemal kar rhy thy
        with st.spinner("Processing data..."):
            st.info("AI Ingestion process is running...")
            # (Apna purana extraction code yahan waisa ka waisa hi rahega)
            
else:
    st.info("Master Summary Sheet is empty. Load your text/files above and click 'Start AI Ingestion'.")
