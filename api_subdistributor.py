import os

import requests
import json
import pandas as pd
import re

def verwerk_subdistributeur(df, row_number, manufacturer_id, client_id, client_secret):
    log = []
    def l(msg):
        log.append(str(msg))

    LANGUAGE_MAP = {
        "Deutsch": "de", "German": "de", "Nederlands": "nl", "Dutch": "nl",
        "English": "en", "Français": "fr", "French": "fr", "Español": "es", "Spanish": "es"
    }
    COUNTRY_MAP = {
        "Belgium": "BE", "Germany": "DE", "The Netherlands": "NL", "Netherlands": "NL",
        "France": "FR", "Spain": "ES", "United Kingdom": "GB"
    }

    def get_distributor_ids(manufacturer_id):
        if manufacturer_id == "MyAquadeck":
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
            raise ValueError(f"Onbekende MANUFACTURER_ID: {manufacturer_id}")

    def val(name, row):
        v = row.get(name)
        if pd.isna(v) or str(v).strip().lower() == "nan":
            return ""
        return str(v).strip()

    def val_postcode(name, row):
        waarde = val(name, row)
        if re.match(r"^\\d+\\.0$", waarde):
            waarde = str(int(float(waarde)))
        match = re.match(r"^(\\d{4})([A-Z]{2})$", waarde.replace(" ", "").upper())
        return f"{match.group(1)} {match.group(2)}" if match else waarde

    def extract_company_id_from_url(url):
        match = re.search(r"companies/([a-f0-9]{32})", url)
        return match.group(1) if match else None

    def strip_before_parenthesis(value):
        return value.split(" (")[0].strip() if " (" in value else value.strip()

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
                return "❌ Geen geldige URL voor bestaande subdistributeur."
            method = "PUT"
        else:
            method = "POST"

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
            return "❌ Ongeldige country code"

        payload = {
            "info": {
                "address": {
                    "addressLine1": val("Company Address: Address line 1 (e.g. street + nbr)", row),
                    "addressLine2": val("Company Address: Address line 2", row),
                    "city": val("Company Address: City", row),
                    "postalCode": val_postcode("Company Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))", row),
                    "countryIso": country_code
                },
                "name": val("Company Name of subdistributor (Pool Builder)", row),
                "description": val("Company Name of subdistributor (Pool Builder)", row),
                "vatNumber": val("VAT Number", row),
                "email": val("Email address of the company (please provide ONLY 1 mail-address)", row),
                "telephone": val("Phone Number (please use ISO format with country code - e.g. +31 495 430 317)", row),
                "preferredLanguage": language
            },
            "productStore": { "enabled": False },
            "subDistributorSettings": { "distributorId": distributor_id }
        }

        if method == "POST":
            resp = requests.post(f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies", headers=api_headers, json=payload)
            if resp.status_code != 201:
                return f"❌ Fout bij aanmaken: {resp.text}"
            company_id = resp.json().get("id")
        else:
            resp = requests.put(f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}", headers=api_headers, json=payload)
            if resp.status_code != 204:
                return f"❌ Fout bij bijwerken: {resp.text}"

        invoice_payload = {
            "type": "INVOICE",
            "address": payload["info"]["address"],
            "companyName": payload["info"]["name"],
            "contactPerson": val("Delivery Address: Contact Person", row),
            "contactPhone": payload["info"]["telephone"],
            "email": payload["info"]["email"],
            "canChangeAddress": False,
            "canChangeAddressOnPlaceOrder": False,
            "vatNumber": payload["info"]["vatNumber"]
        }
        resp = requests.post(f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}/defaultAddresses", headers=api_headers, json=invoice_payload)
        if resp.status_code != 201:
            return f"❌ Fout bij toevoegen INVOICE adres: {resp.text}"

        if val("Delivery Address: Different than Company Address?", row).lower() == "yes":
            delivery_country_code = COUNTRY_MAP.get(val("Delivery Address: Country", row))
            if not delivery_country_code:
                return "❌ Geen geldige country code voor delivery adres."
            delivery_address = {
                "addressLine1": val("Delivery Address: Address line 1 (e.g. street + nbr)", row),
                "addressLine2": val("Delivery Address: Address line 2", row),
                "city": val("Delivery Address: City", row),
                "postalCode": val_postcode("Delivery Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))", row),
                "countryIso": delivery_country_code
            }
            delivery_company = val("Delivery Address: Name of address", row)
            delivery_email = val("Delivery Address: Email address to be used in delivery-communication (please provide ONLY 1 mail-address)", row)
            delivery_phone = val("Delivery Address: Contact Phone (please use ISO format with country code - e.g. +31 495 430 317)", row)
        else:
            delivery_address = invoice_payload["address"]
            delivery_company = invoice_payload["companyName"]
            delivery_email = invoice_payload["email"]
            delivery_phone = invoice_payload["contactPhone"]

        delivery_payload = {
            "type": "DELIVERY",
            "address": delivery_address,
            "companyName": delivery_company,
            "contactPerson": val("Delivery Address: Contact Person", row),
            "contactPhone": delivery_phone,
            "email": delivery_email,
            "canChangeAddress": False,
            "canChangeAddressOnPlaceOrder": True,
            "vatNumber": "" if delivery_company != invoice_payload["companyName"] else invoice_payload["vatNumber"]
        }
        resp = requests.post(f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}/defaultAddresses", headers=api_headers, json=delivery_payload)
        if resp.status_code != 201:
            return f"❌ Fout bij toevoegen DELIVERY adres: {resp.text}"

        discount_group = strip_before_parenthesis(val(f"Discount Group for subdistributor ({distributor_name})", row))
        price_group = strip_before_parenthesis(val("Price Group for subdistributor", row))
        bulk_payload = {
            "customObjects": [
                {
                    "itemId": company_id,
                    "objectKey": company_id,
                    "keyValues": [
                        {"key": "currency", "value": val("Currency", row), "dataType": "STRING"},
                        {"key": "hiveCPQId", "value": company_id, "dataType": "STRING"},
                        {"key": "parent_dealerId", "value": distributor_id, "dataType": "STRING"},
                        {"key": "customer price group", "value": price_group, "dataType": "STRING"},
                        {"key": "name", "value": val("Company Name of subdistributor (Pool Builder)", row), "dataType": "STRING"},
                        {"key": "description", "value": val("Company Name of subdistributor (Pool Builder)", row), "dataType": "STRING"},
                        {"key": "company discount group", "value": discount_group, "dataType": "STRING"}
                    ]
                }
            ]
        }
        resp = requests.post(f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/customObjects/distributor-{distributor_id}/bulkUpsert", headers=api_headers, json=bulk_payload)
        if resp.status_code != 200:
            return f"❌ Fout bij bulk upsert: {resp.text}"

        reset_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/resetCustomObjectUpdateTimestamp"
        reset_resp = requests.post(reset_url, headers=api_headers)
        if reset_resp.status_code != 204:
            return f"⚠️ Reset timestamp faalde: {reset_resp.text}"

        l("✅ Voltooid zonder fouten.")
        return "\\n".join(log)

    except Exception as e:
        return f"❌ Onverwachte fout: {str(e)}"



"/mnt/data/api_subdistributor.py"
