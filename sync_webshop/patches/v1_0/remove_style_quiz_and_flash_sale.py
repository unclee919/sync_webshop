import frappe


TARGETS = (
    ("Webshop Style Quiz Question", "tabWebshop Style Quiz Question"),
    ("Webshop Flash Sale Item", "tabWebshop Flash Sale Item"),
)
OBSOLETE_CONTENT_FIELDS = (
    "style_quiz_enabled",
    "style_quiz_title_en",
    "style_quiz_title_ar",
    "style_quiz_intro_en",
    "style_quiz_intro_ar",
    "master_style_quiz_enabled",
    "flash_sale_enabled",
    "scarcity_threshold",
    "discount_percent",
)


def _table_exists(table_name):
    return bool(frappe.db.sql("SHOW TABLES LIKE %s", (table_name,)))


def _delete_target(doctype, table_name):
    rows_removed = 0
    doctype_removed = 0
    if _table_exists(table_name):
        rows_removed = frappe.db.sql(f"SELECT COUNT(*) FROM `{table_name}`")[0][0]
    if frappe.db.exists("DocType", doctype):
        if _table_exists(table_name):
            frappe.db.sql(f"DELETE FROM `{table_name}`")
        frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
        doctype_removed = 1
    if _table_exists(table_name):
        frappe.db.commit()
        frappe.db.sql(f"DROP TABLE IF EXISTS `{table_name}`")
    return rows_removed, doctype_removed


def execute():
    removed_rows = {}
    deleted_doctypes = 0
    for doctype, table_name in TARGETS:
        rows, deleted = _delete_target(doctype, table_name)
        removed_rows[doctype] = rows
        deleted_doctypes += deleted

    obsolete_single_rows = 0
    if frappe.db.exists("DocType", "Webshop Content Settings"):
        placeholders = ", ".join(["%s"] * len(OBSOLETE_CONTENT_FIELDS))
        obsolete_single_rows = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabSingles` WHERE doctype=%s AND field IN ({placeholders})",
            ("Webshop Content Settings", *OBSOLETE_CONTENT_FIELDS),
        )[0][0]
        frappe.db.sql(
            f"DELETE FROM `tabSingles` WHERE doctype=%s AND field IN ({placeholders})",
            ("Webshop Content Settings", *OBSOLETE_CONTENT_FIELDS),
        )

    frappe.db.commit()
    frappe.clear_cache()
    return {
        "removed_source_rows": removed_rows,
        "deleted_source_doctypes": deleted_doctypes,
        "removed_obsolete_content_single_rows": obsolete_single_rows,
    }
