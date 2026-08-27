import frappe

from sync_webshop.api.auth import get_authenticated_customer
from sync_webshop.api.catalog import _get_price_list, _get_stock, _get_prices
from sync_webshop.api.utils import full_url, get_json_cache, set_cors_headers, set_json_cache


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




def _password_present(doc, fieldname):
    if not doc:
        return False
    try:
        return bool(doc.get_password(fieldname))
    except Exception:
        return bool(doc.get(fieldname))


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
        import json
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
    """Validate a native ERPNext Coupon Code and calculate its discount."""
    code = str(coupon_code or "").strip()
    if not code:
        return {"coupon_code": None, "discount_amount": 0, "coupon": None, "pricing_rule": None}

    if not frappe.db.exists("DocType", "Webshop Content Settings"):
        frappe.throw("Webshop checkout settings are not installed.")
    settings = frappe.get_single("Webshop Content Settings")
    if not getattr(settings, "enable_coupons", 0):
        frappe.throw("Coupons are currently disabled.")

    coupon = frappe.db.get_value(
        "Coupon Code",
        {"coupon_code": code},
        ["name", "coupon_code", "pricing_rule", "valid_from", "valid_upto", "maximum_use", "used"],
        as_dict=True,
    )
    if not coupon:
        frappe.throw("Invalid coupon code.")

    today = frappe.utils.getdate(frappe.utils.nowdate())
    if coupon.valid_from and frappe.utils.getdate(coupon.valid_from) > today:
        frappe.throw("This coupon is not active yet.")
    if coupon.valid_upto and frappe.utils.getdate(coupon.valid_upto) < today:
        frappe.throw("This coupon has expired.")
    if coupon.maximum_use and int(coupon.used or 0) >= int(coupon.maximum_use):
        frappe.throw("This coupon has reached its usage limit.")

    if not coupon.pricing_rule or not frappe.db.exists("Pricing Rule", coupon.pricing_rule):
        frappe.throw("This coupon has no valid pricing rule.")
    pricing_rule = frappe.get_doc("Pricing Rule", coupon.pricing_rule)
    if pricing_rule.disable:
        frappe.throw("This coupon is disabled.")
    if pricing_rule.valid_from and frappe.utils.getdate(pricing_rule.valid_from) > today:
        frappe.throw("This coupon is not active yet.")
    if pricing_rule.valid_upto and frappe.utils.getdate(pricing_rule.valid_upto) < today:
        frappe.throw("This coupon has expired.")

    subtotal = max(0.0, float(total_amount or 0))
    discount = 0.0
    if pricing_rule.rate_or_discount == "Discount Amount":
        discount = float(pricing_rule.discount_amount or 0)
    elif pricing_rule.rate_or_discount == "Discount Percentage":
        discount = subtotal * float(pricing_rule.discount_percentage or 0) / 100.0
    discount = min(max(0.0, discount), subtotal)
    return {
        "coupon_code": code,
        "discount_amount": discount,
        "coupon": coupon,
        "pricing_rule": pricing_rule,
    }


