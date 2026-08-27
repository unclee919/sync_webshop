import hashlib
import re
import secrets
import time

import frappe
from frappe.sessions import get_csrf_token as frappe_get_csrf_token
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import get_url

from sync_webshop.api.utils import set_cors_headers

OTP_TTL = 600
OTP_MAX_ATTEMPTS = 5
OTP_RATE_WINDOW = 60
OTP_MAX_REQUESTS = 3
SESSION_TTL = 60 * 60 * 24 * 7
OTP_PREFIX = "sync_webshop:otp:"
SESSION_PREFIX = "sync_webshop:account_session:"
OTP_EMAIL_TEMPLATE_NAME = "Sync Webshop OTP Verification"


def _clean_email(value):
    value = str(value or "").strip().lower()
    if not value or len(value) > 140 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return ""
    return value


def _clean_phone(value):
    value = re.sub(r"[^0-9+]", "", str(value or "").strip())
    if value.startswith("00"):
        value = "+" + value[2:]
    if not re.fullmatch(r"\+?[0-9]{7,20}", value):
        return ""
    return value


def _identifier(email=None, phone=None, identifier=None):
    raw = str(identifier or "").strip()
    if raw and "@" in raw:
        email = raw
    elif raw:
        phone = raw
    email = _clean_email(email)
    phone = _clean_phone(phone)
    if not email and not phone:
        frappe.throw("Enter a valid email address or phone number.")
    return email, phone


def _lookup_customer(email=None, phone=None):
    customer = None
    if email:
        customer = frappe.db.get_value(
            "Customer",
            {"email_id": email},
            ["name", "customer_name", "email_id", "mobile_no"],
            as_dict=True,
        )
        if not customer:
            customer = frappe.db.get_value(
                "Contact",
                {"email_id": email},
                "name",
            )
    if isinstance(customer, str):
        link = frappe.db.get_value(
            "Dynamic Link",
            {"parent": customer, "parenttype": "Contact", "link_doctype": "Customer"},
            "link_name",
        )
        customer = frappe.db.get_value(
            "Customer",
            link,
            ["name", "customer_name", "email_id", "mobile_no"],
            as_dict=True,
        ) if link else None
    if not customer and phone:
        customer = frappe.db.get_value(
            "Customer",
            {"mobile_no": phone},
            ["name", "customer_name", "email_id", "mobile_no"],
            as_dict=True,
        )
        if not customer:
            contact_name = frappe.db.get_value("Contact", {"phone": phone}, "name") or frappe.db.get_value("Contact", {"mobile_no": phone}, "name")
            link = frappe.db.get_value(
                "Dynamic Link",
                {"parent": contact_name, "parenttype": "Contact", "link_doctype": "Customer"},
                "link_name",
            ) if contact_name else None
            customer = frappe.db.get_value(
                "Customer",
                link,
                ["name", "customer_name", "email_id", "mobile_no"],
                as_dict=True,
            ) if link else None
    return customer


def _customer_profile(customer_name):
    customer = frappe.get_doc("Customer", customer_name)
    email = customer.get("email_id") or ""
    phone = customer.get("mobile_no") or customer.get("phone") or ""
    contact_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Customer", "link_name": customer.name, "parenttype": "Contact"},
        "parent",
    )
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name)
        email = email or next((row.email_id for row in contact.email_ids if row.email_id), "")
        phone = phone or next((row.phone for row in contact.phone_nos if row.phone), "")
    return {
        "name": customer.name,
        "customer_name": customer.customer_name,
        "email": email,
        "phone": phone,
        "customer_group": customer.get("customer_group"),
        "territory": customer.get("territory"),
    }


