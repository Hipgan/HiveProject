import requests
import json

def bulk_upsert(manufacturer_id, client_id, client_secret, user_json):
    try:
        user_obj = json.loads(user_json)
        item_id = user_obj.get('hiveCPQId') or user_obj.get('parent_dealerId')
        if not item_id:
            return "Fout: Geen hiveCPQId of parent_dealerId in JSON!"
        custom_object_type = f"distributor-{user_obj.get('parent_dealerId', '')}"

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

        token_response = requests.post(token_url, headers=token_headers, json=token_payload)
        if token_response.status_code != 200:
            return "Token error: " + token_response.text

        access_token = token_response.json()["access_token"]

        key_values = []
        for key, value in user_obj.items():
            key_values.append({
                "key": key,
                "value": value,
                "dataType": "STRING"
            })

        custom_object_body = {
            "customObjects": [
                {
                    "itemId": item_id,
                    "objectKey": item_id,
                    "keyValues": key_values
                }
            ]
        }

        api_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/customObjects/{custom_object_type}/bulkUpsert"
        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        api_response = requests.post(api_url, headers=api_headers, json=custom_object_body)
        try:
            return json.dumps(api_response.json(), indent=2)
        except Exception:
            return api_response.text
    except Exception as e:
        return "Onverwachte fout: " + str(e)
