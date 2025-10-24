import requests
import pandas as pd
from io import BytesIO

def get_companies_for_distributor_excel(
    manufacturer_id: str,
    client_id: str,
    client_secret: str,
    distributor_id: str,
    output_path: str | None = None,
    manufacturer_slug: str | None = None,  # bv. "MyAquadeck"
    timeout: int = 30
):
    """
    Haalt ALLEEN de opgegeven DISTRIBUTOR + diens SUB_DISTRIBUTORS op en verrijkt met customObject-velden:
      - currency
      - customer price group
      - company discount group

    Kolommen identiek aan get_all_companies_excel:
      ['id','companyType','name','description','distributor','distributorId',
       'telephone','vatNumber','email','websiteUrl','preferredLanguage',
       'addressLine1','addressLine2','city','postalCode','countryIso',
       'currency','customer price group','company discount group']

    CustomObject-paden:
      SUB_DISTRIBUTOR -> /customObjects/distributor-{distributorId}/{subDistributorId}
      DISTRIBUTOR     -> /customObjects/distributor-{distributorId}/{distributorId}
    """
    try:
        # 0) Helpers
        def auth_token() -> str:
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

        def fetch_custom_object(session: requests.Session, bearer: str, m_slug: str,
                                dist_id: str, key_id: str) -> dict:
            """
            GET /api/v1/manufacturers/{m_slug}/customObjects/distributor-{dist_id}/{key_id}
            -> dict { key: value } op basis van payload.keyValues[*].
            """
            url = (
                f"https://api.hivecpq.com/api/v1/manufacturers/{m_slug}"
                f"/customObjects/distributor-{dist_id}/{key_id}"
            )
            headers = {"Authorization": f"Bearer {bearer}"}
            r = session.get(url, headers=headers, timeout=timeout)
            if r.status_code == 404:
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

        # 1) Token
        access_token = auth_token()

        # 2) Alle companies ophalen (zoals in je originele code)
        companies_url = (
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies?pageSize=1000"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        with requests.Session() as s:
            r = s.get(companies_url, headers=headers, timeout=timeout)
            r.raise_for_status()
            companies = r.json()

            if isinstance(companies, dict) and "items" in companies:
                companies = companies["items"]

            m_slug = manufacturer_slug or manufacturer_id

            # 3) Filter: alleen de gevraagde distributeur + diens subdistributeurs
            filtered = []
            for c in companies:
                ctype = c.get("companyType")
                cid = c.get("id", "")
                if ctype == "DISTRIBUTOR" and cid == distributor_id:
                    filtered.append(c)
                elif ctype == "SUB_DISTRIBUTOR":
                    sub_settings = c.get("subDistributorSettings", {}) or {}
                    dist = sub_settings.get("distributor", {}) or {}
                    parent_id = dist.get("id", "")
                    if parent_id == distributor_id:
                        filtered.append(c)

            # 4) Verrijken met customObject-keys (alleen voor DISTRIBUTOR & SUB_DISTRIBUTOR)
            data_rows = []
            for company in filtered:
                info = company.get('info', {}) or {}
                address = info.get('address', {}) or {}

                distributor_name = ''
                dist_id_for_path = ''
                key_id_for_custom_object = ''

                ctype = company.get('companyType')
                cid = company.get('id', '')

                if ctype == 'SUB_DISTRIBUTOR':
                    sub_settings = company.get('subDistributorSettings', {}) or {}
                    distributor = sub_settings.get('distributor', {}) or {}
                    distributor_name = distributor.get('name', '') or ''
                    dist_id_for_path = distributor.get('id', '') or ''
                    key_id_for_custom_object = cid  # key = subDistributorId
                elif ctype == 'DISTRIBUTOR':
                    # Dit is de opgegeven distributeur zelf
                    distributor_name = info.get('name', '') or ''
                    dist_id_for_path = cid
                    key_id_for_custom_object = cid  # key = distributorId
                else:
                    # Andere types komen niet door de filter, maar voor de volledigheid:
                    dist_id_for_path = ''
                    key_id_for_custom_object = ''

                # Defaults
                currency = ''
                customer_price_group = ''
                company_discount_group = ''

                if dist_id_for_path and key_id_for_custom_object:
                    try:
                        kv = fetch_custom_object(
                            s, access_token, m_slug, dist_id_for_path, key_id_for_custom_object
                        )
                        currency = kv.get('currency', '') or ''
                        customer_price_group = kv.get('customer price group', '') or ''
                        company_discount_group = kv.get('company discount group', '') or ''
                    except requests.HTTPError:
                        # Laat leeg bij fout, ga verder
                        pass

                row = {
                    'id': cid,
                    'companyType': ctype or '',
                    'name': (info.get('name') or '').strip(),
                    'description': (info.get('description') or '').strip(),
                    'distributor': distributor_name,
                    'distributorId': dist_id_for_path,
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
                    # CustomObject kolommen
                    'currency': currency,
                    'customer price group': customer_price_group,
                    'company discount group': company_discount_group,
                }
                data_rows.append(row)

        # 5) Kolomvolgorde identiek houden
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
            'currency',
            'customer price group',
            'company discount group',
        ]

        df = pd.DataFrame(data_rows, columns=columns)

        # 6) Excel in-memory
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(output.getbuffer())

        return output  # succes -> BytesIO
    except Exception as e:
        return None, f"Onverwachte fout: {str(e)}"
