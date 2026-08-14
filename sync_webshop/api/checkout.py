import logging
logger = logging.getLogger("sync_webshop")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("/tmp/sync_checkout.log")
logger.addHandler(fh)
import frappe
import json
import traceback
from sync_webshop.api.catalog import _get_price_list, _get_stock, _get_prices
from sync_webshop.api.utils import get_json_cache, set_cors_headers, set_json_cache

def _get_default_customer_group():
    configured = frappe.db.get_single_value("Selling Settings", "customer_group")
    if configured and not frappe.db.get_value("Customer Group", configured, "is_group"):
        return configured
    return frappe.db.get_value("Customer Group", {"is_group": 0}, "name")

def _get_default_territory():
    configured = frappe.db.get_single_value("Selling Settings", "territory")
    if configured and not frappe.db.get_value("Territory", configured, "is_group"):
        return configured
    return frappe.db.get_value("Territory", {"is_group": 0}, "name")

def _get_default_company():
    return frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")

def _get_default_warehouse(company):
    return frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "disabled": 0}, "name")

def _find_or_create_customer(customer):
    email = (customer.get("email") or "").strip()
    phone = (customer.get("phone") or "").strip()
    second_phone = (customer.get("second_phone") or "").strip()
    full_name = (customer.get("name") or "Guest Customer").strip()

    contact_name = None
    if email:
        contact_name = frappe.db.get_value("Contact", {"email_id": email}, "name")
    if not contact_name and phone:
        contact_name = frappe.db.get_value("Contact", {"phone": phone}, "name")
    if not contact_name and phone:
        contact_name = frappe.db.get_value("Contact", {"mobile_no": phone}, "name")

    if contact_name:
        links = frappe.get_all("Dynamic Link", filters={"parent": contact_name, "parenttype": "Contact", "link_doctype": "Customer"}, fields=["link_name"])
        if links:
            if second_phone and second_phone != phone:
                contact_doc = frappe.get_doc("Contact", contact_name)
                existing_numbers = {row.phone for row in (contact_doc.get("phone_nos") or []) if row.phone}
                if second_phone not in existing_numbers:
                    contact_doc.append("phone_nos", {"phone": second_phone})
                    contact_doc.save(ignore_permissions=True)
            return links[0].link_name

    customer_doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": full_name,
        "customer_type": "Individual",
        "customer_group": _get_default_customer_group(),
        "territory": _get_default_territory(),
    })
    customer_doc.flags.ignore_permissions = True
    customer_doc.insert()

    contact_doc = frappe.get_doc({
        "doctype": "Contact",
        "first_name": full_name,
        "email_ids": [{"email_id": email, "is_primary": 1}] if email else [],
        "phone_nos": ([{"phone": phone, "is_primary_mobile_no": 1}] if phone else []) + ([{"phone": second_phone}] if second_phone and second_phone != phone else []),
        "links": [{"link_doctype": "Customer", "link_name": customer_doc.name}],
    })
    contact_doc.flags.ignore_permissions = True
    contact_doc.insert(ignore_mandatory=True)
    return customer_doc.name

def _normalise_items(items):
    if isinstance(items, str):
        items = json.loads(items)
    if not isinstance(items, list):
        frappe.throw("Cart items must be a list.")
    normalised = []
    for row in items:
        code = row.get("item_code")
        qty = float(row.get("qty") or row.get("quantity") or 1)
        if not code or qty <= 0:
            frappe.throw("Each cart line needs a valid item code and quantity.")
        normalised.append({"item_code": code, "qty": qty})
    return normalised

