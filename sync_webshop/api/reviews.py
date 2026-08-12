import frappe

from sync_webshop.api.catalog import _get_price_list, _get_prices
from sync_webshop.api.portal import _find_customer, _guard_order
from sync_webshop.api.utils import get_json_cache, set_cors_headers, set_json_cache


def _settings():
    defaults = {
        "reviews_enabled": True,
        "reviews_require_approval": True,
        "reviews_allow_guest": False,
        "reviews_title_en": "Customer reviews",
        "reviews_title_ar": "آراء العملاء",
        "enable_recently_viewed": True,
        "recently_viewed_limit": 8,
    }
    if not frappe.db.exists("DocType", "Webshop Product Settings"):
        return defaults
    doc = frappe.get_single("Webshop Product Settings")
    return {key: getattr(doc, key, default) if not str(key).startswith("enable_") and key not in {"reviews_enabled", "reviews_require_approval", "reviews_allow_guest"} else bool(getattr(doc, key, default)) for key, default in defaults.items()}


def _stats(item_code):
    if not frappe.db.exists("DocType", "Webshop Review"):
        return {"average": 0, "count": 0, "breakdown": {str(rating): 0 for rating in range(1, 6)}}
    rows = frappe.get_all("Webshop Review", filters={"item_code": item_code, "status": "Approved"}, fields=["rating"])
    breakdown = {str(rating): 0 for rating in range(1, 6)}
    for row in rows:
        key = str(max(1, min(5, int(row.rating or 0))))
        breakdown[key] += 1
    return {"average": round(sum(int(row.rating or 0) for row in rows) / len(rows), 1) if rows else 0, "count": len(rows), "breakdown": breakdown}


@frappe.whitelist(allow_guest=True)
def get_product_reviews(item_code, page=1, page_size=10):
    set_cors_headers()
    settings = _settings()
    if not settings["reviews_enabled"]:
        return {"enabled": False, "reviews": [], "stats": _stats(item_code), "settings": settings}
    try:
        page = max(1, int(page or 1))
        page_size = min(50, max(1, int(page_size or 10)))
    except (TypeError, ValueError):
        page, page_size = 1, 10
    cache_payload = {"item_code": item_code, "page": page, "page_size": page_size}
    cached = get_json_cache("reviews", cache_payload)
    if cached is not None:
        return cached
    if not frappe.db.exists("DocType", "Webshop Review"):
        response = {"enabled": True, "reviews": [], "stats": _stats(item_code), "settings": settings}
        return set_json_cache("reviews", cache_payload, response, expires_in_sec=60)
    filters = {"item_code": item_code, "status": "Approved"}
    reviews = frappe.get_all("Webshop Review", filters=filters, fields=["name", "rating", "review_title", "review_text", "display_name", "verified_purchase", "creation"], order_by="creation desc", start=(page - 1) * page_size, page_length=page_size)
    response = {"enabled": True, "reviews": reviews, "stats": _stats(item_code), "page": page, "page_size": page_size, "settings": settings}
    return set_json_cache("reviews", cache_payload, response, expires_in_sec=60)


@frappe.whitelist(allow_guest=True)
def submit_review(item_code, rating, review_text, review_title=None, display_name=None, order_name=None, email=None, phone=None):
    set_cors_headers()
    settings = _settings()
    if not settings["reviews_enabled"]:
        frappe.throw("Product reviews are disabled.")
    customer = _find_customer(email=email, phone=phone)
    if not customer and not settings["reviews_allow_guest"]:
        frappe.throw("Please sign in or provide a verified customer email before submitting a review.")
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        frappe.throw("Rating must be a whole number between 1 and 5.")
    if rating < 1 or rating > 5:
        frappe.throw("Rating must be a whole number between 1 and 5.")
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Product not found.")
    verified_purchase = False
    if order_name and customer:
        _guard_order(order_name, customer)
        verified_purchase = bool(frappe.db.exists("Sales Order Item", {"parent": order_name, "item_code": item_code}))
        if not verified_purchase:
            frappe.throw("The selected product is not part of this order.")
    if customer and frappe.db.exists("DocType", "Webshop Review") and frappe.db.exists("Webshop Review", {"item_code": item_code, "customer": customer, "order_name": order_name or ["is", "not set"]}):
        frappe.throw("You have already reviewed this product for the selected order.")
    review = frappe.get_doc({
        "doctype": "Webshop Review",
        "item_code": item_code,
        "customer": customer,
        "order_name": order_name,
        "rating": rating,
        "review_title": (review_title or "").strip()[:140],
        "review_text": (review_text or "").strip()[:4000],
        "display_name": (display_name or (customer or "Guest")).strip()[:140],
        "status": "Pending" if settings["reviews_require_approval"] else "Approved",
        "verified_purchase": verified_purchase,
    })
    review.flags.ignore_permissions = True
    review.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"review": review.as_dict(), "stats": _stats(item_code), "pending": review.status == "Pending"}
