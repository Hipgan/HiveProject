import streamlit as st
from api_logic import bulk_upsert
from api_fetch import get_all_project_segment_items_csv
from api_file import get_all_project_segments_csv
from api_companies import get_all_companies_excel
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
            st.code(response, language='json')
    if st.button("Reset Custom Object Cache", key="reset_cache_btn"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in!")
        else:
            with st.spinner('Resetten...'):
                reset_response = reset_custom_object_cache(manufacturer_id, client_id, client_secret)
            st.code(reset_response, language='json')
    st.markdown("""
    <br>
    **Voorbeeld JSON structuur:**
    """, unsafe_allow_html=True)
    st.code(
        '''{
  "company discount group": "D40",
  "customer price group": "PGC01",
  "currency": "EUR",
  "description": "",
  "hiveCPQId": "d11c5a1323ed4b789238e168b803803b",
  "name": "AMARQUE LEISURE SOLUTIONS B.V.",
  "parent_dealerId": "5d5b62fa8dd94e3c9009929f2682f331"
}''', language="json")

# 2. Get all project segment items
elif functionaliteit == "Get all project segment items":
    st.title("Get all project segment items")
    st.markdown("Klik op onderstaande knop om alle project segment items als CSV te downloaden:")
    if st.button("Genereer CSV", key="get_project_segment_items_csv"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in!")
        else:
            with st.spinner('Ophalen en converteren...'):
                csv_content = get_all_project_segment_items_csv(manufacturer_id, client_id, client_secret)
                if isinstance(csv_content, tuple) and csv_content[0] is None:
                    st.error(csv_content[1])
                elif not csv_content:
                    st.error("Onbekende fout of geen data opgehaald.")
                else:
                    st.success("CSV succesvol gegenereerd!")
                    st.download_button(
                        label="Download CSV",
                        data=csv_content,
                        file_name="projectSegmentItems.csv",
                        mime="text/csv"
                    )

# 3. Get all project segments
elif functionaliteit == "Get all project segments":
    st.title("Get all project segments")
    st.markdown("Klik op onderstaande knop om alle project segments als CSV te downloaden:")
    if st.button("Genereer Segments CSV", key="get_project_segments_csv"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in!")
        else:
            with st.spinner('Ophalen en converteren...'):
                csv_content = get_all_project_segments_csv(manufacturer_id, client_id, client_secret)
                if isinstance(csv_content, tuple) and csv_content[0] is None:
                    st.error(csv_content[1])
                elif not csv_content:
                    st.error("Onbekende fout of geen data opgehaald.")
                else:
                    st.success("CSV succesvol gegenereerd!")
                    st.download_button(
                        label="Download Segments CSV",
                        data=csv_content,
                        file_name="projectSegments.csv",
                        mime="text/csv"
                    )

elif functionaliteit == "Get all companies":
    st.title("Get all companies")
    st.markdown("Klik op onderstaande knop om alle bedrijven als Excel te downloaden:")
    if st.button("Genereer Companies Excel", key="get_companies_excel"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in!")
        else:
            with st.spinner('Ophalen en converteren...'):
                excel_content = get_all_companies_excel(manufacturer_id, client_id, client_secret)
                if isinstance(excel_content, tuple) and excel_content[0] is None:
                    st.error(excel_content[1])
                elif not excel_content:
                    st.error("Onbekende fout of geen data opgehaald.")
                else:
                    st.success("Excel succesvol gegenereerd!")
                    st.download_button(
                        label="Download Companies Excel",
                        data=excel_content,
                        file_name="bedrijven_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )


# 5. Update Units
elif functionaliteit == "Update Units":
    st.title("Update Unit van Components")
    st.markdown("""
    **Wijzig de 'unit' van één of meerdere bestaande componenten (op basis van articleCode).**
    - Plak de gewenste articleCodes, gescheiden door komma's.
    - Vul het gewenste unitCode in (bijvoorbeeld: MAT, PCS, ...).
    - Geef de juiste versie op (bijvoorbeeld: 3.0.0).
    """)
    article_codes_input = st.text_area("Plak lijst van articleCodes (gescheiden door komma's)", height=100)
    unit_code_input = st.text_input("Geef de unitCode op (bijvoorbeeld: MAT, PCS, ...)")
    version_input = st.text_input("Geef de versie op (bijvoorbeeld: 3.0.0)")
    if st.button("Update Unit(s)"):
        if not all([manufacturer_id, client_id, client_secret, article_codes_input.strip(), unit_code_input.strip(), version_input.strip()]):
            st.error("Vul alle velden én API-credentials in!")
        else:
            with st.spinner("Bezig met updaten..."):
                results = update_units_of_components(
                    manufacturer_id, client_id, client_secret,
                    article_codes_input, unit_code_input, version_input
                )
            if results and isinstance(results, list):
                st.success("Update uitgevoerd! Zie resultaat hieronder.")
                st.write(results)
            else:
                st.error("Er is iets misgegaan of er zijn geen resultaten.")

# 6. Move to Step 4
elif functionaliteit == "Move to Step 4":
    st.title("Move to Step 4")
    st.markdown("""
    **Bevestig de shipping date en verplaats meerdere projecten tegelijk naar Step 4.**
    - Upload of plak je lijst (tab-gescheiden, eerste regel is header; kolommen: salesId, projectId)
    - Geef de gewenste shippingDateConfirmed in (dd/mm/yy, bijvoorbeeld 05/06/25).
    """)
    input_content = st.text_area(
        "Plak hier je tab-gescheiden input-bestand (salesId\tprojectId)", height=150
    )
    shipping_date = st.text_input("ShippingDateConfirmed (dd/mm/yy)")
    if st.button("Verwerk naar Step 4"):
        if not all([manufacturer_id, client_id, client_secret, input_content.strip(), shipping_date.strip()]):
            st.error("Vul alle velden én API-credentials in!")
        else:
            with st.spinner("Bezig met verwerken..."):
                resultaten = move_segments_to_step4(
                    manufacturer_id, client_id, client_secret, shipping_date, input_content
                )
            if resultaten and isinstance(resultaten, list):
                st.success("Klaar! Zie log/resultaten hieronder.")
                st.write(resultaten)
            else:
                st.error("Er is iets misgegaan of er zijn geen resultaten.")

# 7. Export BOM (meerdere tegelijk!)
elif functionaliteit == "Export BOM":
    st.title("Export BOM naar Excel")
    st.markdown("""
    Exporteer de volledige stuklijststructuur (BOM) van een of meerdere configuraties naar een Excel-bestand.<br>
    Vul per regel een <b>ProjectSegmentItemId</b> in en klik op 'Genereer BOM Excel'.<br>
    <i>Indien je meerdere IDs invult (elk op een nieuwe regel), worden alle BOMs gecombineerd in één Excel-bestand.</i>
    """, unsafe_allow_html=True)
    segment_item_ids_input = st.text_area("ProjectSegmentItemId(s) (één per regel)", height=120)
    segment_item_ids = [x.strip() for x in segment_item_ids_input.splitlines() if x.strip()]
    if st.button("Genereer BOM Excel"):
        if not all([manufacturer_id, client_id, client_secret, segment_item_ids]):
            st.error("Vul alle API-credentials én minimaal één ProjectSegmentItemId in!")
        else:
            with st.spinner("BOM wordt opgehaald en verwerkt..."):
                excel_bytes, filename, error = export_bom_to_excel(
                    manufacturer_id, client_id, client_secret, segment_item_ids
                )
            if error:
                st.error(f"Fout bij exporteren van BOM: {error}")
            elif excel_bytes:
                st.success("Excel-bestand gegenereerd!")
                st.download_button(
                    label="Download Excel",
                    data=excel_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Onbekende fout, geen bestand aangemaakt.")

st.markdown("""
---
**Hulp nodig?** Neem contact op met IT Support.
"""
)
