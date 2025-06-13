import requests
import csv
import io

def get_all_companies_csv(manufacturer_id, client_id, client_secret):
    try:
        # 1. Ophalen van de token
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

        # 2. API-call om bedrijven op te halen
        data_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies?pageSize=1000"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(data_url, headers=headers)
        response.raise_for_status()
        companies = response.json()

        # 3. Als de respons een dict is met 'items'
        if isinstance(companies, dict) and "items" in companies:
            companies = companies["items"]

        # 4. Exporteren naar CSV (in memory!)
        output = io.StringIO()
        fieldnames = [
            'id', 'companyType', 'name', 'description', 'telephone', 'vatNumber',
            'email', 'websiteUrl', 'preferredLanguage',
            'addressLine1', 'addressLine2', 'city', 'postalCode', 'countryIso',
            'distributor'  # <-- nieuwe kolom
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for company in companies:
            info = company.get('info', {})
            address = info.get('address', {})

            # Default leeg, tenzij sub-distributeur met parent distributor
            distributor_name = ''
            if company.get('companyType', '') == 'SUB_DISTRIBUTOR':
                sub_settings = company.get('subDistributorSettings', {})
                distributor = sub_settings.get('distributor', {})
                distributor_name = distributor.get('name', '')

            writer.writerow({
                'id': company.get('id', ''),
                'companyType': company.get('companyType', ''),
                'name': info.get('name', ''),
                'description': info.get('description', ''),
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
                'distributor': distributor_name  # Vul in, blijft leeg bij distributor
            })
        return output.getvalue()
    except Exception as e:
        return None, f"Onverwachte fout: {str(e)}"

