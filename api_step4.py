def move_segments_to_step4(
    manufacturer_id, client_id, client_secret, input_content
):
    """Voert voor elke (salesId, projectId, shippingDate) een moveToStep4 uit."""
    log = []
    try:
        # Token ophalen
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
    except Exception as e:
        return [{"error": f"Fout bij ophalen token: {e}"}]

    # Input verwerken
    regels = []
    lines = input_content.strip().splitlines()
    for i, line in enumerate(lines):
        if i == 0:
            continue  # header skippen
        parts = line.strip().split('\t')
        if len(parts) < 3:
            continue
        sales_id = parts[0].strip()
        project_id = parts[1].strip()
        date_str = parts[2].strip()
        if not (sales_id and project_id and date_str):
            continue
        try:
            dt = datetime.datetime.strptime(date_str, "%d/%m/%y")
            shipping_date = dt.strftime("%Y-%m-%dT16:00:00Z")
            regels.append((sales_id, project_id, shipping_date))
        except Exception as e:
            log.append({"i": i+1, "sales_id": sales_id, "project_id": project_id, "error": f"Ongeldige datum: {date_str}"})

    for i, (sales_id, project_id, shipping_date) in enumerate(regels, start=1):
        try:
            # 1. Project ophalen
            url_proj = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/projects/{project_id}"
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(url_proj, headers=headers)
            resp.raise_for_status()
            project_data = resp.json()
            project_segments = project_data.get("projectSegments", [])
            if not project_segments:
                raise Exception("Geen projectSegments gevonden voor projectId " + project_id)
            project_segment_id = project_segments[0]["id"]

            # 2. Segment detail ophalen
            url_segment = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/projectSegments/{project_segment_id}"
            resp = requests.get(url_segment, headers=headers)
            resp.raise_for_status()
            segment_data = resp.json()

            # 3. Body samenstellen
            order = segment_data.get("order", {})
            delivery = order.get("delivery", {})
            invoice = order.get("invoice", {})
            supplierSoRef = order.get("manufacturerSoRef") or sales_id

            delivery_addr = delivery.get("address", {})
            if delivery_addr.get("stateIso", "") == "":
                delivery_addr.pop("stateIso", None)
            invoice_addr = invoice.get("address", {})
            if invoice_addr.get("stateIso", "") == "":
                invoice_addr.pop("stateIso", None)

            body = {
                "info": {
                    "orderRemarkSupplier": sales_id,
                    "supplierSoRef": supplierSoRef,
                    "shippingDateConfirmed": shipping_date
                },
                "delivery": {
                    "address": delivery_addr,
                    "companyName": delivery.get("companyName", ""),
                    "contactName": delivery.get("contactName", ""),
                    "contactPhone": delivery.get("contactPhone", ""),
                    "email": delivery.get("email", "")
                },
                "invoice": {
                    "address": invoice_addr,
                    "companyName": invoice.get("companyName", ""),
                    "companyVatNumber": invoice.get("companyVatNumber", ""),
                    "contactName": invoice.get("contactName", ""),
                    "contactPhone": invoice.get("contactPhone", ""),
                    "email": invoice.get("email", "")
                }
            }

            # 4. moveToStep4 call
            url_step4 = f"https://connect.hivecpq.com/api/v1/manufacturers/{manufacturer_id}/projectSegments/{project_segment_id}/moveToStep4"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            r = requests.post(url_step4, data=json.dumps(body), headers=headers)
            result = {
                "i": i,
                "project_id": project_id,
                "project_segment_id": project_segment_id,
                "sales_id": sales_id,
                "shipping_date": shipping_date,
                "status_code": r.status_code,
                "response": r.text[:200] + ("..." if len(r.text) > 200 else ""),
                "body": body
            }
            log.append(result)
        except Exception as e:
            tb = traceback.format_exc()
            log.append({
                "i": i,
                "project_id": project_id,
                "sales_id": sales_id,
                "error": str(e),
                "traceback": tb
            })
    return log
