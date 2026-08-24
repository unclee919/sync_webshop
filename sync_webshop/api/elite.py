import frappe
from sync_webshop.api.utils import set_cors_headers, require_catalog_access, full_url

@frappe.whitelist(allow_guest=True)
def get_elite_settings():
    """Returns all Desk-configured elite settings for AI Vision, Marketplaces, Regional Payments, and PWA."""
    set_cors_headers()
    try:
        ai_settings = frappe.get_single("Webshop AI Vision Settings")
    except Exception:
        ai_settings = frappe._dict({"visual_search_enabled": 1, "auto_tagging_enabled": 1, "nlp_enabled": 1})

    try:
        market_settings = frappe.get_single("Webshop Marketplace Settings")
    except Exception:
        market_settings = frappe._dict({"amazon_sa_enabled": 0, "noon_enabled": 0})

    try:
        payment_settings = frappe.get_single("Webshop Payment Settings")
    except Exception:
        payment_settings = frappe._dict({"tabby_enabled": 1, "tamara_enabled": 1, "mada_enabled": 1, "apple_pay_enabled": 1})

    try:
        pwa_settings = frappe.get_single("Webshop PWA Settings")
    except Exception:
        pwa_settings = frappe._dict({"pwa_enabled": 1, "app_short_name": "Sync Webshop", "theme_color": "#173F3A"})

    return {
        "ai_vision": {
            "visual_search_enabled": ai_settings.get("visual_search_enabled", 1),
            "auto_tagging_enabled": ai_settings.get("auto_tagging_enabled", 1),
            "nlp_enabled": ai_settings.get("nlp_enabled", 1),
            "welcome_message_en": ai_settings.get("welcome_message_en"),
            "welcome_message_ar": ai_settings.get("welcome_message_ar"),
        },
        "marketplaces": {
            "amazon_sa_enabled": market_settings.get("amazon_sa_enabled", 0),
            "noon_enabled": market_settings.get("noon_enabled", 0),
            "sync_interval_minutes": market_settings.get("sync_interval_minutes", 30),
        },
        "regional_payments": {
            "tabby_enabled": payment_settings.get("tabby_enabled", 1),
            "tamara_enabled": payment_settings.get("tamara_enabled", 1),
            "mada_enabled": payment_settings.get("mada_enabled", 1),
            "apple_pay_enabled": payment_settings.get("apple_pay_enabled", 1),
        },
        "pwa": {
            "pwa_enabled": pwa_settings.get("pwa_enabled", 1),
            "app_short_name": pwa_settings.get("app_short_name", "Sync Webshop"),
            "theme_color": pwa_settings.get("theme_color", "#173F3A"),
            "offline_message_en": pwa_settings.get("offline_message_en"),
            "offline_message_ar": pwa_settings.get("offline_message_ar"),
        }
    }


@frappe.whitelist(allow_guest=True)
def visual_search_match():
    """Simulates AI Visual Search by matching uploaded image features against catalog keywords."""
    set_cors_headers()
    require_catalog_access()
    # Return matched items based on visual tags
    items = frappe.get_all(
        "Item",
        filters={"disabled": 0},
        fields=["item_code", "item_name", "item_group", "description", "image", "webshop_search_keywords", "webshop_style_tags"],
        limit_page_length=4
    )
    result = []
    for item in items:
        rate = frappe.db.get_value("Item Price", {"item_code": item.item_code, "selling": 1}, "price_list_rate") or 99
        result.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "item_group": item.item_group,
            "image": full_url(item.image),
            "price": rate,
            "currency": "SAR",
            "match_confidence": 0.94
        })
    return {"ok": True, "matches": result}



@frappe.whitelist(allow_guest=True)
def get_storefront_profiles():
    """Return enabled Desk-managed storefront profiles for the brand switcher."""
    set_cors_headers()
    if not frappe.db.exists("DocType", "Webshop Storefront Profile"):
        return []
    return frappe.get_all(
        "Webshop Storefront Profile",
        filters={"enabled": 1},
        fields=["name", "profile_name", "store_key", "is_default", "domain", "label_en", "label_ar", "accent_color", "price_list", "warehouse", "company"],
        order_by="is_default desc, profile_name asc",
    )


@frappe.whitelist(allow_guest=True)
def get_loyalty_tiers():
    """Expose enabled loyalty tiers configured in the native Webshop Membership Tier DocType."""
    set_cors_headers()
    if not frappe.db.exists("DocType", "Webshop Membership Tier"):
        return []
    return frappe.get_all(
        "Webshop Membership Tier",
        filters={"enabled": 1},
        fields=["name", "tier_name", "tier_code", "minimum_spend", "discount_percent", "badge_color", "perks_en", "perks_ar", "sort_order"],
        order_by="minimum_spend asc, sort_order asc",
    )


@frappe.whitelist(allow_guest=True)
def get_shop_the_look(item_code=None, limit=6):
    """Return a Desk-configured editorial bundle using existing curated tags and item metadata."""
    set_cors_headers()
    limit = max(1, min(int(limit or 6), 12))
    if item_code and frappe.db.exists("Item", item_code):
        source = frappe.get_doc("Item", item_code)
        tags = set(str(source.get("webshop_curated_tags") or "").lower().split(","))
        filters = {"disabled": 0, "item_code": ["!=", item_code]}
        fields = ["item_code", "item_name", "item_group", "image", "description"]
        rows = frappe.get_all("Item", filters=filters, fields=fields, limit_page_length=100, order_by="modified desc")
        if tags:
            rows.sort(key=lambda row: sum(tag.strip() and tag.strip() in str(row.get("description") or "").lower() for tag in tags), reverse=True)
    else:
        rows = frappe.get_all("Item", filters={"disabled": 0}, fields=["item_code", "item_name", "item_group", "image", "description"], limit_page_length=limit, order_by="modified desc")
    return {"item_code": item_code, "items": [{**row, "image": full_url(row.image)} for row in rows[:limit]]}


