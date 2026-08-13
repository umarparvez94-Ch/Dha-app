import streamlit as st
import gspread

st.set_page_config(page_title="DHA Property Portal", layout="centered")

# Load Credentials & Connect to Google Sheets
@st.cache_resource
def get_google_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(creds_dict)
    
    # Direct Sheet Link
    sheet_url = "https://docs.google.com/spreadsheets/d/14FCDh1QuLTTobH94d-cJ-DMGCQugnzoblnbFmJvyuDU/edit?gid=0#gid=0"
    
    return gc.open_by_url(sheet_url).sheet1

try:
    sheet = get_google_sheet()
except Exception as e:
    st.error(f"Sheet Connection Failed: {e}")
    st.stop()

# Portal UI
st.title("🏠 DHA Property Entry Portal")
st.write("پراپرٹی کا ڈیٹا نیچے باکس میں پیسٹ کریں اور سیو کریں۔")

source = st.selectbox("Data Source", ["WhatsApp Group", "Direct Client", "Facebook", "Other"])
raw_text = st.text_area("Paste Raw Property Text Here", height=200)

if st.button("💾 Save Data", use_container_width=True):
    if raw_text.strip():
        try:
            sheet.append_row([source, raw_text])
            st.success("✅ ڈیٹا کامیابی سے گوگل شیٹ میں محفوظ ہو گیا ہے!")
            st.balloons()
        except Exception as e:
            st.error(f"Error saving data: {e}")
    else:
        st.warning("براہِ کرم پہلے کچھ ٹیکسٹ پیسٹ کریں۔")
