import requests
import json
import pandas as pd
import re

def get_country_code(country_str):
    COUNTRY_MAP = {
        "Belgium": "BE",
        "Germany": "DE",
        "The Netherlands": "NL",
        "Netherlands": "NL",
        "France": "FR",
        "Spain": "ES"
    }
    if pd.isna(country_str) or str(country_str).strip() == "":
        return None
    return COUNTRY_MAP.get(str(country_str).strip(), None)

def extract_company_id_from_url(url):
    match = re.search(r"companies/([a-f0-9]{32})", url)
    return match.group(1) if match else None

def strip_before_parenthesis(value):
    return value.split(" (")[0].strip() if " (" in value else value.strip()

def val(name, row):
    try:
        waarde = row.get(name)
        if pd.isna(waarde):
            return ""
        if isinstance(waarde, float) and waarde.is_integer():
            return str(int(waarde))
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

def verwerk_distributeur(df, row_number, manufacturer_id, client_id, client_secret):
    log = []
    def l(msg):
        log.append(msg)

    try:
        row = df.iloc[row_number]

        # Token ophalen
        l("🔐 Token ophalen...")
        token_response = requests.post(
            "https://ebusinesscloud.eu.auth0.com/oauth/token",
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": "https://ebusinesscloud.eu.auth0.com/api/v2/"
            }
        )
        if token_response.status_code != 200:
            return f"❌ Token ophalen mislukt: {token_response.text}"
        access_token = token_response.json()["access_token"]
        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        url = val("Link of the distributor as known in Hive (copy link from your URL and paste it in the response field beneath)", row)
        company_id = extract_company_id_from_url(url)
        if not company_id:
            return "❌ Ongeldige Hive-URL voor company ID."

        l(f"🏷️ Verwerkte company ID: {company_id}")

        basic_data_ready = val("Has the basic data been added in MyAquadeck (address info, delivery address,...)?", row).strip().lower() == "yes, we only need the price information to be added".lower()
        if not basic_data_ready:
            l("📬 INVOICE adres toevoegen...")
            invoice_country = get_country_code(val("Company Address: Country", row))
            if not invoice_country:
                return "❌ Geen geldige landcode voor invoice-adres."

            invoice_payload = {
                "type": "INVOICE",
                "address": {
                    "addressLine1": val("Company Address: Address line 1 (e.g. street + nbr)", row),
                    "addressLine2": val("Company Address: Address line 2", row),
                    "city": val("Company Address: City", row),
                    "postalCode": val_postcode("Company Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))", row),
                    "countryIso": invoice_country
                },
                "vatNumber": val("VAT Number", row),
                "contactPhone": val("Phone Number (please use ISO format with country code - e.g. +31 495 430 317)", row),
                "contactPerson": val("Delivery Address: Contact Person", row),
                "email": val("Email address of the company (please provide ONLY 1 mail-address)", row),
                "canChangeAddress": False,
                "canChangeAddressOnPlaceOrder": True,
                "companyName": val("Company Name of Distributor", row)
            }

            resp = requests.post(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}/defaultAddresses",
                headers=api_headers,
                json=invoice_payload
            )
            l(f"📥 INVOICE status: {resp.status_code}")
            if resp.status_code != 201:
                return f"❌ Fout bij toevoegen invoice-adres: {resp.text}"

            l("🚚 DELIVERY adres toevoegen...")
            delivery_differs = val("Delivery Address: Different than Company Address?", row).strip().lower() != "no, same as company address"
            if delivery_differs:
                delivery_country = get_country_code(val("Delivery Address: Country", row))
                if not delivery_country:
                    return "❌ Geen geldige landcode voor delivery-adres."
                delivery_address = {
                    "addressLine1": val("Delivery Address: Address line 1 (e.g. street + nbr)", row),
                    "addressLine2": val("Delivery Address: Address line 2", row),
                    "city": val("Delivery Address: City", row),
                    "postalCode": val_postcode("Delivery Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))", row),
                    "countryIso": delivery_country
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
                "canChangeAddressOnPlaceOrder": True
            }

            resp = requests.post(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}/defaultAddresses",
                headers=api_headers,
                json=delivery_payload
            )
            l(f"📦 DELIVERY status: {resp.status_code}")
            if resp.status_code != 201:
                return f"❌ Fout bij toevoegen delivery-adres: {resp.text}"

        l("🧩 Custom object toevoegen...")
        price_group_stripped = strip_before_parenthesis(val("Price Group for Distributor", row))
        discount_group_stripped = strip_before_parenthesis(val("Discount Group for Distributor (Aquadeck)", row))

        bulk_payload = {
            "customObjects": [
                {
                    "itemId": company_id,
                    "objectKey": company_id,
                    "keyValues": [
                        {"key": "currency", "value": val("Currency", row), "dataType": "STRING"},
                        {"key": "hiveCPQId", "value": company_id, "dataType": "STRING"},
                        {"key": "parent_dealerId", "value": company_id, "dataType": "STRING"},
                        {"key": "customer price group", "value": price_group_stripped, "dataType": "STRING"},
                        {"key": "name", "value": val("Company Name of Distributor", row), "dataType": "STRING"},
                        {"key": "description", "value": val("Company Name of Distributor", row), "dataType": "STRING"},
                        {"key": "company discount group", "value": discount_group_stripped, "dataType": "STRING"}
                    ]
                }
            ]
        }

        resp = requests.post(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/customObjects/distributor%20-{company_id}/bulkUpsert",
            headers=api_headers,
            json=bulk_payload
        )
        l(f"🔁 bulkUpsert status: {resp.status_code}")
        if resp.status_code != 200:
            return f"❌ Fout bij bulk upsert: {resp.text}"

        l("♻️ Reset custom object timestamp...")
        reset_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/resetCustomObjectUpdateTimestamp"
        reset_resp = requests.post(reset_url, headers=api_headers)
        l(f"🔁 Reset status: {reset_resp.status_code}")
        if reset_resp.status_code != 200:
            return f"❌ Fout bij reset timestamp: {reset_resp.text}"

        l("✅ Distributeurverwerking voltooid zonder fouten.")
        return "\\n".join(log)

    except Exception as e:
        return f"❌ Onverwachte fout: {str(e)}"
