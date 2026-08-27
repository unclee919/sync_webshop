import frappe
from sync_webshop.api.utils import full_url, set_cors_headers

@frappe.whitelist(allow_guest=True)
def get_luxury_settings():
    set_cors_headers()
    settings = {}
    if frappe.db.exists("DocType", "Webshop Content Settings"):
        try:
            doc = frappe.get_single("Webshop Content Settings")
            settings = {
                "enabled": int(doc.get("sensory_enabled", 1)),
                "magnetic_cursor_enabled": int(doc.get("sensory_magnetic_cursor_enabled", 1)),
                "cinematic_transitions_enabled": int(doc.get("sensory_cinematic_transitions_enabled", 1)),
                "circadian_theme_enabled": int(doc.get("sensory_circadian_theme_enabled", 1)),
                "predictive_prefetch_enabled": int(doc.get("sensory_predictive_prefetch_enabled", 1)),
                "webxr_ar_enabled": int(doc.get("sensory_webxr_ar_enabled", 1)),
                "exploder_3d_enabled": int(doc.get("sensory_exploder_3d_enabled", 1)),
            }
        except Exception:
            pass
    return settings or {
        "enabled": 1,
        "magnetic_cursor_enabled": 1,
        "cinematic_transitions_enabled": 1,
        "circadian_theme_enabled": 1,
        "predictive_prefetch_enabled": 1,
        "webxr_ar_enabled": 1,
        "exploder_3d_enabled": 1,
    }

@frappe.whitelist(allow_guest=True)
def get_live_sessions():
    set_cors_headers()
    if not frappe.db.exists("DocType", "Webshop Live Session"):
        return []
    sessions = frappe.get_all("Webshop Live Session", filters={"is_live": 1}, fields=["name", "title_en", "title_ar", "stream_url", "featured_item", "viewer_count"])
    result = []
    for s in sessions:
        item = None
        if s.featured_item and frappe.db.exists("Item", s.featured_item):
            item_doc = frappe.db.get_value("Item", s.featured_item, ["item_code", "item_name", "image", "standard_rate"], as_dict=True)
            if item_doc:
                item = {
                    "item_code": item_doc.item_code,
                    "item_name": item_doc.item_name,
                    "image": full_url(item_doc.image) if item_doc.image else None,
                    "price": item_doc.standard_rate
                }
        result.append({
            "name": s.name,
            "title_en": s.title_en,
            "title_ar": s.title_ar,
            "stream_url": s.stream_url,
            "viewer_count": s.viewer_count or 342,
            "featured_item": item
        })
    return result

@frappe.whitelist(allow_guest=True)
def get_social_pulse():
    set_cors_headers()
    if not frappe.db.exists("DocType", "Webshop Social Pulse"):
        return [
            {"text_en": "Someone in Riyadh just added Coffee Master Edition", "text_ar": "قام شخص في الرياض بإضافة إصدار القهوة الفاخر", "city": "Riyadh"},
            {"text_en": "New 5-star review from Jeddah", "text_ar": "تقييم جديد 5 نجوم من جدة", "city": "Jeddah"},
        ]
    rows = frappe.get_all("Webshop Social Pulse", filters={"enabled": 1}, fields=["text_en", "text_ar", "city"])
    return rows

@frappe.whitelist(allow_guest=True)
def get_community_wall():
    set_cors_headers()
    if not frappe.db.exists("DocType", "Webshop Community Post"):
        return []
    posts = frappe.get_all("Webshop Community Post", filters={"enabled": 1}, fields=["author_name", "image_url", "caption", "linked_item"])
    result = []
    for p in posts:
        item = None
        if p.linked_item and frappe.db.exists("Item", p.linked_item):
            item_doc = frappe.db.get_value("Item", p.linked_item, ["item_code", "item_name", "image", "standard_rate"], as_dict=True)
            if item_doc:
                item = {
                    "item_code": item_doc.item_code,
                    "item_name": item_doc.item_name,
                    "image": full_url(item_doc.image) if item_doc.image else None,
                    "price": item_doc.standard_rate
                }
        result.append({
            "author_name": p.author_name,
            "image_url": full_url(p.image_url) if p.image_url else None,
            "caption": p.caption,
            "item": item
        })
    return result
