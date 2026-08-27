import frappe


SOURCES = (
    "Webshop Feature Settings",
    "Webshop Commerce Settings",
    "Webshop SEO Settings",
)
LAYOUT_FIELD_TYPES = {"Section Break", "Column Break", "HTML"}


def _raw(doctype, field):
    return frappe.db.sql(
        "SELECT value FROM `tabSingles` WHERE doctype=%s AND field=%s LIMIT 1",
        (doctype, field),
    )


def _copy_same_named_fields(source, target):
    copied = 0
    source_meta = frappe.get_meta(source)
    target_meta = frappe.get_meta(target)
    target_fields = {field.fieldname for field in target_meta.fields}
    for field in source_meta.fields:
        if field.fieldtype in LAYOUT_FIELD_TYPES or field.fieldname not in target_fields:
            continue
        source_value = _raw(source, field.fieldname)
        if source_value and not _raw(target, field.fieldname):
            # set_single_value writes the value without exposing it, including Password fields.
            frappe.db.set_single_value(
                target,
                field.fieldname,
                source_value[0][0],
                update_modified=False,
            )
            copied += 1
    return copied


def execute():
    copied = 0
    deleted = 0
    deleted_single_rows = 0
    target = "Webshop Content Settings"
    for source in SOURCES:
        if frappe.db.exists("DocType", source) and frappe.db.exists("DocType", target):
            copied += _copy_same_named_fields(source, target)
    for source in SOURCES:
        if frappe.db.exists("DocType", source):
            frappe.delete_doc("DocType", source, force=True, ignore_permissions=True)
            deleted += 1
        # DocType deletion can leave orphaned Single rows; remove only these three source keys.
        deleted_single_rows += frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSingles` WHERE doctype=%s",
            (source,),
        )[0][0]
        frappe.db.sql("DELETE FROM `tabSingles` WHERE doctype=%s", (source,))
    frappe.db.commit()
    frappe.clear_cache()
    return {
        "copied_fields": copied,
        "deleted_doctypes": deleted,
        "deleted_single_rows": deleted_single_rows,
    }
