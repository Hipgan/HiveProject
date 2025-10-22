import requests
import pandas as pd
from io import BytesIO

def get_all_companies_excel(
    manufacturer_id,
    client_id,
    client_secret,
    output_path=None,
    manufacturer_slug=None,   # bv. "MyAquadeck"
    timeout=30
):
    """
    Haalt alle companies op en verrijkt met customObject-velden:
      - currency
      - customer price group
      - company discount group

    Voor SUB_DISTRIBUTOR:
      /customObjects/distributor-{distributorId}/{subDistributorId}

    Voor DISTRIBUTOR:
      /customObjects/distributor-{distributorId}/{distributorId}
    """
    try:
        # 0. Hulpfuncties
        def auth_token():
            token_url = "https://ebusinesscloud.eu.auth0.com/oauth/token"
            token_payload = {
                "grant_type": "client_credentials",
                "client_name": "API USER",
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": "https://ebusinesscloud.eu.auth0.com/api/v2/",
                "domain": "https://ebusinesscloud.eu.auth0.com"
            }
            headers = {"Content-Type": "application/json"}
            r = requests.post(token_url, json=token_payload, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()["access_token"]

        def fetch_custom_object(session, bearer, m_slug, distributor_id, key_id):
            """
            GET /api/v1/manufacturers/{m_slug}/customObjects/distributor-{distributor_id}/{key_id}
            Retourneert dict met keys -> values uit keyValues.
            """
            co_url = (
                f"https://api.hivecpq.com/api/v1/manufacturers/{m_slug}"
                f"/customObjects/distributor-{distributor_id}/{key_id}"
            )
            headers = {"Authorization": f"Bearer {bearer}"}
            r = session.get(co_url, headers=headers, timeout=timeout)
            if r.status_code == 404:
                # Geen customObject voor deze combinatie; stil terugkeren
                return {}
            r.raise_for_status()
            payload = r.json() or {}
            key_values = payload.get("keyValues", []) or []
            out = {}
            for kv in key_values:
                k = (kv.get("key") or "").strip()
                v = kv.get("value")
                out[k] = v
            return out

        # 1. Token ophalen
        access_token = auth_token()

        # 2. Bedrijven ophalen
        companies_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies?pageSize=1000"
        headers = {"Authorization": f"Bearer {access_token}"}
        with requests.Session() as s:
            r = s.get(companies_url, headers=headers, timeout=timeout)
            r.raise_for_status()
            companies = r.json()

            # 3. "items" uitpakken indien nodig
            if isinstance(companies, dict) and "items" in companies:
                companies = companies["items"]

            m_slug = manufacturer_slug or manufacturer_id

            # 4. Data structureren + customObject per bedrijf
            data = []
            for company in companies:
                info = company.get('info', {}) or {}
                address = info.get('address', {}) or {}

                distributor_name = ''
                distributor_id = ''
                key_id_for_custom_object = ''

                ctype = company.get('companyType')
                cid = company.get('id', '')

                if ctype == 'SUB_DISTRIBUTOR':
                    sub_settings = company.get('subDistributorSettings', {}) or {}
                    distributor = sub_settings.get('distributor', {}) or {}
                    distributor_name = distributor.get('name', '') or ''
                    distributor_id = distributor.get('id', '') or ''
                    # customObject key id is subdistributeur id
                    key_id_for_custom_object = cid
                elif ctype == 'DISTRIBUTOR':
                    distributor_name = info.get('name', '') or ''
                    distributor_id = cid
                    # customObject key id = distributor id
                    key_id_for_custom_object = cid
                else:
                    # Andere types: geen customObject-call
                    distributor_name = ''
                    distributor_id = ''
                    key_id_for_custom_object = ''

                # Defaults voor de drie nieuwe kolommen
                currency = ''
                customer_price_group = ''
                company_discount_group = ''

                # 4b. CustomObject-call uitvoeren indien van toepassing
                if distributor_id and key_id_for_custom_object:
                    try:
                        kv = fetch_custom_object(
                            s, access_token, m_slug, distributor_id, key_id_for_custom_object
                        )
                        # Exacte keys zoals in je voorbeeld
                        currency = kv.get('currency', '') or ''
                        customer_price_group = kv.get('customer price group', '') or ''
                        company_discount_group = kv.get('company discount group', '') or ''
                    except requests.HTTPError as e:
                        # Als de call faalt, laten we de kolommen leeg en gaan door
                        pass

                # 4c. Rij opbouwen
                row = {
                    'id': cid,
                    'companyType': ctype or '',
                    'name': (info.get('name') or '').strip(),
                    'description': (info.get('description') or '').strip(),
                    'distributor': distributor_name,
                    'distributorId': distributor_id,
                    'telephone': info.get('telephone', ''),
                    'vatNumber': (info.get('vatNumber') or '').strip(),
                    'email': info.get('email', ''),
                    'websiteUrl': info.get('websiteUrl', ''),
                    'preferredLanguage': info.get('preferredLanguage', ''),
                    'addressLine1': address.get('addressLine1', ''),
                    'addressLine2': address.get('addressLine2', ''),
                    'city': address.get('city', ''),
                    'postalCode': address.get('postalCode', ''),
                    'countryIso': address.get('countryIso', ''),
                    # Nieuwe kolommen uit customObject
                    'currency': currency,
                    'customer price group': customer_price_group,
                    'company discount group': company_discount_group,
                }
                data.append(row)

        # 5. Kolomvolgorde
        columns = [
            'id',
            'companyType',
            'name',
            'description',
            'distributor',
            'distributorId',
            'telephone',
            'vatNumber',
            'email',
            'websiteUrl',
            'preferredLanguage',
            'addressLine1',
            'addressLine2',
            'city',
            'postalCode',
            'countryIso',
            # nieuwe kolommen (exacte benamingen zoals gevraagd)
            'currency',
            'customer price group',
            'company discount group',
        ]
        df = pd.DataFrame(data, columns=columns)

        # 6. Excel maken in-memory
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        # Optioneel: opslaan op schijf
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(output.getbuffer())

        return output  # succes
    except Exception as e:
        return None, f"Onverwachte fout: {str(e)}"