@frappe.whitelist(allow_guest=True)
def validate_coupon(coupon_code, total_amount):
    set_cors_headers()
    result = _validate_coupon_data(coupon_code, total_amount)
    return {
        "valid": True,
        "coupon_code": result["coupon_code"],
        "discount_amount": result["discount_amount"],
        "pricing_rule": result["pricing_rule"].name if result["pricing_rule"] else None,
    }


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

    cached = get_json_cache("checkout_settings", {})
    if cached:
        return cached

    settings = frappe.get_single("Webshop API Settings")
    payment_settings = frappe.get_single("Webshop Payment Settings")

    gateways = []

    # Stripe
    if getattr(payment_settings, "stripe_enabled", 0):
        gateways.append({
            "name": "stripe",
            "label": "Stripe (Card / Apple Pay / Google Pay)",
            "currency": getattr(payment_settings, "stripe_currency", "gbp"),
            "publishable_key": getattr(payment_settings, "stripe_publishable_key", None),
        })

    # Paymob Sub-methods
    regional_payment_options = []
    payment_channels = [
        ("visa", "Visa / Credit Card", "بطاقة الائتمان / فيزا"),
        ("wallet", "Mobile Wallet", "محفظة إلكترونية"),
        ("value", "valU (Installments)", "تطبيقات التقسيط (valu)"),
        ("tabby", "Tabby (Pay in 4)", "تابي (ادفع لاحقاً)"),
        ("tamara", "Tamara (Split in 3)", "تمارا (مقسّط)"),
        ("mada", "Mada Debit Card", "بطاقة مدى"),
        ("apple_pay", "Apple Pay", "Apple Pay"),
    ]
    for channel_name, default_en, default_ar in payment_channels:
        enabled_field = f"{channel_name}_enabled"
        integration_field = f"{channel_name}_integration_id"
        if getattr(payment_settings, enabled_field, 0) and str(getattr(payment_settings, integration_field, "") or "").strip():
            label_en = getattr(payment_settings, f"{channel_name}_label_en", default_en)
            label_ar = getattr(payment_settings, f"{channel_name}_label_ar", default_ar)
            icon = getattr(payment_settings, f"{channel_name}_icon", None)
            regional_payment_options.append({
                "name": channel_name,
                "label": label_en,
                "label_en": label_en,
                "label_ar": label_ar,
                "icon": full_url(icon) if icon else None,
                "status": getattr(payment_settings, "paymob_mode", "Test") or "Test",
            })

    # Do not show a payment option that cannot start Unified Checkout. Credentials
    # remain private; this boolean is evaluated only on the server.
    paymob_ready = (
        bool(getattr(payment_settings, "paymob_enabled", 0))
        and _password_present(payment_settings, "paymob_api_key")
        and bool(str(getattr(payment_settings, "paymob_public_key", "") or "").strip())
        and bool(regional_payment_options)
    )
    if paymob_ready:
        gateways.append({
            "name": "paymob",
            "label": "Online Payment (Paymob)",
            "label_ar": "الدفع الإلكتروني (بايموب)",
            "currency": getattr(payment_settings, "paymob_currency", "EGP") or "EGP",
            "methods": regional_payment_options,
            "configuration_ready": True,
        })

    # Cash on Delivery
    if getattr(payment_settings, "cod_enabled", 0):
        gateways.append({
            "name": "cod",
            "label": getattr(payment_settings, "cod_label_en", "Cash on Delivery"),
            "label_ar": getattr(payment_settings, "cod_label_ar", "الدفع عند الاستلام"),
            "currency": "SAR",
        })

    # Get warehouses
    warehouses = []
    try:
        pickup_warehouses = settings.get("pickup_warehouses")
        if pickup_warehouses:
            warehouses = [{"name": w.warehouse, "label": w.label or w.warehouse} for w in pickup_warehouses]
    except Exception:
        pass

    if not warehouses:
        all_warehouses = frappe.get_all("Warehouse", filters={"is_group": 0}, fields=["name", "warehouse_name"])
        warehouses = [{"name": w.name, "label": w.warehouse_name or w.name} for w in all_warehouses[:5]]

    data = {
        "currency": getattr(payment_settings, "paymob_currency", None) or "SAR",
        "checkout_require_city_governorate": bool(getattr(settings, "checkout_require_city_governorate", False)),
        "checkout_require_second_phone": bool(getattr(settings, "checkout_require_second_phone", False)),
        "coupon_placeholder_en": getattr(settings, "coupon_placeholder_en", "Enter coupon code"),
        "coupon_placeholder_ar": getattr(settings, "coupon_placeholder_ar", "أدخل كود الخصم"),
        "delivery_settings": {
            "min_days": getattr(settings, "min_delivery_days", 1),
            "max_days": getattr(settings, "max_delivery_days", 5),
        },
        "fulfillment": {
            "pickup_enabled": bool(getattr(settings, "enable_pickup", True)),
            "pickup_title_en": getattr(settings, "pickup_title_en", "Store pickup"),
            "pickup_title_ar": getattr(settings, "pickup_title_ar", "الاستلام من المتجر"),
            "pickup_note_en": getattr(settings, "pickup_note_en", "Choose an available warehouse and collect your order there."),
            "pickup_note_ar": getattr(settings, "pickup_note_ar", "اختر مستودعاً متاحاً لاستلام طلبك منه."),
            "warehouses": warehouses
        },
        "payment_gateways": gateways,
        "shipping_rules": [
            {
                "name": r.shipping_rule,
                "shipping_cost": r.shipping_cost,
                "free_shipping_threshold": r.free_shipping_threshold
            } for r in settings.get("shipping_rules", [])
        ] if hasattr(settings, "shipping_rules") else [],
        "regional_payment_options": regional_payment_options
    }

    return set_json_cache("checkout_settings", {}, data)

