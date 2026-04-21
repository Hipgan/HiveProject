import requests
import pandas as pd
import re


def verwerk_subdistributeur(df, row_number, manufacturer_id, client_id, client_secret):
    log = []

    def l(msg):
        log.append(str(msg))

    LANGUAGE_MAP = {
        "Deutsch": "de",
        "German": "de",
        "Nederlands": "nl",
        "Dutch": "nl",
        "English": "en",
        "Français": "fr",
        "French": "fr",
        "Español": "es",
        "Spanish": "es"
    }

    COUNTRY_MAP = {
        "Belgium": "BE",
        "Germany": "DE",
        "The Netherlands": "NL",
        "Netherlands": "NL",
        "France": "FR",
        "Spain": "ES",
        "United Kingdom": "GB",
        "Morocco": "MA",
        "Marocco": "MA"
    }

    def get_distributor_data(manufacturer_id):
        if manufacturer_id == "MyAquadeck":
            return {
                "Golden Coast": {
                    "id": "ef73acdbda854f5485691f38329b306f",
                    "email": "swimmer@goldenc.com"
                },
                "Pomaz": {
                    "id": "5d5b62fa8dd94e3c9009929f2682f331",
                    "email": "aquadeck@pomaz.nl"
                },
                "PPG BE": {
                    "id": "329c8d4389704462ad43e1748c5f34d3",
                    "email": "info@polletpoolgroup.com"
                }
            }
        elif manufacturer_id == "aquadeck_staging":
            return {
                "Golden Coast": {
                    "id": "5363bfc79e5f42749bee36216f6e76e4",
                    "email": "swimmer@goldenc.com"
                },
                "Pomaz": {
                    "id": "075e802cf3e64ee680f20a63d2cee489",
                    "email": "aquadeck@pomaz.nl"
                },
                "PPG BE": {
                    "id": "1fd05cd86ca34668bfa3dd3d69618239",
                    "email": "info@polletpoolgroup.com"
                }
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

        if re.match(r"^\d+\.0$", waarde):
            waarde = str(int(float(waarde)))

        match = re.match(r"^(\d{4})([A-Z]{2})$", waarde.replace(" ", "").upper())
        return f"{match.group(1)} {match.group(2)}" if match else waarde

    def extract_company_id_from_url(url):
        match = re.search(r"companies/([a-f0-9]{32})", str(url))
        return match.group(1) if match else None

    def extract_group_code(value):
        if not value:
            return ""

        value = str(value).strip()
        match = re.match(r"^([A-Za-z]+[0-9]+)", value)
        return match.group(1) if match else value

    def unique_non_empty(values):
        result = []
        seen = set()

        for item in values:
            cleaned = str(item).strip()
            if not cleaned:
                continue

            lowered = cleaned.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            result.append(cleaned)

        return result

    def get_access_token(client_id, client_secret):
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
            raise RuntimeError(f"Token ophalen mislukt: {token_resp.text}")

        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise RuntimeError("Geen access_token ontvangen.")

        return access_token

    def get_company_payload_for_update(api_headers, manufacturer_id, company_id):
        """
        Haalt de huidige company op uit HiveCPQ en bouwt hiervan een veilige PUT-payload.
        Zo vermijden we dat velden leeg worden door een onvolledige of fout gevormde body.
        """
        resp = requests.get(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}",
            headers=api_headers
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Company ophalen mislukt: {resp.text}")

        company = resp.json()

        payload = {
            "info": company.get("info") or {},
            "productStore": company.get("productStore") or {"enabled": False},
            "subDistributorSettings": {}
        }

        # subDistributorSettings veilig opbouwen
        sub_settings = company.get("subDistributorSettings") or {}

        # distributorId kan in sommige responses als object-link terugkomen
        distributor_value = None
        if isinstance(sub_settings.get("distributor"), dict):
            distributor_value = sub_settings["distributor"].get("id")
        elif sub_settings.get("distributorId"):
            distributor_value = sub_settings.get("distributorId")

        if distributor_value:
            payload["subDistributorSettings"]["distributorId"] = distributor_value

        # Als er al andere subdistributorvelden bestaan, behouden we die waar mogelijk
        for key, value in sub_settings.items():
            if key not in ["distributor", "distributorId", "orderEmails"]:
                payload["subDistributorSettings"][key] = value

        return payload

    try:
        row = df.iloc[row_number]

        distributor_data = get_distributor_data(manufacturer_id)
        distributor_name = val("Distributor", row)
        distributor = distributor_data.get(distributor_name)

        if not distributor:
            return f"❌ Distributeur '{distributor_name}' is niet gekend."

        distributor_id = distributor["id"]
        distributor_email = distributor["email"]

        subdistributor_name = val("Company Name of subdistributor (Pool Builder)", row)
        if not subdistributor_name:
            return "❌ Geen subdistributeurnaam gevonden."

        subdistributor_email = val(
            "Email address of the company (please provide ONLY 1 mail-address)",
            row
        )

        language = LANGUAGE_MAP.get(val("Preferred Language", row), "en")

        company_exists = (
            val(
                "Does the subdistributor already exist in Hive (created by Aquadeck sales)?",
                row
            ).lower() == "yes"
        )

        if company_exists:
            url = val("Please add URL from subdistributor underneath", row)
            company_id = extract_company_id_from_url(url)

            if not company_id:
                return "❌ Geen geldige URL voor bestaande subdistributeur."

            method = "PUT"
            l(f"ℹ️ Bestaande subdistributeur gedetecteerd. Company ID: {company_id}")
        else:
            company_id = None
            method = "POST"
            l("ℹ️ Nieuwe subdistributeur zal aangemaakt worden.")

        access_token = get_access_token(client_id, client_secret)

        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        country_code = COUNTRY_MAP.get(val("Company Address: Country", row))
        if not country_code:
            return "❌ Ongeldige country code voor company address."

        company_address = {
            "addressLine1": val("Company Address: Address line 1 (e.g. street + nbr)", row),
            "addressLine2": val("Company Address: Address line 2", row),
            "city": val("Company Address: City", row),
            "postalCode": val_postcode(
                "Company Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))",
                row
            ),
            "countryIso": country_code
        }

        company_info = {
            "address": company_address,
            "name": subdistributor_name,
            "description": subdistributor_name,
            "vatNumber": val("VAT Number", row),
            "email": subdistributor_email,
            "telephone": val(
                "Phone Number (please use ISO format with country code - e.g. +31 495 430 317)",
                row
            ),
            "preferredLanguage": language
        }

        create_or_update_payload = {
            "info": company_info,
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
                json=create_or_update_payload
            )

            if resp.status_code != 201:
                return f"❌ Fout bij aanmaken: {resp.text}"

            response_json = resp.json()
            company_id = response_json.get("id")
            if not company_id:
                return "❌ Company aangemaakt, maar geen company_id teruggekregen."

            l(f"✅ Subdistributeur aangemaakt. Company ID: {company_id}")

        else:
            resp = requests.put(
                f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}",
                headers=api_headers,
                json=create_or_update_payload
            )

            if resp.status_code != 204:
                return f"❌ Fout bij bijwerken: {resp.text}"

            l(f"✅ Subdistributeur bijgewerkt. Company ID: {company_id}")

        invoice_payload = {
            "type": "INVOICE",
            "address": company_address,
            "companyName": subdistributor_name,
            "contactPerson": val("Delivery Address: Contact Person", row),
            "contactPhone": company_info["telephone"],
            "email": company_info["email"],
            "canChangeAddress": False,
            "canChangeAddressOnPlaceOrder": False,
            "vatNumber": company_info["vatNumber"]
        }

        resp = requests.post(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}/defaultAddresses",
            headers=api_headers,
            json=invoice_payload
        )

        if resp.status_code != 201:
            return f"❌ Fout bij toevoegen INVOICE adres: {resp.text}"

        l("✅ INVOICE adres toegevoegd.")

        if val("Delivery Address: Different than Company Address?", row).lower() == "yes":
            delivery_country_code = COUNTRY_MAP.get(val("Delivery Address: Country", row))
            if not delivery_country_code:
                return "❌ Geen geldige country code voor delivery adres."

            delivery_address = {
                "addressLine1": val("Delivery Address: Address line 1 (e.g. street + nbr)", row),
                "addressLine2": val("Delivery Address: Address line 2", row),
                "city": val("Delivery Address: City", row),
                "postalCode": val_postcode(
                    "Delivery Address: Postal Code (e.g. 9999 AA (for NL) or 9999 (for BE))",
                    row
                ),
                "countryIso": delivery_country_code
            }

            delivery_company = val("Delivery Address: Name of address", row)
            delivery_email = val(
                "Delivery Address: Email address to be used in delivery-communication (please provide ONLY 1 mail-address)",
                row
            )
            delivery_phone = val(
                "Delivery Address: Contact Phone (please use ISO format with country code - e.g. +31 495 430 317)",
                row
            )
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
            "vatNumber": (
                ""
                if delivery_company != invoice_payload["companyName"]
                else invoice_payload["vatNumber"]
            )
        }

        resp = requests.post(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}/defaultAddresses",
            headers=api_headers,
            json=delivery_payload
        )

        if resp.status_code != 201:
            return f"❌ Fout bij toevoegen DELIVERY adres: {resp.text}"

        l("✅ DELIVERY adres toegevoegd.")

        discount_group = extract_group_code(
            val(f"Discount Group for subdistributor ({distributor_name})", row)
        )

        price_group = extract_group_code(
            val("Price Group for subdistributor", row)
        )

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
                        {"key": "name", "value": company_info["name"], "dataType": "STRING"},
                        {"key": "description", "value": company_info["description"], "dataType": "STRING"},
                        {"key": "company discount group", "value": discount_group, "dataType": "STRING"}
                    ]
                }
            ]
        }

        resp = requests.post(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/customObjects/distributor-{distributor_id}/bulkUpsert",
            headers=api_headers,
            json=bulk_payload
        )

        if resp.status_code != 200:
            return f"❌ Fout bij bulk upsert: {resp.text}"

        l("✅ Bulk upsert uitgevoerd.")

        # Finale stap:
        # haal de actuele company op uit Hive en update alleen orderEmails daarop
        order_emails = unique_non_empty([
            distributor_email,
            subdistributor_email
        ])

        final_payload = get_company_payload_for_update(
            api_headers=api_headers,
            manufacturer_id=manufacturer_id,
            company_id=company_id
        )

        # Veiligheid: forceer distributorId indien niet teruggekomen in GET-payload
        final_payload.setdefault("subDistributorSettings", {})
        final_payload["subDistributorSettings"]["distributorId"] = (
            final_payload["subDistributorSettings"].get("distributorId") or distributor_id
        )
        final_payload["subDistributorSettings"]["orderEmails"] = order_emails

        resp = requests.put(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/companies/{company_id}",
            headers=api_headers,
            json=final_payload
        )

        if resp.status_code != 204:
            return f"❌ Fout bij invullen orderEmails: {resp.text}"

        l(f"✅ orderEmails ingevuld: {order_emails}")

        reset_resp = requests.post(
            f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/resetCustomObjectUpdateTimestamp",
            headers=api_headers
        )

        if reset_resp.status_code != 204:
            return f"⚠️ Reset timestamp faalde: {reset_resp.text}"

        l("✅ Timestamp reset uitgevoerd.")
        l("✅ Voltooid zonder fouten.")

        return "\n".join(log)

    except Exception as e:
        return f"❌ Onverwachte fout: {str(e)}"
