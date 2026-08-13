import streamlit as st
import gspread

st.set_page_config(page_title="DHA Property Portal", layout="centered")

# Credentials loading
try:
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
    else:
        st.error("Secrets missing! Please check Streamlit Secrets.")
        st.stop()
except Exception as e:
    st.error(f"Credentials Error: {e}")
    st.stop()

# Google Sheet Connection
try:
    sheet = gc.open("Dha_Master_data_app").sheet1
except Exception as e:
    st.error(f"Sheet Connection Error: {e}")
    st.stop()

st.title("🏠 DHA Property Entry Portal")
st.write("پراپرٹی کا خام ڈیٹا نیچے ڈبے میں پیسٹ کریں اور سیو کریں۔")

source = st.selectbox("Data Source", ["WhatsApp Group", "Direct Client", "Facebook", "Other"])
raw_text = st.text_area("Paste Raw Property Text Here", height=200)

if st.button("💾 Save Data", use_container_width=True):
    if raw_text.strip():
        try:
            # Append data to sheet: [Source, Raw Text]
            sheet.append_row([source, raw_text])
            st.success("✅ ڈیٹا کامیابی سے گوگل شیٹ میں محفوظ ہو گیا ہے!")
            st.balloons()
        except Exception as e:
            st.error(f"Error saving data: {e}")
    else:
        st.warning("براہِ کرم پہلے کچھ ٹیکسٹ پیسٹ کریں۔")
