import frappe


MERGES = {
    "Webshop Subscription Settings": {
        "enabled": "subscription_enabled",
        "discount_percent": "subscription_discount_percent",
        "intervals": "subscription_intervals",
    },
    "Webshop Courier Settings": {
        "provider": "courier_provider",
        "api_key": "courier_api_key",
        "auto_waybill": "courier_auto_waybill",
    },
    "Webshop Currency Settings": {
        "auto_detect": "currency_auto_detect",
        "supported_currencies": "supported_currencies",
        "exchange_rates_json": "exchange_rates_json",
    },
    "Webshop Tracking Settings": {
        "enabled": "tracking_enabled",
        "map_enabled": "tracking_map_enabled",
        "courier_name": "tracking_courier_name",
        "tracking_url_template": "tracking_url_template",
        "title_en": "tracking_title_en",
        "title_ar": "tracking_title_ar",
        "status_labels_en": "tracking_status_labels_en",
        "status_labels_ar": "tracking_status_labels_ar",
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
        source_value = _raw(source, source_field)
        if source_value and not _raw(target, target_field):
            frappe.db.set_single_value(target, target_field, source_value[0][0], update_modified=False)
            copied += 1
    return copied


def execute():
    copied = 0
    deleted = 0
    target = "Webshop Commerce Settings"
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