def _validate_coupon_data(coupon_code, total_amount):
    code = str(coupon_code or "").strip()
    if not code:
        return {"coupon_code": None, "discount_amount": 0, "coupon": None, "pricing_rule": None}

    if not frappe.db.exists("Coupon Code", code):
        return {"coupon_code": None, "discount_amount": 0, "coupon": None, "pricing_rule": None}

    coupon = frappe.get_doc("Coupon Code", code)
    if coupon.valid_from and frappe.utils.getdate(coupon.valid_from) > frappe.utils.getdate():
        frappe.throw("This coupon is not yet active.")
    if coupon.valid_upto and frappe.utils.getdate(coupon.valid_upto) < frappe.utils.getdate():
        frappe.throw("This coupon has expired.")

    pricing_rule = frappe.get_doc("Pricing Rule", coupon.pricing_rule)
    discount = 0
    if pricing_rule.rate_or_discount == "Discount Amount":
        discount = float(pricing_rule.discount_amount or 0)
    elif pricing_rule.rate_or_discount == "Discount Percentage":
        discount = (float(pricing_rule.discount_percentage or 0) / 100) * total_amount

    return {
        "coupon_code": code,
        "discount_amount": discount,
        "coupon": coupon,
        "pricing_rule": pricing_rule,
    }

def _validate_territory(governorate, city):
    governorate = str(governorate or "").strip()
    city = str(city or "").strip()
    if not governorate or not city:
        frappe.throw("Please select a governorate and city.")
    if not frappe.db.exists("Territory", {"name": governorate, "is_group": 1}):
        frappe.throw("The selected governorate is invalid.")
    if not frappe.db.exists("Territory", {"name": city, "parent_territory": governorate, "is_group": 0}):
        frappe.throw("The selected city does not belong to the selected governorate.")
    return governorate, city

@frappe.whitelist(allow_guest=True)
def get_checkout_settings():
    set_cors_headers()
    cached = get_json_cache("checkout-settings", {})
    if cached is not None:
        return cached

    payment_settings = frappe.get_single("Webshop Payment Settings")
    content_settings = frappe.get_single("Webshop Content Settings")

    gateways = []
    if getattr(payment_settings, "stripe_enabled", 0):
        gateways.append({
            "name": "stripe",
            "label": "Stripe (Card / Apple Pay / Google Pay)",
            "currency": getattr(payment_settings, "stripe_currency", "gbp"),
            "publishable_key": getattr(payment_settings, "stripe_publishable_key", None),
        })
    if getattr(payment_settings, "paymob_enabled", 0):
        gateways.append({
            "name": "paymob",
            "label": "Paymob (Online Payment)",
            "currency": getattr(payment_settings, "paymob_currency", "EGP"),
        })
    if getattr(payment_settings, "cod_enabled", 0):
        gateways.append({
            "name": "cod",
            "label": "Cash on Delivery",
            "currency": "SAR",
        })

    # Regional/channel cards are entirely Desk-configurable. A missing field or a
    # false value must never expose a payment option in the storefront.
    regional_payment_options = []
    payment_channels = [
        ("visa_enabled", "visa", "Visa", "Visa"),
        ("wallet_enabled", "wallet", "Mobile Wallet", "محفظة إلكترونية"),
        ("value_enabled", "value", "valu", "valU"),
        ("tabby_enabled", "tabby", "Tabby", "تابي"),
        ("tamara_enabled", "tamara", "Tamara", "تمارا"),
        ("mada_enabled", "mada", "Mada", "مدى"),
        ("apple_pay_enabled", "apple_pay", "Apple Pay", "Apple Pay"),
    ]
    for fieldname, channel_name, label_en, label_ar in payment_channels:
        if getattr(payment_settings, fieldname, 0):
            regional_payment_options.append({
                "name": channel_name,
                "label": label_en,
                "label_en": label_en,
                "label_ar": label_ar,
                "status": "Live",
            })

    pickup_enabled = bool(getattr(content_settings, "pickup_enabled", 0))
    pickup_warehouses = []
    if pickup_enabled:
        warehouses = frappe.get_all(
            "Warehouse",
            filters={"is_group": 0, "disabled": 0},
            fields=["name", "warehouse_name"]
        )
        pickup_warehouses = [{"name": w.name, "label": w.warehouse_name} for w in warehouses]

    shipping_rules = frappe.get_all(
        "Webshop Shipping Rule",
        filters={"enabled": 1},
        fields=["name", "shipping_cost", "free_shipping_threshold"]
    )

    response = {
        "payment_gateways": gateways,
        "regional_payment_options": regional_payment_options,
        "fulfillment": {
            "pickup_enabled": pickup_enabled,
            "pickup_title_en": getattr(content_settings, "pickup_title_en", None) or "Store pickup",
            "pickup_title_ar": getattr(content_settings, "pickup_title_ar", None) or "الاستلام من المتجر",
            "pickup_note_en": getattr(content_settings, "pickup_note_en", None) or "Choose an available warehouse and collect your order there.",
            "pickup_note_ar": getattr(content_settings, "pickup_note_ar", None) or "اختر مستودعاً متاحاً لاستلام طلبك منه.",
            "warehouses": pickup_warehouses,
        },
        "shipping_rules": shipping_rules,
        "delivery_settings": {
            "min_days": getattr(content_settings, "min_delivery_days", 1),
            "max_days": getattr(content_settings, "max_delivery_days", 7),
        },
        "checkout_require_city_governorate": bool(getattr(content_settings, "require_city_governorate", 1)),
        "checkout_require_second_phone": bool(getattr(content_settings, "require_second_phone", 1)),
        "coupon_placeholder_en": getattr(content_settings, "coupon_placeholder_en", None) or "Enter coupon code",
        "coupon_placeholder_ar": getattr(content_settings, "coupon_placeholder_ar", None) or "أدخل كود الخصم",
    }
    return set_json_cache("checkout-settings", {}, response, expires_in_sec=120)

