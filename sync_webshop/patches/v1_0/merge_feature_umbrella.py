import frappe


MERGES = {
    "Webshop AI Chat Settings": {
        "enabled": "ai_chat_enabled",
        "provider": "ai_chat_provider",
        "api_key": "ai_chat_api_key",
        "api_base_url": "ai_chat_api_base_url",
        "model": "ai_chat_model",
        "system_prompt": "ai_chat_system_prompt",
        "greeting_message": "ai_chat_greeting_message",
        "primary_color": "ai_chat_primary_color",
        "allow_guest": "ai_chat_allow_guest",
        "rate_limit_per_minute": "ai_chat_rate_limit_per_minute",
        "max_message_length": "ai_chat_max_message_length",
        "max_tokens": "ai_chat_max_tokens",
        "temperature": "ai_chat_temperature",
        "prevent_sensitive_data": "ai_chat_prevent_sensitive_data",
    },
    "Webshop Marketplace Settings": {
        "amazon_sa_enabled": "marketplace_amazon_sa_enabled",
        "amazon_seller_id": "marketplace_amazon_seller_id",
        "amazon_mws_token": "marketplace_amazon_mws_token",
        "noon_enabled": "marketplace_noon_enabled",
        "noon_partner_id": "marketplace_noon_partner_id",
        "noon_api_key": "marketplace_noon_api_key",
        "sync_interval_minutes": "marketplace_sync_interval_minutes",
        "multi_vendor_enabled": "marketplace_multi_vendor_enabled",
        "commission_percent": "marketplace_commission_percent",
        "affiliate_enabled": "marketplace_affiliate_enabled",
    },
    "Webshop Master Tier Settings": {
        "enabled": "master_tier_enabled",
        "ghost_search_enabled": "master_ghost_search_enabled",
        "loyalty_enabled": "master_loyalty_enabled",
        "referrals_enabled": "master_referrals_enabled",
        "hotspots_enabled": "master_hotspots_enabled",
        "abandoned_cart_enabled": "master_abandoned_cart_enabled",
        "ai_seo_enabled": "master_ai_seo_enabled",
        "points_per_currency": "master_points_per_currency",
        "wallet_value_per_point": "master_wallet_value_per_point",
        "min_redeem_points": "master_min_redeem_points",
        "referral_reward_points": "master_referral_reward_points",
        "referral_code_prefix": "master_referral_code_prefix",
        "recovery_delay_hours": "master_recovery_delay_hours",
        "recovery_coupon_percent": "master_recovery_coupon_percent",
        "style_profile_retention_days": "master_style_profile_retention_days",
    },
}


def _raw(doctype, field):
    return frappe.db.sql(
        "SELECT value FROM `tabSingles` WHERE doctype=%s AND field=%s LIMIT 1",
        (doctype, field),
    )


def _copy(source, target, mapping):
    copied = 0
    source_meta = frappe.get_meta(source)
    target_meta = frappe.get_meta(target)
    for source_field, target_field in mapping.items():
        if not source_meta.has_field(source_field) or not target_meta.has_field(target_field):
            continue
        value = _raw(source, source_field)
        if value and not _raw(target, target_field):
            frappe.db.set_single_value(target, target_field, value[0][0], update_modified=False)
            copied += 1
    return copied


def execute():
    copied = 0
    deleted = 0
    target = "Webshop Feature Settings"
    for source, mapping in MERGES.items():
        if frappe.db.exists("DocType", source) and frappe.db.exists("DocType", target):
            copied += _copy(source, target, mapping)
    for source in MERGES:
        if frappe.db.exists("DocType", source):
            frappe.delete_doc("DocType", source, force=True, ignore_permissions=True)
            deleted += 1
    frappe.db.commit()
    frappe.clear_cache()
    return {"copied_fields": copied, "deleted_doctypes": deleted}