def _create_customer(email, phone, full_name):
    existing = _lookup_customer(email=email, phone=phone)
    if existing:
        return existing.name
    group = frappe.db.get_single_value("Selling Settings", "customer_group") or frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    territory = frappe.db.get_single_value("Selling Settings", "territory") or frappe.db.get_value("Territory", {"is_group": 0}, "name")
    customer_doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": (full_name or "Customer").strip()[:140],
        "customer_type": "Individual",
        "customer_group": group,
        "territory": territory,
        "email_id": email or None,
        "mobile_no": phone or None,
    })
    customer_doc.flags.ignore_permissions = True
    customer_doc.insert(ignore_permissions=True)
    contact_doc = frappe.get_doc({
        "doctype": "Contact",
        "first_name": (full_name or "Customer").strip()[:140],
        "email_ids": ([{"email_id": email, "is_primary": 1}] if email else []),
        "phone_nos": ([{"phone": phone, "is_primary_mobile_no": 1}] if phone else []),
        "links": [{"link_doctype": "Customer", "link_name": customer_doc.name}],
    })
    contact_doc.flags.ignore_permissions = True
    contact_doc.insert(ignore_permissions=True)
    return customer_doc.name


def _cache_key(prefix, value):
    return prefix + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _render_otp_email(email, code):
    fallback_subject = "Your Sync Webshop verification code"
    fallback_message = f"Your Sync Webshop verification code is {code}. It expires in 10 minutes."
    context = {
        "brand_name": "Sync Webshop",
        "code": code,
        "expiry_minutes": 10,
        "recipient_email": email,
        "site_url": get_url(),
    }
    try:
        template = frappe.get_cached_doc("Email Template", OTP_EMAIL_TEMPLATE_NAME)
        formatted = template.get_formatted_email(context)
        return formatted.get("subject") or fallback_subject, formatted.get("message") or fallback_message
    except frappe.DoesNotExistError:
        return fallback_subject, fallback_message
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Sync Webshop OTP email template rendering failed")
        return fallback_subject, fallback_message


def _send_code(email, phone, code):
    message = f"Your Sync Webshop verification code is {code}. It expires in 10 minutes."
    sms_gateway_configured = False
    if phone:
        try:
            sms_gateway_configured = bool(frappe.db.get_single_value("SMS Settings", "sms_gateway_url"))
        except Exception:
            sms_gateway_configured = False
    if phone and sms_gateway_configured:
        send_sms([phone], message, success_msg=False)
        return "sms"
    if email:
        subject, rendered_message = _render_otp_email(email, code)
        email_queue = frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=rendered_message,
            delayed=True,
            now=False,
        )
        if email_queue and email_queue.name:
            frappe.enqueue(
                "frappe.email.queue.flush",
                queue="short",
                enqueue_after_commit=True,
                job_name=f"sync_webshop_otp_{email_queue.name}",
            )
        return "email"
    frappe.throw("Phone verification is unavailable because no SMS gateway is configured. Please use email or configure SMS Settings.")


def _session_from_request():
    token = frappe.get_request_header("X-Sync-Account-Session") or frappe.request.cookies.get("sync_webshop_account")
    if not token:
        return None
    session = frappe.cache().get_value(_cache_key(SESSION_PREFIX, token))
    if not session:
        return None
    if isinstance(session, bytes):
        session = session.decode("utf-8")
    if isinstance(session, str):
        import json
        try:
            session = json.loads(session)
        except ValueError:
            return None
    if not isinstance(session, dict) or float(session.get("expires_at") or 0) < time.time():
        frappe.cache().delete_value(_cache_key(SESSION_PREFIX, token))
        return None
    return session


def get_authenticated_customer():
    session = _session_from_request()
    if not session or not session.get("customer"):
        return None
    return {"customer": session["customer"], "profile": _customer_profile(session["customer"])}


@frappe.whitelist(allow_guest=True)
def get_csrf_token():
    set_cors_headers()
    return {"csrf_token": frappe_get_csrf_token()}


