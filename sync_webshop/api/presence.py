import json

import frappe

from sync_webshop.api.utils import set_cors_headers


def _content_settings():
    return frappe.get_single("Webshop Content Settings")



@frappe.whitelist(allow_guest=True)
def get_presence_settings():
    set_cors_headers()
    settings = _content_settings()
    tracking = frappe.get_single("Webshop Content Settings") if frappe.db.exists("DocType", "Webshop Content Settings") else None
    return {
        "material_studio_enabled": bool(getattr(settings, "presence_material_studio_enabled", 1)),
        "quote_requests_enabled": bool(getattr(settings, "quote_requests_enabled", 0)),
        "live_tracking_map_enabled": bool(getattr(settings, "live_tracking_map_enabled", 0)),
        "social_proof_enabled": bool(getattr(settings, "social_proof_enabled", 0)),
        "social_proof_viewer_enabled": bool(getattr(settings, "social_proof_viewer_enabled", 0)),
        "tracking": {"enabled": bool(getattr(tracking, "tracking_enabled", 0)) if tracking else False, "map_enabled": bool(getattr(tracking, "tracking_map_enabled", 0)) if tracking else False, "courier_name": getattr(tracking, "tracking_courier_name", None) if tracking else None},
    }


def _find_or_create_customer(customer):
    customer = customer if isinstance(customer, dict) else {}
    email = (customer.get("email") or "").strip()
    phone = (customer.get("phone") or "").strip()
    name = (customer.get("name") or customer.get("first_name") or email or phone or "Quote customer").strip()[:140]
    existing = None
    if email:
        existing = frappe.db.get_value("Customer", {"email_id": email}, "name")
    if not existing and phone:
        existing = frappe.db.get_value("Customer", {"mobile_no": phone}, "name")
    if existing:
        return existing
    group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or frappe.db.get_value("Customer Group", {}, "name")
    territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or frappe.db.get_value("Territory", {}, "name")
    doc = frappe.new_doc("Customer")
    doc.customer_name = name
    doc.customer_type = "Company" if customer.get("company") else "Individual"
    if group:
        doc.customer_group = group
    if territory:
        doc.territory = territory
    if email:
        doc.email_id = email
    if phone:
        doc.mobile_no = phone
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist(allow_guest=True)
def request_quote(customer, items, note=None, company=None):
    set_cors_headers()
    settings = _content_settings()
    if not getattr(settings, "quote_requests_enabled", 0):
        frappe.throw("Quote requests are disabled.")
    if isinstance(items, str):
        items = json.loads(items)
    items = items if isinstance(items, list) else []
    if not items:
        frappe.throw("At least one item is required.")
    customer_data = json.loads(customer) if isinstance(customer, str) else (customer if isinstance(customer, dict) else {})
    party = _find_or_create_customer({**customer_data, "company": company or customer_data.get("company")})
    quotation = frappe.new_doc("Quotation")
    quotation.quotation_to = "Customer"
    quotation.party_name = party
    if company:
        quotation.customer_name = company
    if note and quotation.meta.has_field("terms"):
        quotation.terms = str(note)[:2000]
    for row in items:
        code = row.get("item_code")
        if not code:
            continue
        child = quotation.append("items", {})
        child.item_code = code
        child.qty = max(float(row.get("qty") or 1), 1)
        if row.get("rate") is not None:
            child.rate = float(row.get("rate") or 0)
    quotation.flags.ignore_permissions = True
    quotation.insert(ignore_permissions=True)
    return {"name": quotation.name, "status": quotation.status, "customer": party, "message": "Quote request received."}
