"""Paymob payment gateway integration for Sync Webshop.

All merchant credentials, integration IDs, labels, and enablement are read from
Webshop Paymob Settings in Frappe Desk. The API never accepts a secret from the
browser and never trusts callback status without HMAC verification.
"""

import hashlib
import hmac
import json
from urllib.parse import quote

import frappe
import requests

from sync_webshop.api.utils import set_cors_headers


PAYMOB_BASE_URL = "https://accept.paymob.com"


def _settings():
    if not frappe.db.exists("DocType", "Webshop Paymob Settings"):
        frappe.throw("Paymob settings are not installed.")
    settings = frappe.get_single("Webshop Paymob Settings")
    if not settings.enabled:
        frappe.throw("Paymob is not enabled.")
    return settings


def _secret(settings, fieldname):
    """Read a protected Desk secret without leaking Frappe password-field errors."""
    try:
        value = settings.get_password(fieldname)
    except Exception:
        value = None
    if value:
        return value
    return getattr(settings, fieldname, "") or ""


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _payment_methods(settings):
    methods = []
    for fieldname in ("card_integration_id", "wallet_integration_id", "kiosk_integration_id"):
        value = _int(getattr(settings, fieldname, None))
        if value and value not in methods:
            methods.append(value)
    configured = getattr(settings, "payment_methods", None)
    if configured:
        for value in str(configured).replace(";", ",").split(","):
            parsed = _int(value)
            if parsed and parsed not in methods:
                methods.append(parsed)
    if not methods:
        frappe.throw("At least one Paymob integration ID must be configured in Desk.")
    return methods


def _billing_data(customer):
    customer = customer if isinstance(customer, dict) else {}
    name = (customer.get("name") or customer.get("first_name") or "Guest Customer").strip()
    parts = name.split(" ", 1)
    return {
        "apartment": str(customer.get("apartment") or "NA"),
        "email": (customer.get("email") or "guest@example.com").strip(),
        "floor": str(customer.get("floor") or "NA"),
        "first_name": parts[0][:50] or "Guest",
        "street": (customer.get("address") or "NA")[:200],
        "building": str(customer.get("building") or "NA"),
        "phone_number": (customer.get("phone") or "+201000000000").strip(),
        "shipping_method": "PKG",
        "postal_code": str(customer.get("postal_code") or "00000"),
        "city": (customer.get("city") or "NA")[:50],
        "country": (customer.get("country") or "EG")[:2].upper(),
        "last_name": (parts[1] if len(parts) > 1 else "Customer")[:50],
        "state": (customer.get("state") or "NA")[:50],
    }


