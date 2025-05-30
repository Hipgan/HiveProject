import requests

def reset_custom_object_cache(manufacturer_id, client_id, client_secret):
    # 1. Haal token op
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

    try:
        token_resp = requests.post(token_url, json=token_payload, headers=token_headers)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
    except Exception as e:
        return f"Fout bij ophalen token: {e}"

    # 2. Voer POST uit zonder body!
    api_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/resetCustomObjectUpdateTimestamp"
    api_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(api_url, headers=api_headers)
        response.raise_for_status()
        # Probeer json, anders plain tekst, anders alleen status
        try:
            return f"Status: {response.status_code}\n{response.json()}"
        except Exception:
            if response.status_code == 200 and not response.text:
                return "Reset succesvol uitgevoerd! (status 200, geen response body)."
            return f"Status: {response.status_code}\nRaw response: {response.text}"
    except Exception as e:
        try:
            return f"Fout bij uitvoeren API-call: {e}\nRaw response: {response.text}"
        except:
            return f"Fout bij uitvoeren API-call: {e}"
