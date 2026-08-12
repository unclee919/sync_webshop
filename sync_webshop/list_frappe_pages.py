import frappe


def list_pages():
    return frappe.get_all(
        "Page",
        fields=["name", "title", "standard"],
        order_by="name asc",
        limit_page_length=100,
    )
