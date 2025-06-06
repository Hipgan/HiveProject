import streamlit as st
from api_logic import bulk_upsert
from api_fetch import get_all_project_segment_items_csv
from api_file import get_all_project_segments_csv
from api_companies import get_all_companies_csv
from api_reset import reset_custom_object_cache
from api_unit import update_units_of_components
from api_step4 import move_segments_to_step4
from api_ExportBom import export_bom_to_excel  # aangepast: accepteert nu lijst van ids

import base64
from io import BytesIO
from PIL import Image

USERNAME = st.secrets["login"]["username"]
PASSWORD = st.secrets["login"]["password"]

def check_password():
    def password_entered():
        if (st.session_state["password"] == PASSWORD
            and st.session_state["username"] == USERNAME):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("Login vereist")
        st.text_input("Gebruikersnaam", on_change=password_entered, key="username")
        st.text_input("Wachtwoord", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.title("Login vereist")
        st.text_input("Gebruikersnaam", on_change=password_entered, key="username")
        st.text_input("Wachtwoord", type="password", on_change=password_entered, key="password")
        st.error("Onjuiste gebruikersnaam of wachtwoord")
        st.stop()
    else:
        return True

if not check_password():
    st.stop()

st.set_page_config(page_title="HIVE Tool", layout="centered", page_icon="🛠️")

# Sidebar logo
with open("logo_base64.txt") as f:
    base64_string = f.read().strip()
if "base64," in base64_string:
    base64_string = base64_string.split("base64,")[-1]
image_bytes = base64.b64decode(base64_string)
try:
    image = Image.open(BytesIO(image_bytes))
except Exception as e:
    st.sidebar.error(f"Fout in het logo: {e}")
else:
    st.sidebar.image(image, width=150)

# Sidebar credentials
st.sidebar.header("API Credentials")
manufacturer_id = st.sidebar.text_input("manufacturerId")
client_id = st.sidebar.text_input("client_id")
client_secret = st.sidebar.text_input("client_secret", type="password")
st.sidebar.markdown("---")
st.sidebar.info("Vul je API-gegevens in. Die blijven bewaard zolang je deze pagina open hebt.")

# Sidebar functionaliteitskeuze
functionaliteit = st.sidebar.selectbox(
    "Kies een functie:",
    [
        "BulkUpsert",
        "Get all project segment items",
        "Get all project segments",
        "Get all companies",
        "Update Units",
        "Move to Step 4",
        "Export BOM"
    ]
)

# 1. BulkUpsert
if functionaliteit == "BulkUpsert":
    st.title("BulkUpsert uitvoeren")
    st.markdown("Plak hieronder je JSON-object:")
    json_input = st.text_area("JSON input", height=200, key="bulkupsert_json")
    if st.button("Verzenden", key="bulkupsert_send"):
        if not all([manufacturer_id, client_id, client_secret, json_input.strip()]):
            st.error("Vul alle credentials én JSON in!")
        else:
            with st.spinner('Verzenden...'):
                response = bulk_upsert(manufacturer_id, client_id, client_secret, json_input)
