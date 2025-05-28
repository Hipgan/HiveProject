import streamlit as st
from api_logic import bulk_upsert
from api_fetch import get_all_project_segment_items_csv

st.set_page_config(page_title="HIVE BulkUpsert Tool", layout="centered", page_icon="🛠️")

# SIDEBAR: Credentials
st.sidebar.header("API Credentials")
manufacturer_id = st.sidebar.text_input("manufacturerId")
client_id = st.sidebar.text_input("client_id")
client_secret = st.sidebar.text_input("client_secret", type="password")
st.sidebar.markdown("---")
st.sidebar.info("Vul je API-gegevens in. Die blijven bewaard zolang je deze pagina open hebt.")

# TABS
tab1, tab2, tab3 = st.tabs(["BulkUpsert", "Add Unit", "Get all project segment items"])

with tab1:
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

st.markdown("""
---
**Hulp nodig?** Neem contact op met IT Support.
""")