@frappe.whitelist(allow_guest=True)
def create_order(customer, items, payment_method=None, stripe_payment_intent=None, delivery_date=None, coupon_code=None, governorate=None, city=None, location=None, second_phone=None, gift_message=None, gift_wrap=False, fulfillment_method=None, pickup_warehouse=None, submit=False):
    set_cors_headers()
    rows = _normalise_items(items)
    customer = customer if isinstance(customer, dict) else {}
    authenticated = get_authenticated_customer()
    if authenticated:
        profile = authenticated["profile"]
        customer = {**customer, "name": profile.get("customer_name") or customer.get("name"), "email": profile.get("email") or customer.get("email"), "phone": profile.get("phone") or customer.get("phone")}
    checkout_settings = frappe.get_single("Webshop API Settings")
    governorate = governorate or customer.get("governorate")
    city = city or customer.get("city")
    location = location or customer.get("location")
    second_phone = second_phone or customer.get("second_phone")
    gift_message = gift_message if gift_message is not None else customer.get("gift_message")
    gift_wrap = bool(gift_wrap or customer.get("gift_wrap"))
    fulfillment_method = str(fulfillment_method or customer.get("fulfillment_method") or "Delivery").strip()
    pickup_warehouse = str(pickup_warehouse or customer.get("pickup_warehouse") or "").strip()
    if getattr(checkout_settings, "checkout_require_city_governorate", 0):
        governorate, city = _validate_territory(governorate, city)
    if getattr(checkout_settings, "checkout_require_second_phone", 0) and not str(second_phone or "").strip():
        frappe.throw("A second phone number is required.")
    company = _get_default_company()
    if fulfillment_method not in {"Delivery", "Store Pickup"}:
        frappe.throw("Invalid fulfillment method.")
    pickup_enabled = bool(getattr(checkout_settings, "pickup_enabled", 0))
    if fulfillment_method == "Store Pickup":
        if not pickup_enabled:
            frappe.throw("Store pickup is currently disabled.")
        warehouse = frappe.db.get_value("Warehouse", {"name": pickup_warehouse, "is_group": 0, "disabled": 0}, "name") if pickup_warehouse else None
        if not warehouse:
            frappe.throw("Please select an available pickup warehouse.")
    else:
        warehouse = _get_default_warehouse(company)
    if not company:
        frappe.throw("No default company is configured in ERPNext.")
    if not warehouse:
        frappe.throw("No active selling warehouse is configured for the default company.")

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
        if available is not None and available > 0 and available < row["qty"]:
            frappe.throw(f"Only {available:g} units of {item_code} are currently available.")
        price = prices.get(item_code)
        if not price:
            frappe.throw(f"No selling price is configured for {item_code}.")
        total_amount += float(price["rate"] or 0) * row["qty"]
        order_lines.append({
            "item_code": item_code,
            "qty": row["qty"],
            "warehouse": warehouse,
            "rate": price["rate"],
        })

    coupon = _validate_coupon_data(coupon_code or customer.get("coupon_code"), total_amount)
    coupon_discount = coupon["discount_amount"]

    shipping_cost = 0
    shipping_rule = frappe.db.get_value(
        "Webshop Shipping Rule",
        {"enabled": 1},
        ["shipping_cost", "free_shipping_threshold"],
        as_dict=1,
    )
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
    if so.meta.has_field("apply_discount_on") and coupon_discount > 0:
        so.apply_discount_on = "Grand Total"
    if so.meta.has_field("discount_amount"):
        so.discount_amount = coupon_discount
    for fieldname, value in {
        "coupon_code": coupon["coupon_code"],
        "webshop_payment_method": payment_method,
        "stripe_payment_intent": stripe_payment_intent,
        "webshop_payment_status": "COD" if payment_method == "cod" else "Pending",
        "webshop_coupon_code": coupon["coupon_code"],
        "webshop_coupon_discount": coupon_discount,
        "webshop_governorate": governorate,
        "webshop_city": city,
        "webshop_location": location,
        "webshop_second_phone": second_phone,
        "webshop_is_gift": bool(gift_message or gift_wrap),
        "webshop_gift_wrap": gift_wrap,
        "webshop_gift_message": gift_message,
        "webshop_fulfillment_method": fulfillment_method,
        "webshop_pickup_warehouse": pickup_warehouse if fulfillment_method == "Store Pickup" else None,
    }.items():
        if so.meta.has_field(fieldname):
            so.set(fieldname, value)
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
    if frappe.utils.cint(submit):
        so.submit()
    return {
        "sales_order": so.name,
        "customer": customer_name,
        "status": so.status,
        "grand_total": so.grand_total,
        "currency": so.currency,
        "shipping_cost": shipping_cost,
        "fulfillment_method": fulfillment_method,
        "pickup_warehouse": pickup_warehouse if fulfillment_method == "Store Pickup" else None,
        "coupon_code": coupon["coupon_code"],
        "coupon_discount": coupon_discount,
        "stock_checked": True,
        "price_list": price_list,
        "authenticated_account": bool(authenticated),
    }
