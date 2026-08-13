import json

import frappe

from sync_webshop.api.utils import set_cors_headers


def _dashboard_settings():
    defaults = {
        "enable_analytics": True,
        "enable_loyalty": True,
        "enable_profile_edit": True,
        "enable_rma": True,
        "enable_tracking_timeline": True,
        "enable_addresses": True,
        "tracking_labels_en": '{"placed":"Order placed","confirmed":"Confirmed","processing":"Preparing","shipped":"Shipped","delivered":"Delivered"}',
        "tracking_labels_ar": '{"placed":"تم تقديم الطلب","confirmed":"تم التأكيد","processing":"قيد التجهيز","shipped":"تم الشحن","delivered":"تم التسليم"}',
    }
    if not frappe.db.exists("DocType", "Webshop Dashboard Settings"):
        settings = dict(defaults)
        settings["tracking_labels"] = {"en": json.loads(defaults["tracking_labels_en"]), "ar": json.loads(defaults["tracking_labels_ar"])}
        return settings
    doc = frappe.get_single("Webshop Dashboard Settings")
    settings = {}
    for key, default in defaults.items():
        value = getattr(doc, key, default)
        settings[key] = bool(value) if key.startswith("enable_") else (value or default)
    try:
        settings["tracking_labels"] = {
            "en": json.loads(settings["tracking_labels_en"]),
            "ar": json.loads(settings["tracking_labels_ar"]),
        }
    except (TypeError, ValueError):
        settings["tracking_labels"] = {"en": json.loads(defaults["tracking_labels_en"]), "ar": json.loads(defaults["tracking_labels_ar"])}
    try:
        content_settings = frappe.get_single("Webshop Content Settings")
        settings["membership_enabled"] = bool(getattr(content_settings, "membership_enabled", 1))
        settings["membership_title_en"] = getattr(content_settings, "membership_title_en", None) or "Your membership"
        settings["membership_title_ar"] = getattr(content_settings, "membership_title_ar", None) or "عضويتك"
    except Exception:
        settings["membership_enabled"] = True
        settings["membership_title_en"] = "Your membership"
        settings["membership_title_ar"] = "عضويتك"
    return settings


def _find_customer(email=None, phone=None):
    if frappe.session.user != "Guest":
        email = email or frappe.session.user
    email = (email or "").strip()
    phone = (phone or "").strip()
    contact_name = None
    if email:
        contact_name = frappe.db.get_value("Contact", {"email_id": email}, "name")
    if not contact_name and phone:
        contact_name = frappe.db.get_value("Contact", {"phone": phone}, "name")
    if not contact_name and phone:
        contact_name = frappe.db.get_value("Contact", {"mobile_no": phone}, "name")
    if contact_name:
        link = frappe.db.get_value(
            "Dynamic Link",
            {"parent": contact_name, "parenttype": "Contact", "link_doctype": "Customer"},
            "link_name",
        )
        if link:
            return link
    if email:
        return frappe.db.get_value("Customer", {"email_id": email}, "name")
    return None


def _customer_contact(customer):
    contact_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
        "parent",
    )
    return frappe.get_doc("Contact", contact_name) if contact_name else None


def _customer_profile(customer):
    customer_doc = frappe.get_doc("Customer", customer)
    contact = _customer_contact(customer)
    email = customer_doc.get("email_id")
    phone = customer_doc.get("mobile_no") or customer_doc.get("phone")
    address = None
    if contact:
        email = email or next((row.email_id for row in contact.email_ids if row.email_id), None)
        phone = phone or next((row.phone for row in contact.phone_nos if row.phone), None)
    return {
        "name": customer_doc.name,
        "customer_name": customer_doc.customer_name,
        "email": email or "",
        "phone": phone or "",
        "customer_group": customer_doc.customer_group,
        "territory": customer_doc.territory,
        "contact": contact.name if contact else None,
        "address": address,
    }


def _analytics(customer, orders):
    totals = {
        "total_orders": len(orders),
        "completed_orders": sum(1 for order in orders if order.status in {"Completed", "Closed"}),
        "total_spend": round(sum(float(order.grand_total or 0) for order in orders), 2),
        "currency": orders[0].currency if orders else None,
        "last_order_date": orders[0].transaction_date if orders else None,
    }
    totals["average_order_value"] = round(totals["total_spend"] / totals["total_orders"], 2) if totals["total_orders"] else 0
    return totals


