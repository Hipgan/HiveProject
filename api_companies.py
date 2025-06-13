import requests
import pandas as pd
from io import BytesIO

def get_all_companies_excel(manufacturer_id, client_id, client_secret, output_path=None):
    try:
        # 1. Token ophalen
        token_url = "https://ebusinesscloud.eu.auth0.com/oauth/token"
        token_payload = {
            "grant_type": "client_credentials",
            "client_name": "API USER",
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": "https://ebusinesscloud.eu.auth0.com/api/v2/",
            "domain": "https://ebusinesscloud.eu.auth0.com"
        }
        token_headers = {"Content-Type": "application/json"}
        response = requests.post(token_url, json=token_payload, headers=token_headers)
        response.raise_for_status()
        access_token = response.json()["access_token"]

        # 2. Bedrijven ophalen
        data_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies?pageSize=1000"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(data_url, headers=headers)
        response.raise_for_status()
        companies = response.json()

        # 3. "items" uitpakken indien nodig
        if isinstance(companies, dict) and "items" in companies:
            companies = companies["items"]

        # 4. Data structureren
        data = []
        for company in companies:
            info = company.get('info', {})
            address = info.get('address', {})

            distributor_name = ''
            if company.get('companyType', '') == 'SUB_DISTRIBUTOR':
                sub_settings = company.get('subDistributorSettings', {})
                distributor = sub_settings.get('distributor', {})
                distributor_name = distributor.get('name', '')

            row = {
                'id': company.get('id', ''),
                'companyType': company.get('companyType', ''),
                'name': info.get('name', ''),
                'description': info.get('description', ''),
                'distributor': distributor_name,  # Vijfde kolom!
                'telephone': info.get('telephone', ''),
                'vatNumber': info.get('vatNumber', ''),
                'email': info.get('email', ''),
                'websiteUrl': info.get('websiteUrl', ''),
                'preferredLanguage': info.get('preferredLanguage', ''),
                'addressLine1': address.get('addressLine1', ''),
                'addressLine2': address.get('addressLine2', ''),
                'city': address.get('city', ''),
                'postalCode': address.get('postalCode', ''),
                'countryIso': address.get('countryIso', ''),
            }
            data.append(row)

        # 5. Kolomvolgorde
        columns = [
            'id',
            'companyType',
            'name',
            'description',
            'distributor',          # Vijfde kolom
            'telephone',
            'vatNumber',
            'email',
            'websiteUrl',
            'preferredLanguage',
            'addressLine1',
            'addressLine2',
            'city',
            'postalCode',
            'countryIso'
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

        return output
    except Exception as e:
        return None, f"Onverwachte fout: {str(e)}"
