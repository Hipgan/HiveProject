import requests
import json

def update_units_of_components(manufacturer_id, client_id, client_secret, article_codes_input, unit_code_input, version_input):
    try:
        # 1. Token ophalen
        token_url = "https://ebusinesscloud.eu.auth0.com/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_name": "API USER",
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": "https://ebusinesscloud.eu.auth0.com/api/v2/",
            "domain": "https://ebusinesscloud.eu.auth0.com"
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(token_url, json=payload, headers=headers)
        resp.raise_for_status()
        token = resp.json()["access_token"]

        # 2. Artikelnummers ophalen
        article_codes = [code.strip() for code in article_codes_input.split(",") if code.strip()]
        unit_code = unit_code_input.strip()
        version = version_input.strip()

        # 3. Haal alle componenten op
        comp_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/containers/main/versions/{version}/components?pageSize=3000"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(comp_url, headers=headers)
        resp.raise_for_status()
        components = resp.json().get("items", [])

        # 4. Per code updaten
        results = []
        for code in article_codes:
            found = next((c for c in components if c.get("articleCode") == code), None)
            if not found:
                results.append({"articleCode": code, "status": "Niet gevonden"})
                continue

            root_id = found["id"]
            name = found.get("name", "")
            body = {
                "names": [
                    {
                        "languageCode": "en",
                        "translation": name
                    }
                ],
                "extensions": {
                    "quantity": {
                        "quantities": [
                            {
                                "unitCode": unit_code,
                                "minimum": 1,
                                "step": 1
                            }
                        ]
                    }
                },
                "articleCode": code
            }

            put_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/containers/main/versions/{version}/components/{root_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            r = requests.put(put_url, data=json.dumps(body), headers=headers)
            result_status = f"{r.status_code} - {r.text}" if r.status_code != 200 else "OK"
            results.append({"articleCode": code, "status": result_status})

        return results

    except Exception as e:
        return [{"error": str(e)}]
