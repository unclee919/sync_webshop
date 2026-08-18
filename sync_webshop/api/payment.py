"""Compatibility payment endpoints for Sync Webshop.

Paymob is implemented in sync_webshop.api.paymob. This module keeps legacy RPC
names available while avoiding duplicate gateway logic and simulated redirects.
"""

import frappe

from sync_webshop.api.utils import set_cors_headers


@frappe.whitelist(allow_guest=True)
def create_stripe_intent(amount, currency="gbp", customer=None):
    """Create a Stripe PaymentIntent when Stripe is explicitly configured."""
    set_cors_headers()
    settings = frappe.get_single("Webshop Payment Settings")
    if not settings.stripe_enabled:
        frappe.throw("Stripe is not enabled in Webshop Payment Settings.")
    secret_key = settings.get_password("stripe_secret_key")
    if not secret_key:
        frappe.throw("Set the Stripe Secret Key before enabling Stripe checkout.")

    try:
        import stripe
        stripe.api_key = secret_key
        intent = stripe.PaymentIntent.create(
            amount=int(round(float(amount) * 100)),
            currency=str(currency).lower(),
            automatic_payment_methods={"enabled": True},
        )
        return {"client_secret": intent.client_secret}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Stripe intent creation failed")
        frappe.throw("Stripe could not create a payment request.")


@frappe.whitelist(allow_guest=True)
def create_payment_intent(amount, currency="gbp", customer=None):
    """Backward-compatible alias for create_stripe_intent."""
    return create_stripe_intent(amount=amount, currency=currency, customer=customer)


@frappe.whitelist(allow_guest=True)
def stripe_webhook():
    """Validate Stripe events before marking an order as paid."""
    set_cors_headers()
    settings = frappe.get_single("Webshop Payment Settings")
    endpoint_secret = settings.get_password("stripe_webhook_secret")
    if not endpoint_secret:
        frappe.local.response.http_status_code = 503
        return {"error": "Stripe webhook is not configured."}

    try:
        import stripe
        stripe.api_key = settings.get_password("stripe_secret_key")
        event = stripe.Webhook.construct_event(
            frappe.request.get_data(),
            frappe.get_request_header("Stripe-Signature"),
            endpoint_secret,
        )
    except ValueError:
        frappe.local.response.http_status_code = 400
        return {"error": "Invalid payload"}
    except Exception:
        frappe.local.response.http_status_code = 400
        return {"error": "Invalid signature"}

    if event.get("type") == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        sales_order_name = frappe.db.get_value(
            "Sales Order", {"stripe_payment_intent": payment_intent.get("id")}, "name"
        )
        if sales_order_name:
            sales_order = frappe.get_doc("Sales Order", sales_order_name)
            if sales_order.meta.has_field("webshop_payment_status"):
                sales_order.db_set("webshop_payment_status", "Paid")
            sales_order.add_comment("Info", "Payment verified through Stripe webhook.")
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def create_paymob_intention(*args, **kwargs):
    """Delegate legacy callers to the canonical Paymob implementation."""
    from sync_webshop.api.paymob import create_payment_intention
    return create_payment_intention(*args, **kwargs)


@frappe.whitelist(allow_guest=True)
def paymob_webhook():
    """Delegate legacy callers to the canonical verified Paymob webhook."""
    from sync_webshop.api.paymob import paymob_webhook as verified_paymob_webhook
    return verified_paymob_webhook()