def _tracking_steps(order, settings):
    labels_en = settings.get("tracking_labels", {}).get("en", {})
    labels_ar = settings.get("tracking_labels", {}).get("ar", {})
    steps = ["placed", "confirmed", "processing", "shipped", "delivered"]
    status = str(order.get("status") or "Draft")
    delivery_notes = order.get("delivery_notes") or []
    shipped = bool(delivery_notes) or bool(order.get("tracking_number"))
    delivered = any(str(note.get("status")) in {"Completed", "Closed"} for note in delivery_notes)
    completed = {
        "placed": True,
        "confirmed": status not in {"Draft", "Cancelled"},
        "processing": status not in {"Draft", "Cancelled", "On Hold"},
        "shipped": shipped or status in {"Completed", "Closed"},
        "delivered": delivered or status in {"Completed", "Closed"},
    }
    return [{"key": key, "label_en": labels_en.get(key, key.title()), "label_ar": labels_ar.get(key, key.title()), "complete": completed[key]} for key in steps]


def _customer_addresses(customer):
    if not frappe.db.exists("DocType", "Address"):
        return []
    address_names = frappe.get_all(
        "Dynamic Link",
        filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
        pluck="parent",
        limit_page_length=20,
    )
    if not address_names:
        return []
    fields = [field for field in ["name", "address_title", "address_type", "address_line1", "address_line2", "city", "state", "pincode", "country", "phone", "email_id", "is_primary_address"] if frappe.get_meta("Address").has_field(field)]
    return frappe.get_all("Address", filters={"name": ["in", address_names]}, fields=fields, order_by="is_primary_address desc, modified desc")


def _loyalty(customer):
    if not frappe.db.exists("DocType", "Loyalty Point Entry"):
        return {"points": 0, "entries": []}
    meta = frappe.get_meta("Loyalty Point Entry")
    if not meta.has_field("customer") or not meta.has_field("loyalty_points"):
        return {"points": 0, "entries": []}
    entries = frappe.get_all(
        "Loyalty Point Entry",
        filters={"customer": customer},
        fields=[field for field in ["name", "posting_date", "loyalty_points", "expiry_date", "sales_invoice"] if meta.has_field(field)],
        order_by="posting_date desc",
        limit_page_length=100,
    )
    return {"points": sum(float(row.get("loyalty_points") or 0) for row in entries), "entries": entries}



def _membership(analytics):
    if not frappe.db.exists("DocType", "Webshop Membership Tier"):
        return None
    try:
        settings = frappe.get_single("Webshop Content Settings")
        if not getattr(settings, "membership_enabled", 1):
            return None
        tiers = frappe.get_all("Webshop Membership Tier", filters={"enabled": 1}, fields=["name", "tier_name", "tier_code", "minimum_spend", "discount_percent", "badge_color", "perks_en", "perks_ar", "sort_order"], order_by="minimum_spend desc, sort_order asc")
        spend = float((analytics or {}).get("total_spend") or 0)
        selected = next((tier for tier in tiers if spend >= float(tier.minimum_spend or 0)), None)
        if not selected:
            return {"tier_name": "", "tier_code": "", "minimum_spend": 0, "discount_percent": 0, "badge_color": "#C8A96B", "perks_en": "", "perks_ar": "", "next_tier": tiers[-1] if tiers else None}
        return dict(selected)
    except Exception:
        return None


def _guard_order(order_name, customer):
    order = frappe.db.get_value(
        "Sales Order",
        {"name": order_name, "customer": customer},
        ["name", "customer", "transaction_date", "delivery_date", "status", "grand_total", "currency", "docstatus", "tracking_number", "webshop_payment_status"],
        as_dict=True,
    )
    if not order:
        frappe.throw("Order not found for this customer.")
    return order


@frappe.whitelist(allow_guest=True)
def get_dashboard_settings():
    set_cors_headers()
    return _dashboard_settings()


