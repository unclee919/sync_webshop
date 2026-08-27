import frappe


FEATURE_MERGES = {
    "Webshop AI Vision Settings": {
        "visual_search_enabled": "ai_vision_visual_search_enabled",
        "auto_tagging_enabled": "ai_vision_auto_tagging_enabled",
        "ai_model_name": "ai_vision_ai_model_name",
        "confidence_threshold": "ai_vision_confidence_threshold",
        "section_nlp": "ai_vision_section_nlp",
        "nlp_enabled": "ai_vision_nlp_enabled",
        "welcome_message_en": "ai_vision_welcome_message_en",
        "welcome_message_ar": "ai_vision_welcome_message_ar",
    },
    "Webshop Dashboard Settings": {
        "enable_analytics": "dashboard_enable_analytics",
        "enable_loyalty": "dashboard_enable_loyalty",
        "enable_profile_edit": "dashboard_enable_profile_edit",
        "enable_rma": "dashboard_enable_rma",
        "enable_tracking_timeline": "dashboard_enable_tracking_timeline",
        "enable_addresses": "dashboard_enable_addresses",
        "tracking_labels_en": "dashboard_tracking_labels_en",
        "tracking_labels_ar": "dashboard_tracking_labels_ar",
    },
    "Webshop Ecosystem AI Settings": {
        "rag_support_enabled": "ecosystem_rag_support_enabled",
        "demand_forecaster_enabled": "ecosystem_demand_forecaster_enabled",
        "marketing_hub_enabled": "ecosystem_marketing_hub_enabled",
    },
    "Webshop Fintech Settings": {
        "gift_cards_enabled": "fintech_gift_cards_enabled",
        "subscription_box_enabled": "fintech_subscription_box_enabled",
    },
    "Webshop Omnichannel Settings": {
        "bopis_enabled": "omnichannel_bopis_enabled",
        "kiosk_mode_enabled": "omnichannel_kiosk_mode_enabled",
    },
    "Webshop Sensory Settings": {
        "enabled": "sensory_enabled",
        "magnetic_cursor_enabled": "sensory_magnetic_cursor_enabled",
        "cinematic_transitions_enabled": "sensory_cinematic_transitions_enabled",
        "circadian_theme_enabled": "sensory_circadian_theme_enabled",
        "predictive_prefetch_enabled": "sensory_predictive_prefetch_enabled",
        "webxr_ar_enabled": "sensory_webxr_ar_enabled",
        "exploder_3d_enabled": "sensory_exploder_3d_enabled",
    },
    "Webshop PWA Settings": {
        "pwa_enabled": "pwa_enabled",
        "app_short_name": "app_short_name",
        "theme_color": "theme_color",
        "offline_message_en": "offline_message_en",
        "offline_message_ar": "offline_message_ar",
    },
}

CONTENT_MERGES = {
    "Webshop About Settings": {
        "title_en": "about_title_en",
        "title_ar": "about_title_ar",
        "subtitle_en": "about_subtitle_en",
        "subtitle_ar": "about_subtitle_ar",
        "hero_image": "about_hero_image",
        "content_en": "about_content_en",
        "content_ar": "about_content_ar",
    },
    "Webshop Announcement Bar": {
        "enabled": "announcement_enabled",
        "message_en": "announcement_message_en",
        "message_ar": "announcement_message_ar",
        "background_color": "announcement_background_color",
        "text_color": "announcement_text_color",
        "link_url": "announcement_link_url",
        "show_close_button": "announcement_show_close_button",
    },
    "Webshop Footer Settings": {
        "enabled": "footer_enabled",
        "footer_logo": "footer_logo",
        "copyright_en": "footer_copyright_en",
        "copyright_ar": "footer_copyright_ar",
    },
    "Webshop Policy Settings": {
        "title_en": "policy_page_title_en",
        "title_ar": "policy_page_title_ar",
        "subtitle_en": "policy_page_subtitle_en",
        "subtitle_ar": "policy_page_subtitle_ar",
        "shipping_title_en": "shipping_policy_title_en",
        "shipping_title_ar": "shipping_policy_title_ar",
        "shipping_policy_en": "shipping_policy_text_en",
        "shipping_policy_ar": "shipping_policy_text_ar",
        "return_title_en": "returns_policy_title_en",
        "return_title_ar": "returns_policy_title_ar",
        "return_policy_en": "returns_policy_text_en",
        "return_policy_ar": "returns_policy_text_ar",
        "privacy_title_en": "privacy_policy_title_en",
        "privacy_title_ar": "privacy_policy_title_ar",
        "privacy_policy_en": "privacy_policy_text_en",
        "privacy_policy_ar": "privacy_policy_text_ar",
    },
    "Webshop Return Policy": {
        "allowed_days": "return_window_days",
        "policy_text_en": "return_window_policy_text_en",
        "policy_text_ar": "return_window_policy_text_ar",
    },
}


def _raw_single(doctype, fieldname):
    return frappe.db.sql(
        "SELECT value FROM `tabSingles` WHERE doctype=%s AND field=%s LIMIT 1",
        (doctype, fieldname),
    )


def _copy_single_fields(source, target, mapping):
    copied = 0
    source_meta = frappe.get_meta(source)
    target_meta = frappe.get_meta(target)
    for source_field, target_field in mapping.items():
        if not source_meta.has_field(source_field) or not target_meta.has_field(target_field):
            continue
        source_row = _raw_single(source, source_field)
        if not source_row or _raw_single(target, target_field):
            continue
        frappe.db.set_single_value(target, target_field, source_row[0][0], update_modified=False)
        copied += 1
    return copied


def execute():
    target_feature = "Webshop Feature Settings"
    target_content = "Webshop Content Settings"
    target_seo = "Webshop SEO Settings"
    target_marketplace = "Webshop Marketplace Settings"
    copied = 0

    for source, mapping in FEATURE_MERGES.items():
        if frappe.db.exists("DocType", source) and frappe.db.exists("DocType", target_feature):
            copied += _copy_single_fields(source, target_feature, mapping)

    if frappe.db.exists("DocType", "Webshop SEO Automation Settings") and frappe.db.exists("DocType", target_seo):
        copied += _copy_single_fields(
            "Webshop SEO Automation Settings",
            target_seo,
            {
                "enabled": "seo_automation_enabled",
                "auto_generate_product_meta": "auto_generate_product_meta",
                "include_json_ld": "include_json_ld",
                "description_max_length": "description_max_length",
                "brand_voice_en": "brand_voice_en",
                "brand_voice_ar": "brand_voice_ar",
            },
        )

    if frappe.db.exists("DocType", "Webshop Marketplace Vendor Settings") and frappe.db.exists("DocType", target_marketplace):
        copied += _copy_single_fields(
            "Webshop Marketplace Vendor Settings",
            target_marketplace,
            {
                "multi_vendor_enabled": "multi_vendor_enabled",
                "commission_percent": "commission_percent",
                "affiliate_enabled": "affiliate_enabled",
            },
        )

    for source, mapping in CONTENT_MERGES.items():
        if frappe.db.exists("DocType", source) and frappe.db.exists("DocType", target_content):
            copied += _copy_single_fields(source, target_content, mapping)

    to_delete = list(FEATURE_MERGES) + [
        "Webshop SEO Automation Settings",
        "Webshop Marketplace Vendor Settings",
    ] + list(CONTENT_MERGES)
    deleted = 0
    for doctype in to_delete:
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
            deleted += 1

    frappe.db.commit()
    frappe.clear_cache()
    return {"copied_fields": copied, "deleted_doctypes": deleted}
