# Copyright (c) 2026, Sync Webshop and contributors
# For license information, please see license.txt

import frappe


DEFAULT_SETTINGS = {
    "enabled": 1,
    "about_enabled": 1,
    "about_show_in_nav": 1,
    "about_label_en": "About us",
    "about_label_ar": "من نحن",
    "policy_enabled": 1,
    "policy_show_in_nav": 1,
    "policy_label_en": "Our policy",
    "policy_label_ar": "سياساتنا",
    "articles_enabled": 1,
    "articles_show_in_nav": 1,
    "articles_label_en": "Articles",
    "articles_label_ar": "المقالات",
    "qa_enabled": 1,
    "qa_show_in_nav": 1,
    "qa_label_en": "Q&A",
    "qa_label_ar": "الأسئلة والأجوبة",
    "seo_description_en": "Discover the story, policies, and helpful answers from our store.",
    "seo_description_ar": "اكتشف قصتنا وسياساتنا وإجاباتنا المفيدة من متجرنا.",
}


def _get_settings():
    settings = dict(DEFAULT_SETTINGS)
    if not frappe.db.exists("DocType", "Webshop Dynamic Pages Settings"):
        return settings
    try:
        doc = frappe.get_single("Webshop Dynamic Pages Settings")
        settings.update({key: doc.get(key) for key in DEFAULT_SETTINGS if doc.get(key) is not None})
    except Exception:
        # Keep the public storefront available while migrations are being completed.
        pass
    return settings


def _get_single(doctype, defaults):
    values = dict(defaults)
    if not frappe.db.exists("DocType", doctype):
        return values
    try:
        doc = frappe.get_single(doctype)
        values.update({key: doc.get(key) for key in defaults if doc.get(key) is not None})
    except Exception:
        pass
    return values


@frappe.whitelist(allow_guest=True)
def get_dynamic_page_settings():
    return _get_settings()


@frappe.whitelist(allow_guest=True)
def get_about_page():
    settings = _get_settings()
    page = _get_single("Webshop About Settings", {
        "title_en": "About Our Brand",
        "title_ar": "عن علامتنا التجارية",
        "subtitle_en": "A considered way to discover what belongs in your everyday.",
        "subtitle_ar": "طريقة مدروسة لاكتشاف ما يناسب تفاصيل يومك.",
        "hero_image": "",
        "content_en": "<p>We curate thoughtfully selected essentials for modern living.</p>",
        "content_ar": "<p>نختار بعناية فائقة أساسيات الحياة العصرية.</p>",
    })
    page["enabled"] = int(bool(settings.get("enabled") and settings.get("about_enabled")))
    return page


@frappe.whitelist(allow_guest=True)
def get_policy_page():
    settings = _get_settings()
    page = _get_single("Webshop Policy Settings", {
        "title_en": "Our Policy",
        "title_ar": "سياساتنا",
        "subtitle_en": "Clear commitments for every order and every customer.",
        "subtitle_ar": "التزامات واضحة لكل طلب ولكل عميل.",
        "shipping_title_en": "Shipping",
        "shipping_title_ar": "الشحن",
        "shipping_policy_en": "<p>Reliable regional shipping with clear tracking.</p>",
        "shipping_policy_ar": "<p>شحن موثوق في جميع أنحاء المنطقة مع تتبع دقيق.</p>",
        "return_title_en": "Returns & Exchanges",
        "return_title_ar": "الإرجاع والاستبدال",
        "return_policy_en": "<p>Contact our team within 14 days for unused items in their original condition.</p>",
        "return_policy_ar": "<p>تواصل مع فريقنا خلال 14 يوماً للأصناف غير المستخدمة وبحالتها الأصلية.</p>",
        "privacy_title_en": "Privacy",
        "privacy_title_ar": "الخصوصية",
        "privacy_policy_en": "<p>We use customer data only to provide, secure, and improve the shopping experience.</p>",
        "privacy_policy_ar": "<p>نستخدم بيانات العملاء فقط لتقديم تجربة التسوق وتأمينها وتحسينها.</p>",
    })
    page["enabled"] = int(bool(settings.get("enabled") and settings.get("policy_enabled")))
    return page


@frappe.whitelist(allow_guest=True)
def get_articles():
    settings = _get_settings()
    if not settings.get("enabled") or not settings.get("articles_enabled"):
        return []
    if not frappe.db.exists("DocType", "Webshop Article"):
        return []
    return frappe.get_all(
        "Webshop Article",
        filters={"published": 1},
        fields=["name", "title_en", "title_ar", "route", "excerpt_en", "excerpt_ar", "image", "content_en", "content_ar", "creation"],
        order_by="creation desc",
    )


@frappe.whitelist(allow_guest=True)
def get_article(route):
    settings = _get_settings()
    if not settings.get("enabled") or not settings.get("articles_enabled"):
        return {"enabled": 0}
    route = (route or "").strip()
    if not route or not frappe.db.exists("DocType", "Webshop Article"):
        return None
    article = frappe.get_all(
        "Webshop Article",
        filters={"route": route, "published": 1},
        fields=["name", "title_en", "title_ar", "route", "excerpt_en", "excerpt_ar", "image", "content_en", "content_ar", "creation"],
        limit_page_length=1,
    )
    return article[0] if article else None


@frappe.whitelist(allow_guest=True)
def get_qa_items():
    settings = _get_settings()
    if not settings.get("enabled") or not settings.get("qa_enabled"):
        return []
    if not frappe.db.exists("DocType", "Webshop QA Item"):
        return []
    return frappe.get_all(
        "Webshop QA Item",
        filters={"published": 1},
        fields=["name", "question_en", "question_ar", "answer_en", "answer_ar", "category", "sort_order"],
        order_by="sort_order asc, creation asc",
    )