@frappe.whitelist(allow_guest=True)
def get_customer_portal(email=None, phone=None):
    """Return the complete customer dashboard payload for a verified customer context."""
    set_cors_headers()
    settings = _dashboard_settings()
    customer = _find_customer(email=email, phone=phone)
    if not customer:
        return {"customer": None, "profile": None, "orders": [], "invoices": [], "returns": [], "analytics": None, "loyalty": None, "addresses": [], "settings": settings}

    orders = frappe.get_all(
        "Sales Order",
        filters={"customer": customer},
        fields=["name", "transaction_date", "delivery_date", "status", "grand_total", "currency", "docstatus", "tracking_number", "webshop_payment_status"],
        order_by="creation desc",
        limit_page_length=50,
    )
    for order in orders:
        order["items"] = frappe.get_all(
            "Sales Order Item",
            filters={"parent": order.name},
            fields=["item_code", "item_name", "qty", "rate", "amount"],
        )
        order["delivery_notes"] = frappe.get_all(
            "Delivery Note",
            filters={"against_sales_order": order.name},
            fields=["name", "posting_date", "status", "tracking_number"],
        )
        if settings["enable_tracking_timeline"]:
            order["tracking_timeline"] = _tracking_steps(order, settings)

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer, "docstatus": ["<", 2]},
        fields=["name", "posting_date", "due_date", "status", "grand_total", "outstanding_amount", "currency"],
        order_by="posting_date desc",
        limit_page_length=50,
    )
    for invoice in invoices:
        invoice["pdf_url"] = f"/api/method/sync_webshop.api.portal.get_invoice_pdf?invoice_name={invoice.name}"

    returns = frappe.get_all(
        "Issue",
        filters={"customer": customer, "subject": ["like", "RMA:%"]},
        fields=["name", "subject", "status", "opening_date", "resolution_date"],
        order_by="creation desc",
        limit_page_length=50,
    )
    return {
        "customer": customer,
        "profile": _customer_profile(customer),
        "orders": orders,
        "invoices": invoices,
        "returns": returns,
        "analytics": _analytics(customer, orders) if settings["enable_analytics"] else None,
        "loyalty": _loyalty(customer) if settings["enable_loyalty"] else None,
        "membership": _membership(_analytics(customer, orders)) if settings.get("enable_loyalty") else None,
        "addresses": _customer_addresses(customer) if settings["enable_addresses"] else [],
        "settings": settings,
    }


@frappe.whitelist(allow_guest=True)
def update_customer_profile(profile, email=None, phone=None):
    set_cors_headers()
    settings = _dashboard_settings()
    if not settings["enable_profile_edit"]:
        frappe.throw("Profile editing is disabled.")
    if isinstance(profile, str):
        profile = json.loads(profile)
    if not isinstance(profile, dict):
        frappe.throw("Profile data must be an object.")
    customer = _find_customer(email=email, phone=phone)
    if not customer:
        frappe.throw("Customer verification is required before editing the profile.")
    customer_doc = frappe.get_doc("Customer", customer)
    if profile.get("customer_name"):
        customer_doc.customer_name = str(profile["customer_name"]).strip()[:140]
        customer_doc.save(ignore_permissions=True)
    contact = _customer_contact(customer)
    if contact:
        if profile.get("phone") and contact.meta.has_field("phone_nos"):
            primary = contact.phone_nos[0] if contact.phone_nos else contact.append("phone_nos", {})
            primary.phone = str(profile["phone"]).strip()[:40]
            primary.is_primary_mobile_no = 1
        if profile.get("email") and contact.meta.has_field("email_ids"):
            primary = contact.email_ids[0] if contact.email_ids else contact.append("email_ids", {})
            primary.email_id = str(profile["email"]).strip()[:140]
            primary.is_primary = 1
        contact.save(ignore_permissions=True)
    return {"profile": _customer_profile(customer)}


@frappe.whitelist(allow_guest=True)
def request_return(order_name, item_code, qty=1, reason=None, email=None, phone=None):
    set_cors_headers()
    if not _dashboard_settings()["enable_rma"]:
        frappe.throw("Returns are disabled.")
    customer = _find_customer(email=email, phone=phone)
    if not customer:
        frappe.throw("Customer verification is required before requesting a return.")
    _guard_order(order_name, customer)
    order_item = frappe.db.get_value(
        "Sales Order Item",
        {"parent": order_name, "item_code": item_code},
        ["item_name", "qty"],
        as_dict=True,
    )
    if not order_item:
        frappe.throw("The selected item does not belong to this order.")
    qty = float(qty or 1)
    if qty <= 0 or qty > float(order_item.qty or 0):
        frappe.throw("Return quantity is not valid for this order line.")
    subject = f"RMA: {order_name} / {item_code}"
    existing = frappe.db.get_value("Issue", {"customer": customer, "subject": subject}, "name")
    if existing:
        return {"return_request": existing, "status": frappe.db.get_value("Issue", existing, "status")}
    details = {"sales_order": order_name, "item_code": item_code, "item_name": order_item.item_name, "quantity": qty, "reason": reason or "Customer requested return"}
    issue = frappe.get_doc({"doctype": "Issue", "customer": customer, "subject": subject, "description": json.dumps(details, ensure_ascii=False, indent=2)})
    issue.flags.ignore_permissions = True
    issue.insert(ignore_permissions=True)
    return {"return_request": issue.name, "status": issue.status or "Open"}


