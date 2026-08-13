import frappe
import json
import requests
from frappe.utils import flt, getdate, nowdate

from sync_webshop.api.utils import set_cors_headers


@frappe.whitelist(allow_guest=True)
def validate_coupon(coupon_code, total_amount=0):
    set_cors_headers()
    settings = frappe.get_single("Webshop Content Settings")
    if not getattr(settings, "enable_coupons", 0):
        frappe.throw("Coupons are currently disabled")

    normalized_code = str(coupon_code or "").strip()
    if not normalized_code:
        frappe.throw("Coupon code is required")

    coupon = frappe.db.get_value(
        "Coupon Code",
        {"coupon_code": normalized_code},
        ["name", "pricing_rule", "valid_from", "valid_upto", "maximum_use", "used"],
        as_dict=True,
    )
    if not coupon:
        frappe.throw("Invalid coupon code")

    today = getdate(nowdate())
    if coupon.valid_from and getdate(coupon.valid_from) > today:
        frappe.throw("Coupon is not yet valid")
    if coupon.valid_upto and getdate(coupon.valid_upto) < today:
        frappe.throw("Coupon has expired")
    if coupon.maximum_use and flt(coupon.used) >= flt(coupon.maximum_use):
        frappe.throw("Coupon usage limit has been reached")
    if not coupon.pricing_rule:
        frappe.throw("Coupon has no pricing rule")

    pricing_rule = frappe.get_doc("Pricing Rule", coupon.pricing_rule)
    if getattr(pricing_rule, "disable", 0):
        frappe.throw("Coupon is disabled")

    subtotal = max(flt(total_amount), 0)
    discount_amount = 0
    if pricing_rule.rate_or_discount == "Discount Amount":
        discount_amount = flt(pricing_rule.discount_amount)
    elif pricing_rule.rate_or_discount == "Discount Percentage":
        discount_amount = subtotal * flt(pricing_rule.discount_percentage) / 100

    return {
        "coupon_code": normalized_code,
        "discount_amount": min(max(discount_amount, 0), subtotal),
        "pricing_rule": pricing_rule.name,
    }


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