@frappe.whitelist(allow_guest=True)
def get_territories():
    set_cors_headers()
    governorates = frappe.get_all(
        "Territory",
        filters={"is_group": 1},
        fields=["name"],
        order_by="name asc",
    )
    result = []
    for governorate in governorates:
        cities = frappe.get_all(
            "Territory",
            filters={"parent_territory": governorate.name, "is_group": 0},
            fields=["name"],
            order_by="name asc",
        )
        if cities:
            result.append({"governorate": governorate.name, "cities": [city.name for city in cities]})
    return result

@frappe.whitelist(allow_guest=True)
def validate_coupon(coupon_code, total_amount):
    set_cors_headers()
    result = _validate_coupon_data(coupon_code, total_amount)
    return {
        "coupon_code": result["coupon_code"],
        "discount_amount": result["discount_amount"],
        "pricing_rule": result["pricing_rule"].name if result["pricing_rule"] else None,
    }

@frappe.whitelist(allow_guest=True)
def create_order(*args, **kwargs):
    import logging
    l = logging.getLogger("sync_webshop")
    l.debug(f"REQUEST: {frappe.request.method} {frappe.request.url}")
    l.debug(f"HEADERS: {dict(frappe.request.headers)}")
    l.debug(f"COOKIES: {dict(frappe.request.cookies)}")
    l.debug(f"FORM_DICT: {dict(frappe.form_dict)}")
    frappe.local.flags.ignore_csrf = True
    set_cors_headers()
    try:
        # Use frappe.form_dict directly for absolute robustness
        data = frappe.form_dict

        # Parse customer and items if they are JSON strings
        customer = data.get("customer")
        if isinstance(customer, str):
            customer = json.loads(customer)
        elif not customer:
            customer = {}

        items = data.get("items")
        if isinstance(items, str):
            items = json.loads(items)
        elif not items:
            items = []

        if not items:
            frappe.throw("Cart is empty.")

        rows = _normalise_items(items)
        content_settings = frappe.get_single("Webshop Content Settings")

        # Get other fields from data or customer object
        payment_method = data.get("payment_method") or customer.get("payment_method")
        governorate = data.get("governorate") or customer.get("governorate")
        city = data.get("city") or customer.get("city")
        second_phone = data.get("second_phone") or customer.get("second_phone")
        fulfillment_method = data.get("fulfillment_method") or customer.get("fulfillment_method") or "Delivery"
        delivery_date = data.get("delivery_date") or customer.get("delivery_date")
        coupon_code = data.get("coupon_code") or customer.get("coupon_code")
        pickup_warehouse = data.get("pickup_warehouse") or customer.get("pickup_warehouse")
        submit = frappe.utils.cint(data.get("submit") or customer.get("submit") or 0)

        if getattr(content_settings, "require_city_governorate", 0):
            governorate, city = _validate_territory(governorate, city)
        if getattr(content_settings, "require_second_phone", 0) and not str(second_phone or "").strip():
            frappe.throw("A second phone number is required.")

        company = _get_default_company()
        if not company:
            frappe.throw("No default company is configured.")

        if fulfillment_method == "Store Pickup":
            if not pickup_warehouse:
                frappe.throw("Please select a pickup warehouse.")
            warehouse = pickup_warehouse
        else:
            warehouse = _get_default_warehouse(company)

        if not warehouse:
            frappe.throw("No warehouse available for this order.")

        codes = [row["item_code"] for row in rows]
        stock = _get_stock(codes)
        price_list = _get_price_list()
        prices = _get_prices(codes, price_list)

        order_lines = []
        total_amount = 0
        for row in rows:
            item_code = row["item_code"]
            if not frappe.db.exists("Item", {"item_code": item_code, "disabled": 0}):
                frappe.throw(f"Item {item_code} is not available.")

            available = stock.get(item_code, {}).get("available_qty")
            if available is not None and available < row["qty"]:
                frappe.throw(f"Only {available:g} units of {item_code} are available.")

            price = prices.get(item_code)
            if not price:
                frappe.throw(f"No price for {item_code}.")

            total_amount += float(price["rate"]) * row["qty"]
            order_lines.append({
                "item_code": item_code,
                "qty": row["qty"],
                "warehouse": warehouse,
                "rate": price["rate"],
            })

        coupon = _validate_coupon_data(coupon_code, total_amount)
        coupon_discount = coupon["discount_amount"]

        shipping_cost = 0
        shipping_rule = frappe.db.get_value("Webshop Shipping Rule", {"enabled": 1}, ["shipping_cost", "free_shipping_threshold"], as_dict=1)
        if shipping_rule and total_amount < float(shipping_rule.free_shipping_threshold or 0):
            shipping_cost = float(shipping_rule.shipping_cost or 0)

        customer_name = _find_or_create_customer(customer)
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": customer_name,
            "company": company,
            "selling_price_list": price_list,
            "delivery_date": delivery_date or frappe.utils.add_days(frappe.utils.nowdate(), 3),
            "items": order_lines,
        })

        if coupon_discount > 0:
            if so.meta.has_field("apply_discount_on"):
                so.apply_discount_on = "Grand Total"
            if so.meta.has_field("discount_amount"):
                so.discount_amount = coupon_discount

        # Set custom fields
        for field, value in {
            "webshop_payment_method": payment_method,
            "webshop_governorate": governorate,
            "webshop_city": city,
            "webshop_second_phone": second_phone,
            "webshop_fulfillment_method": fulfillment_method,
        }.items():
            if so.meta.has_field(field):
                so.set(field, value)

        if shipping_cost > 0:
            account = frappe.db.get_value("Account", {"account_type": "Tax", "company": company, "is_group": 0}, "name")
            if account:
                so.append("taxes", {
                    "charge_type": "Actual",
                    "account_head": account,
                    "description": "Shipping Charges",
                    "tax_amount": shipping_cost,
                    "add_deduct_tax": "Add",
                })

        so.flags.ignore_permissions = True
        so.insert()
        so.run_method("calculate_taxes_and_totals")
        so.save(ignore_permissions=True)

        if submit:
            so.submit()

        return {
            "sales_order": so.name,
            "customer": customer_name,
            "grand_total": so.grand_total,
            "currency": so.currency,
        }
    except Exception as e:
        frappe.logger().error(f"CHECKOUT ERROR: {str(e)}\n{traceback.format_exc()}")
        frappe.local.response["http_status_code"] = 400
        return {"message": str(e), "exception": traceback.format_exc()}