def _request(method, path, settings, payload=None, headers=None):
    secret = _secret(settings, "secret_key")
    if not secret:
        frappe.throw("Paymob Secret Key is not configured in Desk.")
    request_headers = {"Authorization": f"Token {secret}", "Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    try:
        response = requests.request(
            method,
            f"{PAYMOB_BASE_URL}{path}",
            headers=request_headers,
            json=payload,
            timeout=25,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        frappe.log_error(frappe.get_traceback(), "Paymob API request failed")
        frappe.throw(f"Paymob payment service is unavailable: {exc}")
    except ValueError:
        frappe.throw("Paymob returned an invalid response.")


def _save_transaction(data):
    if not frappe.db.exists("DocType", "Webshop Paymob Transaction"):
        return None
    doc = frappe.new_doc("Webshop Paymob Transaction")
    doc.update(data)
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist(allow_guest=True)
def get_paymob_settings():
    set_cors_headers()
    if not frappe.db.exists("DocType", "Webshop Paymob Settings"):
        return {"enabled": False, "public_key": "", "payment_methods": []}
    settings = frappe.get_single("Webshop Paymob Settings")
    try:
        configured_ids = _payment_methods(settings) if settings.enabled else []
    except Exception:
        # Public configuration discovery must fail closed without turning an incomplete Desk setup into a 417.
        configured_ids = []
    methods = []
    for key, fieldname, label_en, label_ar in (
        ("card", "card_integration_id", getattr(settings, "card_label_en", None) or "Cards", getattr(settings, "card_label_ar", None) or "البطاقات"),
        ("wallet", "wallet_integration_id", getattr(settings, "wallet_label_en", None) or "Mobile wallets", getattr(settings, "wallet_label_ar", None) or "المحافظ الإلكترونية"),
        ("kiosk", "kiosk_integration_id", getattr(settings, "kiosk_label_en", None) or "Kiosk and cash networks", getattr(settings, "kiosk_label_ar", None) or "الأكشاك وشبكات الدفع النقدي"),
    ):
        method_id = _int(getattr(settings, fieldname, None))
        if method_id and method_id in configured_ids:
            methods.append({"key": key, "label_en": label_en, "label_ar": label_ar})
    return {
        "enabled": bool(settings.enabled),
        "online_enabled": bool(getattr(settings, "online_payment_enabled", 1)) and bool(settings.public_key) and bool(_secret(settings, "secret_key")) and bool(_secret(settings, "hmac_secret")) and bool(configured_ids),
        "public_key": settings.public_key or "",
        "payment_methods": configured_ids,
        "methods": methods,
        "checkout_mode": getattr(settings, "checkout_mode", None) or "redirect",
        "label_en": getattr(settings, "label_en", None) or "Paymob",
        "label_ar": getattr(settings, "label_ar", None) or "الدفع عبر Paymob",
        "online_label_en": getattr(settings, "online_label_en", None) or "Online payment",
        "online_label_ar": getattr(settings, "online_label_ar", None) or "الدفع الإلكتروني",
        "online_note_en": getattr(settings, "online_note_en", None) or "Pay securely with the methods enabled in Paymob.",
        "online_note_ar": getattr(settings, "online_note_ar", None) or "ادفع بأمان باستخدام طرق الدفع المفعلة في Paymob.",
    }


@frappe.whitelist(allow_guest=True)
def create_payment_intention(amount, currency="EGP", customer=None, items=None, sales_order=None, delivery_date=None):
    """Create a Paymob intention and a corresponding draft Sales Order when needed."""
    set_cors_headers()
    settings = _settings()
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        frappe.throw("A valid payment amount is required.")
    if amount_value <= 0:
        frappe.throw("Payment amount must be greater than zero.")

    if isinstance(customer, str):
        customer = json.loads(customer)
    if isinstance(items, str):
        items = json.loads(items)
    items = items if isinstance(items, list) else []
    if not items:
        frappe.throw("At least one item is required for Paymob payment.")

    if sales_order and not frappe.db.exists("Sales Order", sales_order):
        frappe.throw("The selected Sales Order does not exist.")

    payload = {
        "amount": int(round(amount_value * 100)),
        "currency": (currency or "EGP").upper(),
        "payment_methods": _payment_methods(settings),
        "items": [
            {
                "name": str(row.get("item_name") or row.get("item_code") or "Product")[:255],
                "amount": int(round(float(row.get("price") or row.get("rate") or 0) * 100)),
                "description": str(row.get("item_name") or row.get("item_code") or "Product")[:255],
                "quantity": int(float(row.get("qty") or row.get("quantity") or 1)),
            }
            for row in items
        ],
        "billing_data": _billing_data(customer),
    }
    if sales_order:
        payload["special_reference"] = sales_order

    response = _request("POST", "/v1/intention/", settings, payload)
    client_secret = response.get("client_secret") or response.get("clientSecret")
    intention_id = response.get("id")
    if not client_secret:
        frappe.throw("Paymob did not return a checkout client secret.")

    transaction_name = _save_transaction({
        "sales_order": sales_order,
        "intention_id": str(intention_id or ""),
        "amount": amount_value,
        "currency": payload["currency"],
        "status": "Pending",
        "customer_email": (customer or {}).get("email") if isinstance(customer, dict) else None,
        "raw_response": json.dumps(response, ensure_ascii=False),
    })
    return {
        "client_secret": client_secret,
        "intention_id": intention_id,
        "checkout_url": f"{PAYMOB_BASE_URL}/unifiedcheckout/?publicKey={quote(settings.public_key or '')}&clientSecret={quote(client_secret)}",
        "transaction": transaction_name,
        "currency": payload["currency"],
    }


def _hmac_value(payload, secret):
    obj = payload.get("obj") if isinstance(payload.get("obj"), dict) else payload
    values = [
        obj.get("amount_cents"),
        obj.get("created_at"),
        obj.get("currency"),
        obj.get("error_occured"),
        obj.get("has_parent_transaction"),
        obj.get("id"),
        obj.get("integration_id"),
        obj.get("is_3d_secure"),
        obj.get("is_auth"),
        obj.get("is_capture"),
        obj.get("is_refunded"),
        obj.get("is_standalone_payment"),
        obj.get("is_voided"),
        (obj.get("order") or {}).get("id") if isinstance(obj.get("order"), dict) else obj.get("order_id"),
        obj.get("owner"),
        obj.get("pending"),
        (obj.get("source_data") or {}).get("pan") if isinstance(obj.get("source_data"), dict) else None,
        (obj.get("source_data") or {}).get("sub_type") if isinstance(obj.get("source_data"), dict) else None,
        (obj.get("source_data") or {}).get("type") if isinstance(obj.get("source_data"), dict) else None,
        obj.get("success"),
    ]
    plain = "".join(str(value if value is not None else "") for value in values)
    return hmac.new(secret.encode(), plain.encode(), hashlib.sha512).hexdigest()


@frappe.whitelist(allow_guest=True)
def paymob_callback():
    """Verify Paymob HMAC callbacks and update the related Sales Order idempotently."""
    set_cors_headers()
    settings = _settings()
    raw = frappe.request.get_data(as_text=True) or "{}"
    try:
        payload = json.loads(raw)
    except ValueError:
        frappe.local.response.http_status_code = 400
        return {"ok": False, "error": "Invalid JSON payload"}

    supplied = frappe.form_dict.get("hmac") or payload.get("hmac")
    expected = _hmac_value(payload, _secret(settings, "hmac_secret")) if _secret(settings, "hmac_secret") else ""
    if not supplied or not expected or not hmac.compare_digest(str(supplied), expected):
        frappe.local.response.http_status_code = 401
        return {"ok": False, "error": "Invalid HMAC"}

    obj = payload.get("obj") if isinstance(payload.get("obj"), dict) else payload
    transaction_id = str(obj.get("id") or "")
    order_data = obj.get("order") if isinstance(obj.get("order"), dict) else {}
    intention_id = str(obj.get("order_id") or order_data.get("id") or "")
    success = bool(obj.get("success")) and not bool(obj.get("error_occured"))
    status = "Paid" if success else "Failed"

    tx_name = frappe.db.get_value("Webshop Paymob Transaction", {"intention_id": intention_id}, "name") if frappe.db.exists("DocType", "Webshop Paymob Transaction") else None
    if tx_name:
        tx = frappe.get_doc("Webshop Paymob Transaction", tx_name)
        tx.db_set("transaction_id", transaction_id)
        tx.db_set("status", status)
        tx.db_set("hmac_verified", 1)
        tx.db_set("raw_callback", raw)
        sales_order = tx.sales_order
    else:
        sales_order = None

    if sales_order and frappe.db.exists("Sales Order", sales_order):
        so = frappe.get_doc("Sales Order", sales_order)
        if so.meta.has_field("webshop_payment_status"):
            so.db_set("webshop_payment_status", status)
        if so.meta.has_field("webshop_paymob_transaction_id"):
            so.db_set("webshop_paymob_transaction_id", transaction_id)

    return {"ok": True, "status": status, "transaction_id": transaction_id}
