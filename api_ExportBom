import requests
import pandas as pd
from io import BytesIO

def get_token(client_id, client_secret):
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
    return resp.json()["access_token"]

def get_project_segment_item(access_token, manufacturer_id, segment_item_id):
    url = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/projectSegmentItems/{segment_item_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_bom_json(access_token, manufacturer_id, configuration_id):
    url = (
        f"https://connect.hivecpq.com/api/v1/manufacturers/"
        f"{manufacturer_id}/configurations/{configuration_id}"
        f"?outputMode=BOM_ONLY&language=en"
    )
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def format_price(val):
    if val is None:
        return "0,00"
    val = float(val)
    return f"{val:.2f}".replace('.', ',')

def has_bomitem_descendants(node):
    for sub in node.get("nodes", []):
        if sub["type"] == "BOM_ITEM":
            return True
        if has_bomitem_descendants(sub):
            return True
    return False

def bom_label_for_level(level):
    if level == 1:
        return "BOM"
    elif level == 2:
        return "SUB_BOM"
    elif level == 3:
        return "SUB_SUB_BOM"
    else:
        return "SUB_" * (level - 2) + "BOM"

def traverse(node, parent, level, project_code, rows):
    for subnode in node.get("nodes", []):
        if subnode["type"] == "BOM_ITEM":
            if has_bomitem_descendants(subnode):
                item_type = bom_label_for_level(level)
            else:
                item_type = "Component"
            aantal = subnode.get("quantity", "")
            if isinstance(aantal, float) and aantal.is_integer():
                aantal = int(aantal)
            price = subnode.get("price", {}) or {}
            list_price = format_price(price.get("listPrice", 0))
            purchase_price = format_price(price.get("purchasePrice", 0))
            rows.append({
                "Level": level,
                "Parent": parent,
                "Project": project_code if level == 0 else "",
                "Component": subnode.get("componentCode", ""),
                "ItemType": item_type,
                "Aantal": aantal,
                "Unit": subnode.get("unit", ""),
                "ListPrice": list_price,
                "PurchasePrice": purchase_price,
            })
            traverse(subnode, subnode.get("componentCode", ""), level + 1, project_code, rows)
        else:
            traverse(subnode, parent, level, project_code, rows)

def bom_json_to_excel_bytes(data):
    project_code = data["configuredProduct"]["code"]
    configuration_code = data.get("configurationCode", "")
    project_display = f"{project_code} : {configuration_code}" if configuration_code else project_code

    rows = [{
        "Level": 0,
        "Parent": "",
        "Project": project_display,
        "Component": "",
        "ItemType": "",
        "Aantal": "",
        "Unit": "",
        "ListPrice": "",
        "PurchasePrice": "",
    }]

    for node in data.get("nodes", []):
        traverse(node, project_code, 1, project_code, rows)

    df = pd.DataFrame(rows, columns=[
        "Level", "Parent", "Project", "Component", "ItemType",
        "Aantal", "Unit", "ListPrice", "PurchasePrice"
    ])
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output

def export_bom_to_excel(manufacturer_id, client_id, client_secret, segment_item_id):
    try:
        access_token = get_token(client_id, client_secret)
        project_segment_item = get_project_segment_item(access_token, manufacturer_id, segment_item_id)
        config_id = project_segment_item["configuration"]["id"]
        bom_data = get_bom_json(access_token, manufacturer_id, config_id)
        excel_bytes = bom_json_to_excel_bytes(bom_data)
        filename = f"bom_{segment_item_id}.xlsx"
        return excel_bytes, filename, None
    except Exception as e:
        return None, None, str(e)
