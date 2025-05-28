import streamlit as st
from api_logic import bulk_upsert

st.set_page_config(
    page_title="HIVE BulkUpsert Tool",
    layout="wide",
    page_icon="🛠️"
)

st.title("HIVE BulkUpsert Tool")

tab1, tab2 = st.tabs(["BulkUpsert", "Over"])

with tab1:
    col1, col2 = st.columns([2, 3])
    with col1:
        manufacturer_id = st.text_input("manufacturerId")
        client_id = st.text_input("client_id")
        client_secret = st.text_input("client_secret", type="password")
        st.markdown("Plak hieronder je JSON:")
        json_input = st.text_area("", height=200)
        if st.button("Verzenden"):
            if not all([manufacturer_id, client_id, client_secret, json_input.strip()]):
                st.error("Vul alle velden in!")
            else:
                with st.spinner('Verzenden...'):
                    response = bulk_upsert(manufacturer_id, client_id, client_secret, json_input)
                st.session_state['last_response'] = response
    with col2:
        st.markdown("### Respons")
        if 'last_response' in st.session_state:
            st.code(st.session_state['last_response'], language='json')

with tab2:
    st.header("Over deze app")
    st.markdown("""
    **Versie**: 1.0  
    **Door**: Arbi  
    - BulkUpsert tool voor HIVE API
    - Ontworpen met Streamlit  
    """)

st.sidebar.title("Menu")
st.sidebar.info("Gebruik de tabbladen bovenaan om te navigeren.")
st.sidebar.markdown("Contact: jouw@email.com")
