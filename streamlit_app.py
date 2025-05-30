import streamlit as st
from api_logic import bulk_upsert
from api_fetch import get_all_project_segment_items_csv
from api_file import get_all_project_segments_csv
from api_companies import get_all_companies_csv
from api_reset import reset_custom_object_cache  # <-- De script voor de reset knop!


with open("logo_base64.txt") as f:
    base64_logo = f.read()


st.set_page_config(page_title="HIVE BulkUpsert Tool", layout="centered", page_icon="🛠️")

# SIDEBAR: Credentials
st.sidebar.header("API Credentials")
manufacturer_id = st.sidebar.text_input("manufacturerId")
client_id = st.sidebar.text_input("client_id")
client_secret = st.sidebar.text_input("client_secret", type="password")
st.sidebar.markdown("---")
st.sidebar.info("Vul je API-gegevens in. Die blijven bewaard zolang je deze pagina open hebt.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "BulkUpsert",
    "Add Unit",
    "Get all project segment items",
    "Get all project segments",
    "Get all companies"
])


with tab1:
    st.title("BulkUpsert uitvoeren")
    st.markdown("Plak hieronder je JSON-object:")
    json_input = st.text_area("JSON input", height=200, key="bulkupsert_json_tab1")

    # Reset cache knop
    if st.button("Reset Custom Object Cache", key="reset_cache_btn_tab1"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in!")
        else:
            with st.spinner('Resetten...'):
                reset_response = reset_custom_object_cache(manufacturer_id, client_id, client_secret)
            st.code(reset_response, language='json')

    if st.button("Verzenden", key="bulkupsert_send_tab1"):
        if not all([manufacturer_id, client_id, client_secret, json_input.strip()]):
            st.error("Vul alle credentials én JSON in!")
        else:
            with st.spinner('Verzenden...'):
                response = bulk_upsert(manufacturer_id, client_id, client_secret, json_input)
            st.code(response, language='json')

    # Helptekst / JSON voorbeeld toevoegen
    st.markdown("""
    <br>
    **Dit is de structuur van hoe de JSON moet worden opgebouwd (exact dezelfde structuur):**
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

with tab2:
    st.title("Add Unit")
    st.markdown("**Hier kun je straks units toevoegen.**")
    st.info("Deze tab is nog niet geconfigureerd.")

with tab3:
    st.title("Get all project segment items")
    st.markdown("Klik op onderstaande knop om alle project segment items als CSV te downloaden:")
    if st.button("Genereer CSV", key="get_project_segment_items_csv"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in de sidebar in!")
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

with tab4:
    st.title("Get all project segments")
    st.markdown("Klik op onderstaande knop om alle project segments als CSV te downloaden:")
    if st.button("Genereer Segments CSV", key="get_project_segments_csv"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in de sidebar in!")
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

with tab5:
    st.title("Get all companies")
    st.markdown("Klik op onderstaande knop om alle bedrijven als CSV te downloaden:")
    if st.button("Genereer Companies CSV", key="get_companies_csv"):
        if not all([manufacturer_id, client_id, client_secret]):
            st.error("Vul alle credentials in de sidebar in!")
        else:
            with st.spinner('Ophalen en converteren...'):
                csv_content = get_all_companies_csv(manufacturer_id, client_id, client_secret)
                if isinstance(csv_content, tuple) and csv_content[0] is None:
                    st.error(csv_content[1])
                elif not csv_content:
                    st.error("Onbekende fout of geen data opgehaald.")
                else:
                    st.success("CSV succesvol gegenereerd!")
                    st.download_button(
                        label="Download Companies CSV",
                        data=csv_content,
                        file_name="bedrijven_export.csv",
                        mime="text/csv"
                    )

st.markdown("""
---
**Hulp nodig?** Neem contact op met IT Support.
"""
"""
Arbi.Taramov@polletgroupit.com
""")
