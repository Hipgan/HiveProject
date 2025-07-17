import requests
import pandas as pd
import re
import json

def verwerk_subdistributeur(df, row_number, manufacturer_id, client_id, client_secret):
    log = []
    def l(msg):
        log.append(msg)

    LANGUAGE_MAP = {
        "Deutsch": "de", "German": "de",
        "Nederlands": "nl", "Dutch": "nl",
        "English": "en", "Français": "fr",
        "French": "fr", "Español": "es",
        "Spanish": "es"
    }

    COUNTRY_MAP = {
        "Belgium": "BE", "Germany": "DE",
        "The Netherlands": "NL", "Netherlands": "NL",
        "France": "FR", "Spain": "ES"
    }

    def get_distributor_ids(mid):
        if mid == "myAquadeck":
            return {
                "Golden Coast": "ef73acdbda854f5485691f38329b306f",
                "Pomaz": "5d5b62fa8dd94e3c9009929f2682f331",
                "PPG BE": "329c8d4389704462ad43e1748c5f34d3"
            }
        elif mid == "aquadeck_staging":
            return {
                "Golden Coast": "5363bfc79e5f42749bee36216f6e76e4",
                "Pomaz": "075e802cf3e64ee680f20a63d2cee489",
                "PPG BE": "1fd05cd86ca34668bfa3dd3d69618239"
            }
        else:
            raise ValueError(f"Onbekende MANUFACTURER_ID: {mid}")

    def val(name, row):
        try:
            v = row.get(name)
            if pd.isna(v):
                return ""
            v = str(v).strip()
            if v.lower() == "nan":
                return ""
            return v
        except Exception:
            return ""

    def extract_company_id_from_url(url):
        match = re.search(r"companies/([a-f0-9]{32})", url)
        return match.group(1) if match else None

    try:
        row = df.iloc[row_number]
        distributor_ids = get_distributor_ids(manufacturer_id)
        distributor_name = val("Distributor", row)
        distributor_id = distributor_ids.get(distributor_name)
        if not distributor_id:
            return f"❌ Distributeur '{distributor_name}' is niet gekend."

        language = LANGUAGE_MAP.get(val("Preferred Language", row), "en")
        company_exists = val("Does the subdistributor already exist in Hive (created by Aquadeck sales)?", row).lower() == "yes"
        if company_exists:
            url = val("Please add URL from subdistributor underneath", row)
            company_id = extract_company_id_from_url(url)
            if not company_id:
                return "❌ Ongeldige URL gevonden."
            method = "PUT"
        else:
            method = "POST"

        # Token ophalen
        l("🔐 Token ophalen...")
        token_resp = requests.post(
            "https://ebusinesscloud.eu.auth0.com/oauth/token",
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": "https://ebusinesscloud.eu.auth0.com/api/v2/"
            }
        )
        if token_resp.status_code != 200:
            return f"❌ Token ophalen mislukt: {token_resp.text}"
        access_token = token_resp.json()["access_token"]
        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        country_code = COUNTRY_MAP.get(val("Company Address: Country", row))
        if not country_code:
            return "❌ Geen geldige landcode voor company-adres."

        payload = {
            "info": {
                "address": {
                    "addressLine1": val("Company Address: Address line 1 (e.g. street + nbr)", row),
                    "addressLine2": val("Company Address: Address line 2", row),
                    "city": val("Company Address: City", row),
                    "postalCode": val("Company Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))", row),
                    "countryIso": country_code
                },
                "name": val("Company Name of subdistributor (Pool Builder)", row),
                "description": val("Company Name of subdistributor (Pool Builder)", row),
                "vatNumber": val("VAT Number", row),
                "email": val("Email address of the company (please provide ONLY 1 mail-address)", row),
                "telephone": val("Phone Number (please use ISO format with country code - e.g. +31 495 430 317)", row),
                "preferredLanguage": language
            },
            "productStore": {
                "enabled": False
            },
            "subDistributorSettings": {
                "distributorId": distributor_id
            }
        }

        if method == "POST":
            l("🏗️ Nieuwe subdistributeur aanmaken...")
            resp = requests.post(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies",
                headers=api_headers,
                json=payload
            )
            if resp.status_code != 201:
                return f"❌ Fout bij aanmaken: {resp.text}"
            company_id = resp.json().get("id")
        else:
            l(f"🔁 Bestaande subdistributeur bijwerken: {company_id}")
            resp = requests.put(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}",
                headers=api_headers,
                json=payload
            )
            if resp.status_code != 204:
                return f"❌ Fout bij update: {resp.text}"

        l(f"✅ Subdistributeur verwerkt: {company_id}")
        return "\\n".join(log)

    except Exception as e:
        return f"❌ Interne fout: {str(e)}"
