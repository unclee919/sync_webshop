import frappe


LEGACY_DOCTYPES = (
    "Webshop Paymob Settings",
    "Webshop Regional Payment Settings",
)

PAYMOB_MAPPING = {
    "enabled": "paymob_enabled",
    "secret_key": "paymob_api_key",
    "public_key": "paymob_public_key",
    "hmac_secret": "paymob_hmac_secret",
    "card_integration_id": "visa_integration_id",
    "wallet_integration_id": "wallet_integration_id",
    "kiosk_integration_id": "paymob_kiosk_integration_id",
    "payment_methods": "paymob_payment_methods",
    "checkout_mode": "paymob_checkout_mode",
    "label_en": "paymob_label_en",
    "label_ar": "paymob_label_ar",
    "online_payment_enabled": "paymob_online_payment_enabled",
    "online_label_en": "paymob_online_label_en",
    "online_label_ar": "paymob_online_label_ar",
    "online_note_en": "paymob_online_note_en",
    "online_note_ar": "paymob_online_note_ar",
    "card_label_en": "paymob_card_label_en",
    "card_label_ar": "paymob_card_label_ar",
    "wallet_label_en": "paymob_wallet_label_en",
    "wallet_label_ar": "paymob_wallet_label_ar",
    "kiosk_label_en": "paymob_kiosk_label_en",
    "kiosk_label_ar": "paymob_kiosk_label_ar",
}

REGIONAL_MAPPING = {
    "regional_live_mode": "regional_live_mode",
    "tabby_enabled": "tabby_enabled",
    "tabby_public_key": "tabby_public_key",
    "tamara_enabled": "tamara_enabled",
    "tamara_token": "tamara_token",
    "mada_enabled": "mada_enabled",
    "apple_pay_enabled": "apple_pay_enabled",
}


def _raw_single_value(doctype, fieldname):
    row = frappe.db.sql(
        "select value from `tabSingles` where doctype=%s and field=%s limit 1",
        (doctype, fieldname),
        as_dict=True,
    )
    return row[0].value if row and row[0].value not in (None, "") else None


def _read_value(doc, fieldname):
    field = doc.meta.get_field(fieldname)
    if field and field.fieldtype == "Password":
        try:
            return doc.get_password(fieldname)
        except Exception:
            return doc.get(fieldname)
    return doc.get(fieldname)


def _copy_mapping(canonical, legacy, mapping):
    copied = []
    for source_field, target_field in mapping.items():
        if not legacy.meta.has_field(source_field) or not canonical.meta.has_field(target_field):
            continue
        if _raw_single_value("Webshop Payment Settings", target_field) is not None:
            continue
        if _raw_single_value(legacy.doctype, source_field) is None:
            continue
        value = _read_value(legacy, source_field)
        if value not in (None, ""):
            canonical.set(target_field, value)
            copied.append(target_field)
    return copied


def execute():
    if not frappe.db.exists("DocType", "Webshop Payment Settings"):
        return

    canonical = frappe.get_single("Webshop Payment Settings")
    copied = []
    if frappe.db.exists("DocType", "Webshop Paymob Settings"):
        copied.extend(_copy_mapping(canonical, frappe.get_single("Webshop Paymob Settings"), PAYMOB_MAPPING))
    if frappe.db.exists("DocType", "Webshop Regional Payment Settings"):
        copied.extend(_copy_mapping(canonical, frappe.get_single("Webshop Regional Payment Settings"), REGIONAL_MAPPING))

    # Preserve an old API key separately when it is distinct from the old secret key.
    # It is not used by the current runtime, but retaining it avoids silent data loss.
    if frappe.db.exists("DocType", "Webshop Paymob Settings") and canonical.meta.has_field("paymob_legacy_api_key"):
        legacy = frappe.get_single("Webshop Paymob Settings")
        if _raw_single_value("Webshop Payment Settings", "paymob_legacy_api_key") is None and _raw_single_value(legacy.doctype, "api_key") is not None:
            value = _read_value(legacy, "api_key")
            if value not in (None, ""):
                canonical.set("paymob_legacy_api_key", value)
                copied.append("paymob_legacy_api_key")

    if copied:
        canonical.save(ignore_permissions=True)

    for doctype in LEGACY_DOCTYPES:
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc("DocType", doctype, ignore_permissions=True, force=True)

    frappe.db.commit()
    frappe.clear_cache()