@frappe.whitelist(allow_guest=True)
def request_otp(identifier=None, email=None, phone=None, mode="login", full_name=None):
    set_cors_headers()
    email, phone = _identifier(email=email, phone=phone, identifier=identifier)
    mode = "register" if str(mode or "").lower() == "register" else "login"
    rate_key = _cache_key(OTP_PREFIX + "rate:", email or phone)
    rate = frappe.cache().get_value(rate_key) or {"count": 0, "window": time.time()}
    if float(rate.get("window") or 0) + OTP_RATE_WINDOW < time.time():
        rate = {"count": 0, "window": time.time()}
    if int(rate.get("count") or 0) >= OTP_MAX_REQUESTS:
        frappe.throw("Too many verification requests. Please wait one minute and try again.")
    rate["count"] = int(rate.get("count") or 0) + 1
    frappe.cache().set_value(rate_key, rate, expires_in_sec=OTP_RATE_WINDOW)
    existing = _lookup_customer(email=email, phone=phone)
    if mode == "login" and not existing:
        frappe.throw("No account was found for this email or phone number. Choose Register to create one.")
    if mode == "register" and existing:
        mode = "login"
    code = f"{secrets.randbelow(1000000):06d}"
    challenge_id = secrets.token_urlsafe(24)
    payload = {
        "email": email,
        "phone": phone,
        "mode": mode,
        "full_name": (full_name or "").strip()[:140],
        "code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "attempts": 0,
        "created_at": time.time(),
    }
    frappe.cache().set_value(_cache_key(OTP_PREFIX, challenge_id), payload, expires_in_sec=OTP_TTL)
    channel = _send_code(email, phone, code)
    return {"challenge_id": challenge_id, "channel": channel, "expires_in": OTP_TTL, "mode": mode}


@frappe.whitelist(allow_guest=True)
def verify_otp(challenge_id=None, code=None, full_name=None):
    set_cors_headers()
    challenge_id = str(challenge_id or "").strip()
    code = str(code or "").strip()
    if not challenge_id or not re.fullmatch(r"[0-9]{6}", code):
        frappe.throw("Enter the six-digit verification code.")
    key = _cache_key(OTP_PREFIX, challenge_id)
    payload = frappe.cache().get_value(key)
    if not payload:
        frappe.throw("This verification code has expired. Please request a new code.")
    if isinstance(payload, str):
        import json
        payload = json.loads(payload)
    attempts = int(payload.get("attempts") or 0)
    if attempts >= OTP_MAX_ATTEMPTS:
        frappe.cache().delete_value(key)
        frappe.throw("Too many incorrect attempts. Please request a new code.")
    expected = payload.get("code_hash") or ""
    actual = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if not secrets.compare_digest(expected, actual):
        payload["attempts"] = attempts + 1
        frappe.cache().set_value(key, payload, expires_in_sec=max(1, OTP_TTL - int(time.time() - float(payload.get("created_at") or time.time()))))
        frappe.throw("The verification code is incorrect.")
    frappe.cache().delete_value(key)
    email = payload.get("email") or ""
    phone = payload.get("phone") or ""
    customer = _lookup_customer(email=email, phone=phone)
    if not customer:
        customer_name = _create_customer(email, phone, full_name or payload.get("full_name") or "Customer")
    else:
        customer_name = customer.name
    profile = _customer_profile(customer_name)
    token = secrets.token_urlsafe(32)
    session = {"customer": customer_name, "profile": profile, "created_at": time.time(), "expires_at": time.time() + SESSION_TTL}
    frappe.cache().set_value(_cache_key(SESSION_PREFIX, token), session, expires_in_sec=SESSION_TTL)
    frappe.local.cookie_manager.set_cookie("sync_webshop_account", token, max_age=SESSION_TTL, httponly=True, samesite="Lax")
    return {"authenticated": True, "profile": profile, "expires_in": SESSION_TTL}


@frappe.whitelist(allow_guest=True)
def get_current_account():
    set_cors_headers()
    authenticated = get_authenticated_customer()
    if not authenticated:
        return {"authenticated": False, "profile": None}
    return {"authenticated": True, "profile": authenticated["profile"], "expires_in": SESSION_TTL}


@frappe.whitelist(allow_guest=True)
def logout():
    set_cors_headers()
    token = frappe.get_request_header("X-Sync-Account-Session") or frappe.request.cookies.get("sync_webshop_account")
    if token:
        frappe.cache().delete_value(_cache_key(SESSION_PREFIX, token))
    frappe.local.cookie_manager.delete_cookie("sync_webshop_account")
    return {"authenticated": False}


@frappe.whitelist(allow_guest=True)
def customer_login():
    """Compatibility wrapper: the account page now uses request_otp and verify_otp."""
    set_cors_headers()
    frappe.throw("Use the secure one-time verification flow instead of direct customer login.")
