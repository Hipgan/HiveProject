import requests
import csv
import io

def get_all_project_segment_items_csv(manufacturer_id, client_id, client_secret):
    try:
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
        token_resp = requests.post(token_url, json=token_payload, headers=token_headers)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        data_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/projectSegmentItems?pageSize=10000"
        data_headers = {"Authorization": f"Bearer {access_token}"}
        data_resp = requests.get(data_url, headers=data_headers)
        data_resp.raise_for_status()
        items = data_resp.json()
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        output = io.StringIO()
        fieldnames = [
            'id', 'name', 'list_price', 'discount', 'purchase_price',
            'sales_price', 'currency', 'markup', 'status'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow({
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'list_price': item.get('price', {}).get('listPrice', ''),
                'discount': item.get('price', {}).get('discount', ''),
                'purchase_price': item.get('price', {}).get('purchasePrice', ''),
                'sales_price': item.get('price', {}).get('salesPrice', ''),
                'currency': item.get('price', {}).get('currency', ''),
                'markup': item.get('price', {}).get('markup', ''),
                'status': item.get('projectSegment', {}).get('orderStatus', ''),
            })
        return output.getvalue()
    except Exception as e:
        return None, f"Onverwachte fout: {str(e)}"
