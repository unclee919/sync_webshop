import frappe
from frappe.utils import flt


SOURCE = "Webshop Volume Pricing Rule"
TARGET = "Pricing Rule"
CONTENT = "Webshop Content Settings"


def _currency(price_list=None):
    if price_list:
        currency = frappe.db.get_value("Price List", price_list, "currency")
        if currency:
            return currency
    return frappe.db.get_single_value("Global Defaults", "default_currency") or "SAR"


def _selling_price_list(price_list):
    return bool(price_list and frappe.db.get_value("Price List", price_list, "selling"))


def _standard_name(source_name):
    return f"Sync Volume Pricing - {source_name}"


def _create_rule(row):
    name = _standard_name(row.name)
    if frappe.db.exists(TARGET, name):
        return name, False
    rule = frappe.get_doc(
        {
            "doctype": TARGET,
            "title": f"Volume Pricing - {row.item_code} from {flt(row.minimum_qty)}",
            "apply_on": "Item Code",
            "price_or_product_discount": "Price",
            "selling": 1,
            "buying": 0,
            "disable": 0 if row.enabled else 1,
            "currency": _currency(row.price_list),
            "min_qty": flt(row.minimum_qty),
            "rate_or_discount": "Discount Percentage",
            "discount_percentage": flt(row.discount_percent),
            "for_price_list": row.price_list if _selling_price_list(row.price_list) else None,
        }
    )
    rule.append("items", {"item_code": row.item_code})
    rule.insert(ignore_permissions=True)
    return rule.name, True


def execute():
    created_rules = 0
    removed_rows = 0
    deleted_doctype = 0
    migrated_rule_names = []

    if frappe.db.exists("DocType", SOURCE):
        rows = frappe.db.sql(
            "SELECT name, enabled, item_code, minimum_qty, discount_percent, price_list "
            "FROM `tabWebshop Volume Pricing Rule` ORDER BY name",
            as_dict=True,
        )
        for row in rows:
            rule_name, created = _create_rule(row)
            migrated_rule_names.append(rule_name)
            created_rules += int(created)
        frappe.db.sql("DELETE FROM `tabWebshop Volume Pricing Rule`")
        removed_rows = len(rows)
        frappe.delete_doc("DocType", SOURCE, force=True, ignore_permissions=True)
        deleted_doctype = 1

    # Frappe may retain an empty physical table after deleting a DocType; remove only this backed-up table.
    source_table = frappe.db.sql("SHOW TABLES LIKE %s", ("tabWebshop Volume Pricing Rule",))
    if source_table:
        frappe.db.sql("DROP TABLE IF EXISTS `tabWebshop Volume Pricing Rule`")

    if frappe.db.exists("DocType", CONTENT):
        existing_link = frappe.db.get_single_value(CONTENT, "volume_pricing_rule")
        if not existing_link and len(migrated_rule_names) == 1:
            frappe.db.set_single_value(CONTENT, "volume_pricing_rule", migrated_rule_names[0])

    frappe.db.commit()
    frappe.clear_cache()
    return {
        "created_pricing_rules": created_rules,
        "removed_source_rows": removed_rows,
        "deleted_source_doctype": deleted_doctype,
        "linked_single_rule": migrated_rule_names[0] if len(migrated_rule_names) == 1 else None,
    }
