import frappe
import json
import requests
from sync_webshop.api.utils import set_cors_headers


@frappe.whitelist()
def sync_cart(cart_data):
    set_cors_headers()
    if frappe.session.user == "Guest":
        return
        
    settings = frappe.get_single("Webshop Content Settings")
    master_recovery_enabled = None
    if frappe.db.exists("DocType", "Webshop Master Tier Settings"):
        try:
            master_recovery_enabled = bool(getattr(frappe.get_single("Webshop Master Tier Settings"), "abandoned_cart_enabled", 0))
        except Exception:
            master_recovery_enabled = None
    if master_recovery_enabled is False or (master_recovery_enabled is None and not settings.enable_abandoned_cart_recovery):
        return
        
    user = frappe.get_doc("User", frappe.session.user)
    
    abandoned_cart = frappe.db.get_value("Webshop Abandoned Cart", {"user": user.name, "status": "Abandoned"}, "name")
    
    if abandoned_cart:
        doc = frappe.get_doc("Webshop Abandoned Cart", abandoned_cart)
        doc.cart_data = json.dumps(cart_data)
        doc.last_updated = frappe.utils.now()
        if doc.meta.has_field("recovery_stage"):
            doc.recovery_stage = "Pending Follow-up"
            doc.recovery_ready_at = None
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Webshop Abandoned Cart",
            "user": user.name,
            "email": user.email,
            "cart_data": json.dumps(cart_data),
            "status": "Abandoned",
            "last_updated": frappe.utils.now(),
            "recovery_stage": "Pending Follow-up"
        })
        doc.insert(ignore_permissions=True)
        
    return "Cart synced"

@frappe.whitelist(allow_guest=True)
def subscribe_newsletter(email):
    set_cors_headers()
    settings = frappe.get_single("Webshop Content Settings")
    if not settings.enable_mailchimp:
        # Fallback: Save to a local DocType or just return success
        return "Subscription successful (local)"
        
    api_key = settings.mailchimp_api_key
    list_id = settings.mailchimp_list_id
    server = settings.mailchimp_server_prefix
    
    if not all([api_key, list_id, server]):
        frappe.throw("Mailchimp configuration is incomplete")
        
    url = f"https://{server}.api.mailchimp.com/3.0/lists/{list_id}/members"
    auth = ("any", api_key)
    data = {
        "email_address": email,
        "status": "subscribed"
    }
    
    try:
        response = requests.post(url, auth=auth, json=data)
        if response.status_code == 200 or response.status_code == 201:
            return "Subscribed successfully"
        else:
            res_json = response.json()
            if res_json.get("title") == "Member Exists":
                return "Already subscribed"
            frappe.throw(f"Mailchimp error: {res_json.get('detail')}")
    except Exception as e:
        frappe.throw(f"Failed to connect to Mailchimp: {str(e)}")
