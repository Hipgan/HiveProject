import requests
import csv
import io

def get_all_project_segments_csv(manufacturer_id, client_id, client_secret):
    try:
        # 1. Token ophalen
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

        # 2. Data ophalen
        data_url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/projectSegments?pageSize=10000"
        data_headers = {"Authorization": f"Bearer {access_token}"}
        data_resp = requests.get(data_url, headers=data_headers)
        data_resp.raise_for_status()
        segments = data_resp.json()

        # 3. Items uit de lijst halen
        if isinstance(segments, dict) and "items" in segments:
            segments = segments["items"]

        # 4. CSV schrijven (naar in-memory string)
        output = io.StringIO()
        fieldnames = [
            'root.id',  # Nieuw: rootobject ID
            'project.id', 'project.name', 'listPrice', 'purchasePrice', 'subDistributorPurchasePrice', 'salesPrice',
            'currency', 'orderStatus', 'status', 'projectSegmentItems'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for seg in segments:
            order = seg.get('order', {})
            price = seg.get('price', {})
            project = seg.get('project', {})
            segment_items = seg.get('projectSegmentItems', [])

            writer.writerow({
                'root.id': seg.get('id', ''),  # Vul het rootobject ID in
                'project.id': project.get('id', ''),
                'project.name': project.get('name', ''),
                'listPrice': price.get('listPrice', ''),
                'purchasePrice': price.get('purchasePrice', ''),
                'subDistributorPurchasePrice': price.get('subDistributorPurchasePrice', ''),
                'salesPrice': price.get('salesPrice', ''),
                'currency': price.get('currency', ''),
                'orderStatus': order.get('orderStatus', ''),
                'status': seg.get('status', ''),
                'projectSegmentItems': "; ".join(
                    item.get('id', '') for item in segment_items
                )
            })
        return output.getvalue()
    except Exception as e:
        return None, f"Onverwachte fout: {str(e)}"