@frappe.whitelist(allow_guest=True)
def get_invoice(invoice_name, email=None, phone=None):
    set_cors_headers()
    customer = _find_customer(email=email, phone=phone)
    if not customer:
        frappe.throw("Customer verification is required.")
    invoice = frappe.db.get_value("Sales Invoice", {"name": invoice_name, "customer": customer}, ["name", "posting_date", "due_date", "status", "grand_total", "outstanding_amount", "currency"], as_dict=True)
    if not invoice:
        frappe.throw("Invoice not found for this customer.")
    invoice["items"] = frappe.get_all("Sales Invoice Item", filters={"parent": invoice_name}, fields=["item_code", "item_name", "qty", "rate", "amount"])
    invoice["pdf_url"] = f"/api/method/sync_webshop.api.portal.get_invoice_pdf?invoice_name={invoice.name}"
    return invoice


@frappe.whitelist(allow_guest=True)
def get_invoice_pdf(invoice_name, email=None, phone=None):
    set_cors_headers()
    customer = _find_customer(email=email, phone=phone)
    if not customer or not frappe.db.exists("Sales Invoice", {"name": invoice_name, "customer": customer}):
        frappe.throw("Invoice not found for this customer.")
    pdf = frappe.get_print("Sales Invoice", invoice_name, print_format=None, as_pdf=True)
    frappe.local.response.filename = f"{invoice_name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
    return



def _guard_address(address_name, customer):
    if not address_name:
        return None
    linked = frappe.db.exists("Dynamic Link", {"parent": address_name, "parenttype": "Address", "link_doctype": "Customer", "link_name": customer})
    if not linked:
        frappe.throw("Address not found for this customer.")
    return frappe.get_doc("Address", address_name)


@frappe.whitelist(allow_guest=True)
def save_customer_address(address=None, address_name=None, email=None, phone=None):
    set_cors_headers()
    settings = _dashboard_settings()
    if not settings["enable_addresses"]:
        frappe.throw("Saved addresses are disabled.")
    if isinstance(address, str):
        address = json.loads(address)
    if not isinstance(address, dict):
        frappe.throw("Address data must be an object.")
    customer = _find_customer(email=email, phone=phone)
    if not customer:
        frappe.throw("Customer verification is required before saving an address.")
    doc = _guard_address(address_name, customer) if address_name else frappe.new_doc("Address")
    allowed = ["address_title", "address_type", "address_line1", "address_line2", "city", "state", "pincode", "country", "phone", "email_id", "is_primary_address"]
    for fieldname in allowed:
        if doc.meta.has_field(fieldname) and address.get(fieldname) is not None:
            doc.set(fieldname, str(address[fieldname]).strip()[:255] if fieldname not in {"is_primary_address"} else bool(address[fieldname]))
    if not doc.address_title:
        doc.address_title = customer
    if not doc.address_type:
        doc.address_type = "Shipping"
    if not address_name:
        doc.append("links", {"link_doctype": "Customer", "link_name": customer})
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True) if address_name else doc.insert(ignore_permissions=True)
    return {"address": doc.as_dict(), "addresses": _customer_addresses(customer)}


@frappe.whitelist(allow_guest=True)
def delete_customer_address(address_name, email=None, phone=None):
    set_cors_headers()
    settings = _dashboard_settings()
    if not settings["enable_addresses"]:
        frappe.throw("Saved addresses are disabled.")
    customer = _find_customer(email=email, phone=phone)
    if not customer:
        frappe.throw("Customer verification is required before deleting an address.")
    doc = _guard_address(address_name, customer)
    doc.flags.ignore_permissions = True
    frappe.delete_doc("Address", doc.name, ignore_permissions=True)
    return {"deleted": doc.name, "addresses": _customer_addresses(customer)}
