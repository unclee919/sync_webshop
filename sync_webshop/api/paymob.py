"""Paymob Unified Checkout integration for Sync Webshop.

This module uses Webshop Payment Settings as the single source of truth for
payment method presentation and credentials. Webshop Paymob Settings remains
available in Desk only as a legacy configuration record and is not used for new
transactions.
"""

import hashlib
import hmac
import json
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote

import frappe
import requests

from sync_webshop.api.utils import set_cors_headers

PAYMOB_INTENTION_URL = "https://accept.paymob.com/v1/intention/"
PAYMOB_CHECKOUT_URL = "https://accept.paymob.com/unifiedcheckout/"

METHOD_FIELD_MAP = {
    "visa": "visa_integration_id",
    "wallet": "wallet_integration_id",
    "value": "value_integration_id",
    "tabby": "tabby_integration_id",
    "tamara": "tamara_integration_id",
    "mada": "mada_integration_id",
    "apple_pay": "apple_pay_integration_id",
}

HMAC_FIELDS = (
    "amount_cents", "created_at", "currency", "error_occured",
    "has_parent_transaction", "id", "integration_id", "is_3d_secure",
    "is_auth", "is_capture", "is_refunded", "is_standalone_payment",
    "is_voided", "order_id", "owner", "pending", "source_data_pan",
    "source_data_sub_type", "source_data_type", "success",
)


def _as_string(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value)


def _parse_dict(value, name):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            frappe.throw(f"{name} must be valid JSON.")
    if value is None:
        return {}
    if not isinstance(value, dict):
        frappe.throw(f"{name} must be an object.")
    return value


def _payment_settings():
    settings = frappe.get_single("Webshop Payment Settings")
    if not settings.paymob_enabled:
        frappe.throw("Online payments are not enabled in Webshop Payment Settings.")
    return settings


def _secret(settings, fieldname):
    try:
        return settings.get_password(fieldname)
    except Exception:
        return settings.get(fieldname)


def _integration_id(settings, payment_method):
    method = str(payment_method or "visa").strip().lower()
    if method not in METHOD_FIELD_MAP:
        frappe.throw("The selected Paymob payment method is not supported.")
    if not settings.get(f"{method}_enabled"):
        frappe.throw("The selected Paymob payment method is disabled in Desk.")
    raw_id = str(settings.get(METHOD_FIELD_MAP[method]) or "").strip()
    if not raw_id.isdigit() or int(raw_id) <= 0:
        frappe.throw(f"Set a valid Integration ID for {method} in Webshop Payment Settings.")
    return method, int(raw_id)


def _storefront_base_url():
    api_settings = frappe.get_single("Webshop API Settings")
    configured = str(api_settings.get("public_storefront_url") or "").strip().rstrip("/")
    if configured.startswith(("https://", "http://")):
        return configured

    allowed_origins = str(api_settings.get("allowed_origins") or "")
    for origin in allowed_origins.splitlines():
        origin = origin.strip().rstrip("/")
        if origin.startswith(("https://", "http://")):
            return origin

    frappe.throw("Set Public Storefront URL in Webshop API Settings before enabling Paymob checkout.")


def _billing_data(sales_order, customer):
    customer = _parse_dict(customer, "customer")
    full_name = str(customer.get("name") or customer.get("full_name") or sales_order.customer_name or "Customer").strip()
    name_parts = full_name.split(maxsplit=1)
    first_name = name_parts[0] if name_parts else "Customer"
    last_name = name_parts[1] if len(name_parts) > 1 else "Customer"
    phone = str(customer.get("phone") or customer.get("phone_number") or "").strip()
    email = str(customer.get("email") or "").strip()
    if not phone or not email:
        frappe.throw("A customer email address and phone number are required for Paymob checkout.")

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone_number": phone,
        "apartment": "NA",
        "floor": "NA",
        "street": str(customer.get("address") or "NA"),
        "building": "NA",
        "shipping_method": "PKG",
        "postal_code": "NA",
        "city": str(customer.get("city") or "NA"),
        "country": "EG",
        "state": str(customer.get("governorate") or "NA"),
    }


