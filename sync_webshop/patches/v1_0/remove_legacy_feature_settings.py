import frappe


LEGACY_DOCTYPES = (
    "Webshop Enterprise AI Settings",
    "Webshop B2B Wholesale Settings",
    "Webshop Live Shopping Settings",
    "Webshop Flash Sale Settings",
    "Webshop Recovery Settings",
    "Webshop Fraud Shield Settings",
    "Webshop Infrastructure Settings",
)


def _has_value(value):
    return value is not None and value != ""


def execute():
    if not frappe.db.exists("DocType", "Webshop Feature Settings"):
        return

    canonical = frappe.get_single("Webshop Feature Settings")
    canonical_fields = {field.fieldname for field in frappe.get_meta("Webshop Feature Settings").fields}
    migrated = []

    for doctype in LEGACY_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        legacy = frappe.get_single(doctype)
        copied = []
        for fieldname in canonical_fields:
            if not legacy.meta.has_field(fieldname):
                continue
            value = legacy.get(fieldname)
            if _has_value(value) and not _has_value(canonical.get(fieldname)):
                canonical.set(fieldname, value)
                copied.append(fieldname)
        if copied:
            migrated.append({"doctype": doctype, "fields": copied})

    if migrated:
        canonical.save(ignore_permissions=True)

    for doctype in LEGACY_DOCTYPES:
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc("DocType", doctype, ignore_permissions=True, force=True)

    frappe.db.commit()
    frappe.clear_cache()