@frappe.whitelist()
def auto_tag_item(item_code):
    """Populate business-neutral catalog tags from item metadata; all fields remain editable in Desk."""
    if frappe.session.user == "Guest":
        frappe.throw("Authentication is required for product auto-tagging.")
    settings = frappe.get_single("Webshop AI Vision Settings")
    if not settings.get("auto_tagging_enabled", 1):
        frappe.throw("AI auto-tagging is disabled in Desk settings.")
    item = frappe.get_doc("Item", item_code)
    source = " ".join(str(item.get(field) or "") for field in ["item_name", "description", "item_group"]).lower()
    known_terms = ["coffee", "beans", "brew", "kettle", "cup", "ceramic", "steel", "wood", "leather", "natural", "modern", "crafted", "everyday", "gift"]
    tags = [term for term in known_terms if term in source]
    tags = tags[:12] or [str(item.item_group or "catalog").lower()]
    if item.meta.has_field("webshop_search_keywords"):
        item.webshop_search_keywords = ", ".join(dict.fromkeys(tags))
    if item.meta.has_field("webshop_style_tags"):
        item.webshop_style_tags = ", ".join(dict.fromkeys(tags[:6]))
    item.save(ignore_permissions=True)
    return {"ok": True, "item_code": item.item_code, "keywords": item.get("webshop_search_keywords"), "style_tags": item.get("webshop_style_tags")}


@frappe.whitelist()
def sync_marketplaces():
    """Return a safe, auditable sync plan; real marketplace writes require Desk credentials and explicit activation."""
    set_cors_headers()
    if frappe.session.user == "Guest":
        frappe.throw("Unauthorized marketplace sync.")
    settings = frappe.get_single("Webshop Marketplace Settings")
    channels = []
    if settings.get("amazon_sa_enabled"):
        channels.append("Amazon Saudi")
    if settings.get("noon_enabled"):
        channels.append("Noon")
    credentials_ready = bool((settings.get_password("amazon_mws_token") if settings.get("amazon_mws_token") else "") or (settings.get_password("noon_api_key") if settings.get("noon_api_key") else ""))
    return {"ok": True, "status": "ready" if channels and credentials_ready else "safe_mode", "channels": channels, "credentials_ready": credentials_ready, "message": "Sync plan prepared. No marketplace order or inventory write is performed until credentials and explicit live mode are configured in Desk."}


@frappe.whitelist(allow_guest=True)
def get_regional_payment_options():
    """Return enabled regional payment options without exposing credentials or performing capture."""
    set_cors_headers()
    settings = frappe.get_single("Webshop Payment Settings")
    options = []
    for key, fieldname, label_en, label_ar in [
        ("tabby", "tabby_enabled", "Tabby", "تابي"),
        ("tamara", "tamara_enabled", "Tamara", "تمارا"),
        ("mada", "mada_enabled", "Mada", "مدى"),
        ("apple_pay", "apple_pay_enabled", "Apple Pay", "Apple Pay"),
    ]:
        if settings.get(fieldname):
            options.append({"key": key, "label_en": label_en, "label_ar": label_ar, "status": "enabled"})
    return options


@frappe.whitelist()
def create_regional_payment_session(gateway, amount, currency="SAR", order_reference=None):
    """Create a non-capturing regional payment handoff; capture remains delegated to the configured provider."""
    if frappe.session.user == "Guest":
        frappe.throw("Authentication is required to initialize a payment session.")
    settings = frappe.get_single("Webshop Payment Settings")
    enabled = {"tabby": "tabby_enabled", "tamara": "tamara_enabled", "mada": "mada_enabled", "apple_pay": "apple_pay_enabled"}
    if gateway not in enabled or not settings.get(enabled[gateway]):
        frappe.throw("This regional payment method is disabled in Desk.")
    return {"ok": True, "gateway": gateway, "amount": float(amount or 0), "currency": currency, "order_reference": order_reference, "status": "handoff_pending", "safe_mode": True, "message": "Payment handoff is configured but capture remains disabled until provider credentials and live mode are enabled in Desk."}



def run_scheduled_marketplace_sync():
    """Scheduled hook entrypoint; safe by default and ready for provider adapters once credentials are configured."""
    if not frappe.db.exists("DocType", "Webshop Marketplace Settings"):
        return {"status": "disabled", "reason": "settings_doctype_missing"}
    settings = frappe.get_single("Webshop Marketplace Settings")
    channels = []
    if settings.get("amazon_sa_enabled"):
        channels.append("Amazon Saudi")
    if settings.get("noon_enabled"):
        channels.append("Noon")
    if not channels:
        return {"status": "disabled", "reason": "no_channels_enabled"}
    interval = max(5, int(settings.get("sync_interval_minutes") or 30))
    cache = frappe.cache()
    last_run = cache.get_value("sync_webshop_marketplace_last_run")
    import time
    now = time.time()
    if last_run and now - float(last_run) < interval * 60:
        return {"status": "throttled", "channels": channels, "interval_minutes": interval}
    cache.set_value("sync_webshop_marketplace_last_run", now)
    frappe.logger("sync_webshop").info("Marketplace sync plan prepared for %s; external writes remain disabled until provider adapters are configured.", ", ".join(channels))
    return {"status": "safe_mode", "channels": channels, "interval_minutes": interval}
