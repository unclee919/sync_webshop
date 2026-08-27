import json
import re
import secrets
import string

import frappe
from frappe.utils import flt, get_datetime, now_datetime

from sync_webshop.api.portal import _find_customer
from sync_webshop.api.utils import full_url, require_catalog_access, set_cors_headers


DEFAULTS = {
    "enabled": 1,
    "ghost_search_enabled": 1,
    "loyalty_enabled": 1,
    "referrals_enabled": 1,
    "hotspots_enabled": 1,
    "abandoned_cart_enabled": 1,
    "ai_seo_enabled": 1,
    "points_per_currency": 1.0,
    "wallet_value_per_point": 0.1,
    "min_redeem_points": 100.0,
    "referral_reward_points": 50.0,
    "referral_code_prefix": "SYNC",
    "recovery_delay_hours": 2,
    "recovery_coupon_percent": 10.0,
    "style_profile_retention_days": 0,
}


def _settings():
    values = dict(DEFAULTS)
    if not frappe.db.exists("DocType", "Webshop Content Settings"):
        return values
    try:
        doc = frappe.get_single("Webshop Content Settings")
        for key in DEFAULTS:
            value = doc.get(f"master_{key}")
            if value is not None:
                values[key] = value
    except Exception:
        pass
    return values


def _enabled(settings, key):
    return bool(int(settings.get("enabled", 1)) and int(settings.get(key, 1)))


def _json(value, fallback):
    try:
        parsed = json.loads(value or "")
        return parsed if isinstance(parsed, (dict, list)) else fallback
    except Exception:
        return fallback


def _customer(email=None, phone=None):
    return _find_customer(email=email, phone=phone)


def _native_points(customer):
    if not frappe.db.exists("DocType", "Loyalty Point Entry"):
        return 0.0
    meta = frappe.get_meta("Loyalty Point Entry")
    if not meta.has_field("customer") or not meta.has_field("loyalty_points"):
        return 0.0
    rows = frappe.get_all("Loyalty Point Entry", filters={"customer": customer}, fields=["loyalty_points"], limit_page_length=500)
    return round(sum(flt(row.get("loyalty_points")) for row in rows), 2)


def _wallet_rows(customer):
    if not frappe.db.exists("DocType", "Webshop Loyalty Wallet Entry"):
        return []
    return frappe.get_all(
        "Webshop Loyalty Wallet Entry",
        filters={"customer": customer},
        fields=["name", "entry_type", "points", "wallet_amount", "reference_doctype", "reference_name", "note", "creation"],
        order_by="creation desc",
        limit_page_length=100,
    )


def _tier_for_spend(spend):
    if not frappe.db.exists("DocType", "Webshop Membership Tier"):
        return None
    meta = frappe.get_meta("Webshop Membership Tier")
    fields = ["name", "tier_name", "discount_percent", "badge_color"]
    for field in ["tier_code", "minimum_spend", "min_spend", "perks_en", "perks_ar", "sort_order", "points_multiplier"]:
        if meta.has_field(field):
            fields.append(field)
    rows = frappe.get_all("Webshop Membership Tier", filters={"enabled": 1}, fields=fields, order_by="sort_order asc, minimum_spend asc, min_spend asc")
    selected = None
    for row in rows:
        threshold = flt(row.get("minimum_spend") or row.get("min_spend"))
        if spend >= threshold and (selected is None or threshold >= flt(selected.get("minimum_spend") or selected.get("min_spend"))):
            selected = row
    if selected:
        selected["minimum_spend"] = flt(selected.get("minimum_spend") or selected.get("min_spend"))
        return selected
    return rows[0] if rows else None


def _loyalty_snapshot(customer):
    settings = _settings()
    rows = _wallet_rows(customer)
    earned = sum(flt(row.get("points")) for row in rows if row.get("entry_type") in ("Earn", "Adjustment"))
    redeemed = sum(flt(row.get("points")) for row in rows if row.get("entry_type") == "Redeem")
    points = round(max(0, _native_points(customer) + earned - redeemed), 2)
    orders = frappe.get_all("Sales Order", filters={"customer": customer, "docstatus": 1}, fields=["grand_total"], limit_page_length=500)
    spend = round(sum(flt(row.get("grand_total")) for row in orders), 2)
    tier = _tier_for_spend(spend)
    wallet_value = round(points * flt(settings.get("wallet_value_per_point"), 0.1), 2)
    return {
        "points": points,
        "wallet_value": wallet_value,
        "currency": "SAR",
        "total_spend": spend,
        "tier": tier,
        "entries": rows[:50],
        "settings": {
            "points_per_currency": flt(settings.get("points_per_currency"), 1),
            "wallet_value_per_point": flt(settings.get("wallet_value_per_point"), 0.1),
            "min_redeem_points": flt(settings.get("min_redeem_points"), 100),
        },
    }


