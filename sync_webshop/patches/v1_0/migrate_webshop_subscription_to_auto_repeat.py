import frappe


SOURCE = "Webshop Subscription"
TARGET = "Auto Repeat"
SUPPORTED_FREQUENCIES = {"Monthly", "Quarterly"}


def _normalise_email(value):
    return str(value or "").strip().lower()


def _valid_reference(row):
    if not row.last_order or not frappe.db.exists("Sales Order", row.last_order):
        return False
    order = frappe.get_doc("Sales Order", row.last_order)
    if not order.items or order.items[0].item_code != row.item_code:
        return False
    if not _normalise_email(order.contact_email) or _normalise_email(order.contact_email) != _normalise_email(row.customer_email):
        return False
    return True


def _create_auto_repeat(row):
    if row.interval not in SUPPORTED_FREQUENCIES or not _valid_reference(row):
        return False
    if frappe.db.exists(TARGET, {"reference_doctype": "Sales Order", "reference_document": row.last_order}):
        return True
    repeat = frappe.get_doc(
        {
            "doctype": TARGET,
            "reference_doctype": "Sales Order",
            "reference_document": row.last_order,
            "frequency": row.interval,
            "start_date": row.next_delivery_date or frappe.utils.today(),
            "disabled": 0 if row.status == "Active" else 1,
            "submit_on_creation": 0,
        }
    )
    repeat.insert(ignore_permissions=True)
    return True


def execute():
    created_or_reused = 0
    skipped_rows = 0
    removed_rows = 0
    deleted_doctype = 0

    if frappe.db.exists("DocType", SOURCE):
        rows = frappe.db.sql(
            "SELECT `name`, `customer_email`, `item_code`, `interval`, `status`, `discount_percent`, `next_delivery_date`, `last_order` "
            "FROM `tabWebshop Subscription` ORDER BY `name`",
            as_dict=True,
        )
        for row in rows:
            if _create_auto_repeat(row):
                created_or_reused += 1
            else:
                skipped_rows += 1
        frappe.db.sql("DELETE FROM `tabWebshop Subscription`")
        removed_rows = len(rows)
        frappe.delete_doc("DocType", SOURCE, force=True, ignore_permissions=True)
        deleted_doctype = 1

    source_table = frappe.db.sql("SHOW TABLES LIKE %s", ("tabWebshop Subscription",))
    if source_table:
        # DROP TABLE causes an implicit commit in MariaDB and must run after prior writes are committed.
        frappe.db.commit()
        frappe.db.sql("DROP TABLE IF EXISTS `tabWebshop Subscription`")

    frappe.db.commit()
    frappe.clear_cache()
    return {
        "created_or_reused_auto_repeats": created_or_reused,
        "skipped_for_backup_review": skipped_rows,
        "removed_source_rows": removed_rows,
        "deleted_source_doctype": deleted_doctype,
    }
