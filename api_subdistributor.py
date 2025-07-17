import requests
import json
import pandas as pd
import re

def verwerk_subdistributeur(df, row_number, manufacturer_id, client_id, client_secret):
    log = []
    def l(msg):
        log.append(msg)

    try:
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

        def get_distributor_ids(manufacturer_id):
            if manufacturer_id == "myAquadeck":
                return {
                    "Golden Coast": "ef73acdbda854f5485691f38329b306f",
                    "Pomaz": "5d5b62fa8dd94e3c9009929f2682f331",
                    "PPG BE": "329c8d4389704462ad43e1748c5f34d3"
                }
            elif manufacturer_id == "aquadeck_staging":
                return {
                    "Golden Coast": "5363bfc79e5f42749bee36216f6e76e4",
                    "Pomaz": "075e802cf3e64ee680f20a63d2cee489",
                    "PPG BE": "1fd05cd86ca34668bfa3dd3d69618239"
                }
            else:
                raise Exception(f"Onbekende MANUFACTURER_ID: {manufacturer_id}")

        DISTRIBUTOR_IDS = get_distributor_ids(manufacturer_id)

        def val(name, row):
            try:
                waarde = row.get(name)
                if pd.isna(waarde):
                    return ""
                waarde = str(waarde).strip()
                if waarde.lower() == "nan":
                    return ""
                return waarde
            except Exception:
                return ""

        def val_postcode(name, row):
            waarde = val(name, row)
            if re.match(r"^\\d+\\.0$", waarde):
                waarde = str(int(float(waarde)))
            match = re.match(r"^(\\d{4})([A-Z]{2})$", waarde.replace(" ", "").upper())
            if match:
                return f"{match.group(1)} {match.group(2)}"
            return waarde

        def get_country_code(country_str):
            if pd.isna(country_str) or str(country_str).strip() == "":
                return None
            return COUNTRY_MAP.get(str(country_str).strip(), None)

        def extract_company_id_from_url(url):
            match = re.search(r"companies/([a-f0-9]{32})", url)
            return match.group(1) if match else None

        def strip_before_parenthesis(value):
            return value.split(" (")[0].strip() if " (" in value else value.strip()

        row = df.iloc[row_number]
        distributor_name = val("Distributor", row)
        distributor_id = DISTRIBUTOR_IDS.get(distributor_name)
        if not distributor_id:
            return f"❌ Distributeur '{distributor_name}' is niet gekend."

        language = LANGUAGE_MAP.get(val("Preferred Language", row), "en")

        company_exists = val("Does the subdistributor already exist in Hive (created by Aquadeck sales)?", row).lower() == "yes"
        if company_exists:
            url = val("Please add URL from subdistributor underneath", row)
            company_id = extract_company_id_from_url(url)
            if not company_id:
                return "❌ Geen geldige URL gevonden."
            method = "PUT"
            l(f"🔁 Bestaande subdistributeur updaten: {company_id}")
        else:
            method = "POST"
            l("🏗️ Nieuwe subdistributeur aanmaken...")

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
            return f"❌ Fout bij token ophalen: {token_resp.text}"
        access_token = token_resp.json()["access_token"]
        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        company_country = get_country_code(val("Company Address: Country", row))
        if not company_country:
            return "❌ Geen geldige landcode voor company-adres."

        company_payload = {
            "info": {
                "address": {
                    "addressLine1": val("Company Address: Address line 1 (e.g. street + nbr)", row),
                    "addressLine2": val("Company Address: Address line 2", row),
                    "city": val("Company Address: City", row),
                    "postalCode": val_postcode("Company Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))", row),
                    "countryIso": company_country
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
            resp = requests.post(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies",
                headers=api_headers,
                json=company_payload
            )
            if resp.status_code != 201:
                return f"❌ Kon subdistributeur niet aanmaken: {resp.text}"
            company_id = resp.json().get("id")
        else:
            resp = requests.put(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}",
                headers=api_headers,
                json=company_payload
            )
            if resp.status_code != 204:
                return f"❌ Fout bij update: {resp.text}"

        # Adressen + bulkUpsert + resetTimestamp => later toe te voegen in Streamlit flow
        l(f"✅ Subdistributeurverwerking voltooid: {company_id}")
        return "\\n".join(log)

    except Exception as e:
        return f"❌ Fout tijdens verwerking: {str(e)}"
"""

# Schrijf naar bestand
path = "/mnt/data/api_subdistributor.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(subdistributor_stub)