@frappe.whitelist(allow_guest=True)
def get_master_tier_settings():
    settings = _settings()
    return {
        "enabled": bool(settings["enabled"]),
        "ghost_search_enabled": _enabled(settings, "ghost_search_enabled"),
        "loyalty_enabled": _enabled(settings, "loyalty_enabled"),
        "referrals_enabled": _enabled(settings, "referrals_enabled"),
        "hotspots_enabled": _enabled(settings, "hotspots_enabled"),
        "abandoned_cart_enabled": _enabled(settings, "abandoned_cart_enabled"),
        "ai_seo_enabled": _enabled(settings, "ai_seo_enabled"),
        "points_per_currency": flt(settings["points_per_currency"]),
        "wallet_value_per_point": flt(settings["wallet_value_per_point"]),
        "min_redeem_points": flt(settings["min_redeem_points"]),
        "referral_reward_points": flt(settings["referral_reward_points"]),
    }


@frappe.whitelist(allow_guest=True)
def get_predictive_search(search=None, limit=6):
    set_cors_headers()
    require_catalog_access()
    settings = _settings()
    if not _enabled(settings, "ghost_search_enabled"):
        return {"enabled": False, "query": search or "", "suggestions": [], "ghost": None}
    term = str(search or "").strip()
    if len(term) < 2:
        return {"enabled": True, "query": term, "suggestions": [], "ghost": None}
    safe_limit = max(1, min(int(limit or 6), 12))
    like = f"%{term}%"
    rows = frappe.get_all(
        "Item",
        filters={"disabled": 0},
        or_filters=[["item_code", "like", like], ["item_name", "like", like], ["description", "like", like]],
        fields=["item_code", "item_name", "item_group", "image", "description"],
        limit_page_length=safe_limit,
        order_by="modified desc",
    )
    suggestions = []
    for row in rows:
        price = frappe.db.get_value("Item Price", {"item_code": row.item_code, "selling": 1}, "price_list_rate") or 0
        suggestions.append({
            "item_code": row.item_code,
            "item_name": row.item_name,
            "item_group": row.item_group,
            "image": full_url(row.image) if row.image else None,
            "price": flt(price),
            "currency": "SAR",
        })
    return {"enabled": True, "query": term, "suggestions": suggestions, "ghost": suggestions[0] if suggestions else None}


@frappe.whitelist(allow_guest=True)
def get_hotspots(limit=24):
    set_cors_headers()
    require_catalog_access()
    settings = _settings()
    if not _enabled(settings, "hotspots_enabled") or not frappe.db.exists("DocType", "Webshop Hotspot"):
        return []
    rows = frappe.get_all(
        "Webshop Hotspot",
        filters={"enabled": 1},
        fields=["name", "title_en", "title_ar", "image_url", "item_code", "coord_x", "coord_y"],
        order_by="modified desc",
        limit_page_length=max(1, min(int(limit or 24), 60)),
    )
    result = []
    for row in rows:
        item = None
        if row.item_code and frappe.db.exists("Item", row.item_code):
            item = frappe.db.get_value("Item", row.item_code, ["item_code", "item_name", "image"], as_dict=True)
        result.append({
            "name": row.name,
            "title_en": row.title_en,
            "title_ar": row.title_ar,
            "image_url": full_url(row.image_url) if row.image_url else None,
            "item_code": row.item_code,
            "coord_x": flt(row.coord_x),
            "coord_y": flt(row.coord_y),
            "item": {**item, "image": full_url(item.image) if item and item.image else None} if item else None,
        })
    return result


@frappe.whitelist(allow_guest=True)
def get_loyalty_snapshot(email=None, phone=None):
    set_cors_headers()
    settings = _settings()
    if not _enabled(settings, "loyalty_enabled"):
        return {"enabled": False, "customer": None, "points": 0, "wallet_value": 0, "entries": []}
    customer = _customer(email=email, phone=phone)
    if not customer:
        return {"enabled": True, "customer": None, "points": 0, "wallet_value": 0, "entries": []}
    return {"enabled": True, "customer": customer, **_loyalty_snapshot(customer)}


