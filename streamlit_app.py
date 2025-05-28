import streamlit as st
from api_logic import bulk_upsert

st.set_page_config(page_title="HIVE BulkUpsert Tool", layout="centered")
st.title("HIVE BulkUpsert Tool")

st.markdown("Vul onderstaande gegevens in en plak je JSON-object:")

manufacturer_id = st.text_input("manufacturerId")
client_id = st.text_input("client_id")
client_secret = st.text_input("client_secret", type="password")
json_input = st.text_area("Plak je JSON hier (één regel of meerdere regels):", height=200)

if st.button("Verzenden"):
    if not all([manufacturer_id, client_id, client_secret, json_input.strip()]):
        st.error("Vul alle velden in!")
    else:
        with st.spinner('Verzenden...'):
            response = bulk_upsert(manufacturer_id, client_id, client_secret, json_input)
        st.code(response, language='json')