def _amount_cents(amount):
    return int((Decimal(str(amount or 0)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _create_transaction(sales_order, intention_id, paymob_order_id, amount, currency, payment_method, customer_email, response):
    existing = frappe.db.get_value("Webshop Paymob Transaction", {"intention_id": intention_id}, "name")
    if existing:
        return frappe.get_doc("Webshop Paymob Transaction", existing)

    transaction = frappe.get_doc({
        "doctype": "Webshop Paymob Transaction",
        "sales_order": sales_order.name,
        "intention_id": intention_id,
        "paymob_order_id": str(paymob_order_id or ""),
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": "Pending",
        "customer_email": customer_email,
        "raw_response": json.dumps({
            "id": response.get("id"),
            "intention_order_id": response.get("intention_order_id"),
            "payment_methods": response.get("payment_methods"),
            "status": response.get("status"),
        }, default=str),
    })
    transaction.flags.ignore_permissions = True
    transaction.insert()
    return transaction


def _callback_values(transaction):
    source_data = transaction.get("source_data") or {}
    order = transaction.get("order") or {}
    return {
        "amount_cents": transaction.get("amount_cents"),
        "created_at": transaction.get("created_at"),
        "currency": transaction.get("currency"),
        "error_occured": transaction.get("error_occured"),
        "has_parent_transaction": transaction.get("has_parent_transaction"),
        "id": transaction.get("id"),
        "integration_id": transaction.get("integration_id"),
        "is_3d_secure": transaction.get("is_3d_secure"),
        "is_auth": transaction.get("is_auth"),
        "is_capture": transaction.get("is_capture"),
        "is_refunded": transaction.get("is_refunded"),
        "is_standalone_payment": transaction.get("is_standalone_payment"),
        "is_voided": transaction.get("is_voided"),
        "order_id": order.get("id") if isinstance(order, dict) else transaction.get("order_id"),
        "owner": transaction.get("owner"),
        "pending": transaction.get("pending"),
        "source_data_pan": source_data.get("pan"),
        "source_data_sub_type": source_data.get("sub_type"),
        "source_data_type": source_data.get("type"),
        "success": transaction.get("success"),
    }


def verify_callback_hmac(transaction, received_hmac, secret):
    if not received_hmac or not secret:
        return False
    values = _callback_values(transaction)
    signed = "".join(_as_string(values[field]) for field in HMAC_FIELDS)
    expected = hmac.new(secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, str(received_hmac))


@frappe.whitelist(allow_guest=True)
def get_paymob_settings():
    """Return public payment configuration only; never expose credentials."""
    set_cors_headers()
    settings = frappe.get_single("Webshop Payment Settings")
    methods = []
    for method, fieldname in METHOD_FIELD_MAP.items():
        if settings.get(f"{method}_enabled"):
            methods.append({
                "name": method,
                "label_en": settings.get(f"{method}_label_en"),
                "label_ar": settings.get(f"{method}_label_ar"),
                "icon": settings.get(f"{method}_icon"),
                "configured": bool(str(settings.get(fieldname) or "").strip()),
            })
    return {
        "enabled": bool(settings.paymob_enabled),
        "mode": settings.get("paymob_mode") or "Test",
        "currency": settings.get("paymob_currency") or "EGP",
        "methods": methods,
    }


@frappe.whitelist(allow_guest=True)
def create_payment_intention(sales_order=None, payment_method="visa", customer=None, **_ignored):
    """Create one Paymob Unified Checkout intention for an existing pending Sales Order.

    Amount and currency are always calculated from the ERPNext order, not browser
    input. This prevents client-side amount manipulation.
    """
    set_cors_headers()
    order_name = str(sales_order or "").strip()
    if not order_name:
        frappe.throw("Create the Sales Order before starting an online payment.")

    sales_order_doc = frappe.get_doc("Sales Order", order_name)
    if sales_order_doc.docstatus == 2:
        frappe.throw("Cancelled Sales Orders cannot be paid.")
    if sales_order_doc.get("webshop_payment_status") == "Paid":
        frappe.throw("This Sales Order has already been paid.")

    settings = _payment_settings()
    method, integration_id = _integration_id(settings, payment_method)
    secret_key = _secret(settings, "paymob_api_key")
    public_key = str(settings.get("paymob_public_key") or "").strip()
    if not secret_key:
        frappe.throw("Set the Paymob Secret Key in Webshop Payment Settings.")
    if not public_key:
        frappe.throw("Set the Paymob Public Key in Webshop Payment Settings.")

    base_url = _storefront_base_url()
    callback_url = str(settings.get("paymob_callback_url") or "").strip() or f"{base_url}/api/method/sync_webshop.api.paymob.paymob_webhook"
    return_url = str(settings.get("paymob_return_url") or "").strip() or f"{base_url}/checkout?payment=paymob"
    billing_data = _billing_data(sales_order_doc, customer)
    total_amount = float(sales_order_doc.grand_total or 0)
    if total_amount <= 0:
        frappe.throw("The Sales Order total must be greater than zero for online payment.")

    payload = {
        "amount": _amount_cents(total_amount),
        "currency": sales_order_doc.currency or settings.get("paymob_currency") or "EGP",
        "payment_methods": [integration_id],
        "items": [],
        "billing_data": billing_data,
        "extras": {"sales_order": sales_order_doc.name, "payment_method": method},
        "merchant_order_id": sales_order_doc.name,
        "notification_url": callback_url,
        "redirection_url": return_url,
    }
    try:
        response = requests.post(
            PAYMOB_INTENTION_URL,
            headers={"Authorization": f"Token {secret_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        frappe.log_error(frappe.get_traceback(), "Paymob intention network error")
        frappe.throw("Unable to reach Paymob. Please try again shortly.")

    try:
        response_data = response.json()
    except ValueError:
        response_data = {}
    if response.status_code not in (200, 201) or not response_data.get("client_secret"):
        frappe.log_error(json.dumps({"status": response.status_code, "response": response_data}, default=str), "Paymob intention rejected")
        frappe.throw("Paymob rejected the payment request. Check the active mode, Secret Key, currency, and Integration ID in Desk.")

    transaction = _create_transaction(
        sales_order_doc,
        response_data.get("id"),
        response_data.get("intention_order_id"),
        total_amount,
        payload["currency"],
        method,
        billing_data["email"],
        response_data,
    )
    if sales_order_doc.meta.has_field("webshop_payment_method"):
        sales_order_doc.db_set("webshop_payment_method", f"paymob:{method}")
    if sales_order_doc.meta.has_field("webshop_payment_status"):
        sales_order_doc.db_set("webshop_payment_status", "Pending")

    client_secret = response_data["client_secret"]
    checkout_url = f"{PAYMOB_CHECKOUT_URL}?publicKey={quote(public_key)}&clientSecret={quote(client_secret)}"
    return {
        "sales_order": sales_order_doc.name,
        "transaction": transaction.name,
        "intention_id": response_data.get("id"),
        "redirect_url": checkout_url,
        "checkout_url": checkout_url,
    }


@frappe.whitelist(allow_guest=True)
def paymob_webhook():
    """Verify a Paymob processed callback and apply its result idempotently."""
    set_cors_headers()
    payload = frappe.request.get_json() or frappe.form_dict or {}
    transaction_data = payload.get("obj") if isinstance(payload, dict) else None
    if not isinstance(transaction_data, dict):
        transaction_data = payload if isinstance(payload, dict) else {}

    received_hmac = frappe.form_dict.get("hmac") or payload.get("hmac")
    settings = frappe.get_single("Webshop Payment Settings")
    hmac_secret = _secret(settings, "paymob_hmac_secret")
    if not verify_callback_hmac(transaction_data, received_hmac, hmac_secret):
        frappe.log_error("Rejected Paymob callback because HMAC verification failed.", "Paymob callback security")
        frappe.local.response.http_status_code = 403
        return {"status": "rejected"}

    order = transaction_data.get("order") or {}
    paymob_order_id = str(order.get("id") or transaction_data.get("order_id") or "")
    intention_id = str(transaction_data.get("intention_id") or "")
    filters = {"paymob_order_id": paymob_order_id} if paymob_order_id else {"intention_id": intention_id}
    transaction_name = frappe.db.get_value("Webshop Paymob Transaction", filters, "name") if list(filters.values())[0] else None
    if not transaction_name:
        frappe.log_error(json.dumps({"paymob_order_id": paymob_order_id, "intention_id": intention_id}), "Unmatched Paymob callback")
        return {"status": "ignored"}

    transaction = frappe.get_doc("Webshop Paymob Transaction", transaction_name)
    is_success = transaction_data.get("success") is True or str(transaction_data.get("success")).lower() == "true"
    is_pending = transaction_data.get("pending") is True or str(transaction_data.get("pending")).lower() == "true"
    status = "Paid" if is_success and not is_pending else "Failed"
    transaction.db_set("transaction_id", str(transaction_data.get("id") or ""))
    transaction.db_set("status", status)
    transaction.db_set("hmac_verified", 1)
    transaction.db_set("raw_callback", json.dumps(transaction_data, default=str))

    sales_order = frappe.get_doc("Sales Order", transaction.sales_order)
    if sales_order.meta.has_field("webshop_payment_status"):
        sales_order.db_set("webshop_payment_status", status)
    if sales_order.meta.has_field("webshop_payment_method") and not sales_order.get("webshop_payment_method"):
        sales_order.db_set("webshop_payment_method", f"paymob:{transaction.get('payment_method') or 'online'}")
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def create_paymob_intention(*args, **kwargs):
    """Backward-compatible endpoint name delegated to the canonical service."""
    return create_payment_intention(*args, **kwargs)


@frappe.whitelist(allow_guest=True)
def paymob_callback():
    """Backward-compatible callback endpoint name delegated to the verified webhook."""
    return paymob_webhook()