@frappe.whitelist(allow_guest=True)
def redeem_loyalty_points(points, email=None, phone=None):
    set_cors_headers()
    settings = _settings()
    if not _enabled(settings, "loyalty_enabled"):
        frappe.throw("VIP Loyalty is disabled in Desk settings.")
    customer = _customer(email=email, phone=phone)
    if not customer:
        frappe.throw("Customer verification is required to redeem points.")
    requested = round(flt(points), 2)
    minimum = flt(settings.get("min_redeem_points"), 100)
    snapshot = _loyalty_snapshot(customer)
    if requested < minimum:
        frappe.throw(f"The minimum redemption is {minimum:g} points.")
    if requested > snapshot["points"]:
        frappe.throw("The requested points exceed the available balance.")
    if not frappe.db.exists("DocType", "Webshop Loyalty Wallet Entry"):
        frappe.throw("The loyalty wallet ledger is not installed.")
    amount = round(requested * flt(settings.get("wallet_value_per_point"), 0.1), 2)
    doc = frappe.get_doc({
        "doctype": "Webshop Loyalty Wallet Entry",
        "customer": customer,
        "entry_type": "Redeem",
        "points": requested,
        "wallet_amount": amount,
        "note": "Customer points redemption from the storefront.",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "entry": doc.name, **_loyalty_snapshot(customer)}


def _new_referral_code(prefix):
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(12):
        code = f"{prefix}-{''.join(secrets.choice(alphabet) for _ in range(8))}"
        if not frappe.db.exists("Webshop Referral", {"referral_code": code}):
            return code
    frappe.throw("Unable to create a referral code at this time.")


@frappe.whitelist(allow_guest=True)
def get_referral_hub(email=None, phone=None):
    set_cors_headers()
    settings = _settings()
    if not _enabled(settings, "referrals_enabled"):
        return {"enabled": False, "code": None, "referrals": []}
    customer = _customer(email=email, phone=phone)
    if not customer:
        return {"enabled": True, "customer": None, "code": None, "referrals": []}
    code = None
    if frappe.db.exists("DocType", "Webshop Referral"):
        code = frappe.db.get_value("Webshop Referral", {"referrer_customer": customer}, "referral_code")
        if not code:
            doc = frappe.get_doc({
                "doctype": "Webshop Referral",
                "referral_code": _new_referral_code(str(settings.get("referral_code_prefix") or "SYNC").upper()),
                "referrer_customer": customer,
                "reward_points": flt(settings.get("referral_reward_points"), 50),
                "status": "Pending",
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            code = doc.referral_code
        referrals = frappe.get_all("Webshop Referral", filters={"referrer_customer": customer}, fields=["name", "referral_code", "referred_customer", "status", "reward_points", "first_order", "creation"], order_by="creation desc", limit_page_length=50)
    else:
        referrals = []
    return {"enabled": True, "customer": customer, "code": code, "reward_points": flt(settings.get("referral_reward_points"), 50), "referrals": referrals}


@frappe.whitelist(allow_guest=True)
def claim_referral_code(referral_code, email=None, phone=None):
    set_cors_headers()
    settings = _settings()
    if not _enabled(settings, "referrals_enabled"):
        frappe.throw("Referral Hub is disabled in Desk settings.")
    customer = _customer(email=email, phone=phone)
    code = str(referral_code or "").strip().upper()
    if not customer or not code:
        frappe.throw("Customer verification and a referral code are required.")
    referral = frappe.db.get_value("Webshop Referral", {"referral_code": code}, ["name", "referrer_customer", "referred_customer", "status"], as_dict=True)
    if not referral:
        frappe.throw("Referral code not found.")
    if referral.referrer_customer == customer:
        frappe.throw("You cannot claim your own referral code.")
    if referral.referred_customer and referral.referred_customer != customer:
        frappe.throw("This referral code has already been claimed.")
    frappe.db.set_value("Webshop Referral", referral.name, {"referred_customer": customer, "status": "Qualified"}, update_modified=True)
    frappe.db.commit()
    return {"ok": True, "status": "Qualified", "referral_code": code}


def _create_wallet_entry(customer, entry_type, points, reference_doctype=None, reference_name=None, note=None):
    if not frappe.db.exists("DocType", "Webshop Loyalty Wallet Entry"):
        return None
    settings = _settings()
    doc = frappe.get_doc({
        "doctype": "Webshop Loyalty Wallet Entry",
        "customer": customer,
        "entry_type": entry_type,
        "points": abs(flt(points)),
        "wallet_amount": round(abs(flt(points)) * flt(settings.get("wallet_value_per_point"), 0.1), 2),
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "note": note,
    })
    doc.insert(ignore_permissions=True)
    return doc


def on_sales_order_submit(doc, method=None):
    """Award points exactly once for a submitted Sales Order and qualify a referral when applicable."""
    settings = _settings()
    if not _enabled(settings, "loyalty_enabled") or not getattr(doc, "customer", None):
        return
    if frappe.db.exists("DocType", "Webshop Loyalty Wallet Entry") and not frappe.db.exists("Webshop Loyalty Wallet Entry", {"reference_doctype": "Sales Order", "reference_name": doc.name, "entry_type": "Earn"}):
        points = flt(getattr(doc, "grand_total", 0)) * flt(settings.get("points_per_currency"), 1)
        _create_wallet_entry(doc.customer, "Earn", points, "Sales Order", doc.name, "Points earned from a completed storefront order.")
    if _enabled(settings, "referrals_enabled") and frappe.db.exists("DocType", "Webshop Referral"):
        referral = frappe.db.get_value("Webshop Referral", {"referred_customer": doc.customer, "status": "Qualified"}, ["name", "referrer_customer", "reward_points"], as_dict=True)
        if referral:
            _create_wallet_entry(referral.referrer_customer, "Earn", flt(referral.reward_points), "Webshop Referral", referral.name, "Referral reward after the first submitted order.")
            frappe.db.set_value("Webshop Referral", referral.name, {"status": "Rewarded", "first_order": doc.name}, update_modified=True)
    frappe.db.commit()


def run_abandoned_cart_recovery():
    """Mark eligible abandoned carts as ready for configured follow-up; external messages remain opt-in."""
    settings = _settings()
    if not _enabled(settings, "abandoned_cart_enabled") or not frappe.db.exists("DocType", "Webshop Abandoned Cart"):
        return {"status": "disabled", "count": 0}
    meta = frappe.get_meta("Webshop Abandoned Cart")
    if not meta.has_field("recovery_stage"):
        return {"status": "unsupported", "count": 0}
    candidates = frappe.get_all("Webshop Abandoned Cart", filters={"recovery_stage": ["in", ["Pending Follow-up", "Ready"]]}, fields=["name", "modified"], limit_page_length=200)
    updated = 0
    delay_hours = max(1, int(settings.get("recovery_delay_hours") or 2))
    threshold = now_datetime()
    for row in candidates:
        modified = get_datetime(row.modified) if row.modified else threshold
        if (threshold - modified).total_seconds() >= delay_hours * 3600:
            frappe.db.set_value("Webshop Abandoned Cart", row.name, {"recovery_stage": "Ready", "recovery_ready_at": threshold}, update_modified=True)
            updated += 1
    frappe.db.commit()
    return {"status": "planned", "count": updated, "delay_hours": delay_hours, "coupon_discount": flt(settings.get("recovery_coupon_percent"))}


@frappe.whitelist()
def seed_master_tier():
    """Create safe bilingual demo configuration without overwriting existing Desk values."""
    if frappe.session.user == "Guest":
        frappe.throw("Guest users cannot seed Master Tier settings.")

    single_defaults = {
        "Webshop Content Settings": {
            **{f"master_{key}": value for key, value in DEFAULTS.items()},
            "seo_automation_enabled": 1,
            "auto_generate_product_meta": 1,
            "include_json_ld": 1,
            "description_max_length": 155,
            "brand_voice_en": "Clear, refined, warm, and practical.",
            "brand_voice_ar": "واضح وأنيق ودافئ وعملي.",
        },
    }
    for doctype, values in single_defaults.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        doc = frappe.get_single(doctype)
        changed = False
        for fieldname, value in values.items():
            if doc.get(fieldname) is None or doc.get(fieldname) == "":
                doc.set(fieldname, value)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Membership Tier"):
        tiers = [
            {"tier_name": "Bronze", "tier_code": "BRONZE", "min_spend": 0, "minimum_spend": 0, "discount_percent": 0, "points_multiplier": 1, "badge_color": "#A97852", "perks_en": "A considered welcome to the club.", "perks_ar": "بداية مدروسة في النادي.", "sort_order": 10, "enabled": 1},
            {"tier_name": "Silver", "tier_code": "SILVER", "min_spend": 1000, "minimum_spend": 1000, "discount_percent": 3, "points_multiplier": 1.25, "badge_color": "#8C99A5", "perks_en": "Early access to selected edits.", "perks_ar": "وصول مبكر إلى مختارات محددة.", "sort_order": 20, "enabled": 1},
            {"tier_name": "Gold", "tier_code": "GOLD", "min_spend": 3000, "minimum_spend": 3000, "discount_percent": 5, "points_multiplier": 1.5, "badge_color": "#C5A059", "perks_en": "Priority support and member pricing.", "perks_ar": "دعم بأولوية وأسعار خاصة للأعضاء.", "sort_order": 30, "enabled": 1},
            {"tier_name": "Platinum", "tier_code": "PLATINUM", "min_spend": 7500, "minimum_spend": 7500, "discount_percent": 8, "points_multiplier": 2, "badge_color": "#5B6573", "perks_en": "Private releases and white-glove support.", "perks_ar": "إصدارات خاصة ودعم فاخر مخصص.", "sort_order": 40, "enabled": 1},
        ]
        for row in tiers:
            existing = frappe.db.get_value("Webshop Membership Tier", {"tier_code": row["tier_code"]}, "name")
            doc = frappe.get_doc("Webshop Membership Tier", existing) if existing else frappe.new_doc("Webshop Membership Tier")
            changed = False
            for fieldname, value in row.items():
                if doc.get(fieldname) is None or doc.get(fieldname) == "":
                    doc.set(fieldname, value)
                    changed = True
            if changed or not existing:
                doc.save(ignore_permissions=True)


    if frappe.db.exists("DocType", "Webshop Hotspot") and not frappe.db.count("Webshop Hotspot"):
        item = frappe.db.get_value("Item", {"disabled": 0}, ["item_code", "item_name", "image"], as_dict=True)
        if item and item.image:
            frappe.get_doc({
                "doctype": "Webshop Hotspot",
                "title_en": item.item_name or "Featured detail",
                "title_ar": item.item_name or "تفصيل مميز",
                "image_url": item.image,
                "item_code": item.item_code,
                "coord_x": 52,
                "coord_y": 48,
                "enabled": 1,
            }).insert(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()
    return {"ok": True, "seeded": True, "tiers": frappe.db.count("Webshop Membership Tier") if frappe.db.exists("DocType", "Webshop Membership Tier") else 0}


@frappe.whitelist(allow_guest=True)
def get_product_seo(item_code, lang="en"):
    set_cors_headers()
    settings = _settings()
    if not _enabled(settings, "ai_seo_enabled") or not frappe.db.exists("DocType", "Item"):
        return {"enabled": False}
    if not item_code or not frappe.db.exists("Item", item_code):
        frappe.throw("Item not found.")
    item = frappe.db.get_value("Item", item_code, ["item_code", "item_name", "description", "item_group", "image", "stock_uom"], as_dict=True)
    seo_settings = {}
    if frappe.db.exists("DocType", "Webshop Content Settings"):
        try:
            seo_settings = frappe.get_single("Webshop Content Settings")
        except Exception:
            seo_settings = {}
    max_length = max(80, min(int(seo_settings.get("description_max_length") or 155), 300))
    description = re.sub(r"<[^>]+>", " ", str(item.description or "")).strip()
    description = re.sub(r"\s+", " ", description)
    if not description:
        description = f"Explore {item.item_name} from our {item.item_group or 'carefully selected'} collection."
    description = description[:max_length].rstrip(" .") + ("…" if len(description) > max_length else ".")
    title = str(item.item_name or item.item_code).strip()
    base_url = frappe.utils.get_url()
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "description": description,
        "sku": item.item_code,
        "category": item.item_group,
        "image": full_url(item.image) if item.image else None,
        "url": f"{base_url}/products/{item.item_code}",
        "brand": {"@type": "Brand", "name": "Sync Webshop"},
    }
    return {"enabled": True, "title": title, "description": description, "image": full_url(item.image) if item.image else None, "structured_data": structured_data, "language": "ar" if str(lang).lower().startswith("ar") else "en"}
