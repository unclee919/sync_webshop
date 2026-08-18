import frappe
import json
import random
import string

def get_random_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def create_number_card(label, doctype, function="Count", aggregate_function_based_on=None, filters=None):
    name = f"Webshop {label}"
    if frappe.db.exists("Number Card", name):
        doc = frappe.get_doc("Number Card", name)
    else:
        doc = frappe.new_doc("Number Card")
        doc.label = name

    doc.update({
        "document_type": doctype,
        "function": function,
        "aggregate_function_based_on": aggregate_function_based_on,
        "filters_json": frappe.as_json(filters) if filters else "[]",
        "is_public": 1,
        "module": "Sync Webshop"
    })
    doc.save(ignore_permissions=True)
    return name

def create_dashboard_chart():
    name = "Webshop Sales Trend"
    if frappe.db.exists("Dashboard Chart", name):
        return name

    doc = frappe.new_doc("Dashboard Chart")
    doc.chart_name = name
    doc.update({
        "chart_type": "Count",
        "document_type": "Sales Order",
        "based_on": "transaction_date",
        "timespan": "Last Year",
        "time_interval": "Monthly",
        "type": "Line",
        "is_public": 1,
        "filters_json": "[]",
        "module": "Sync Webshop"
    })
    doc.insert(ignore_permissions=True)
    return name

def run_all():
    # 1. Create Assets
    create_number_card("Total Products", "Item")
    create_number_card("Total Orders", "Sales Order")
    create_number_card("Total Customers", "Customer")
    create_number_card("Abandoned Carts", "Webshop Abandoned Cart")
    create_dashboard_chart()

    # 2. Workspace Setup
    workspace_name = "Sync Webshop"

    # Safer delete
    frappe.db.delete("Workspace", {"name": workspace_name})
    frappe.db.delete("Workspace Shortcut", {"parent": workspace_name})
    frappe.db.delete("Workspace Link", {"parent": workspace_name})

    workspace = frappe.new_doc("Workspace")
    workspace.name = workspace_name
    workspace.label = workspace_name
    workspace.title = "Sync Webshop"
    workspace.icon = "shop"
    workspace.module = None
    workspace.public = 1
    workspace.is_standard = 0

    # Define blocks for v15
    blocks = [
        {"id": get_random_id(), "type": "header", "data": {"text": "Sync Webshop Command Center", "level": 2, "col": 12}},
        {"id": get_random_id(), "type": "chart", "data": {"chart_name": "Webshop Sales Trend", "col": 12}},
        {"id": get_random_id(), "type": "spacer", "data": {"col": 12}},

        {"id": get_random_id(), "type": "header", "data": {"text": "Live Store Metrics", "level": 4, "col": 12}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Total Products", "col": 3}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Total Orders", "col": 3}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Total Customers", "col": 3}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Abandoned Carts", "col": 3}},
        {"id": get_random_id(), "type": "spacer", "data": {"col": 12}},

        {"id": get_random_id(), "type": "header", "data": {"text": "Essential Shortcuts", "level": 4, "col": 12}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Item", "col": 3}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Sales Order", "col": 3}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Customer", "col": 3}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Webshop Theme Settings", "col": 3}},
        {"id": get_random_id(), "type": "spacer", "data": {"col": 12}},

        {"id": get_random_id(), "type": "header", "data": {"text": "Store Operations", "level": 4, "col": 12}},
        {"id": get_random_id(), "type": "card", "data": {"card_name": "Sales & Inventory", "col": 4}},
        {"id": get_random_id(), "type": "card", "data": {"card_name": "Storefront Design", "col": 4}},
        {"id": get_random_id(), "type": "card", "data": {"card_name": "Marketing & Support", "col": 4}},
    ]
    workspace.content = json.dumps(blocks)

    # Shortcuts (Internal data for rendering)
    workspace.append("shortcuts", {"label": "Products", "type": "DocType", "link_to": "Item"})
    workspace.append("shortcuts", {"label": "Orders", "type": "DocType", "link_to": "Sales Order"})
    workspace.append("shortcuts", {"label": "Customers", "type": "DocType", "link_to": "Customer"})
    workspace.append("shortcuts", {"label": "Theme Settings", "type": "DocType", "link_to": "Webshop Theme Settings"})

    # Sales & Inventory Card
    workspace.append("links", {"label": "Sales Orders", "link_to": "Sales Order", "link_type": "DocType", "card": "Sales & Inventory"})
    workspace.append("links", {"label": "Customers", "link_to": "Customer", "link_type": "DocType", "card": "Sales & Inventory"})
    workspace.append("links", {"label": "Items (Products)", "link_to": "Item", "link_type": "DocType", "card": "Sales & Inventory"})
    workspace.append("links", {"label": "Item Groups", "link_to": "Item Group", "link_type": "DocType", "card": "Sales & Inventory"})
    workspace.append("links", {"label": "Stock Balance", "link_to": "Stock Balance", "link_type": "Report", "card": "Sales & Inventory"})

    # Storefront Design Card
    workspace.append("links", {"label": "Theme Customizer", "link_to": "Webshop Theme Settings", "link_type": "DocType", "card": "Storefront Design"})
    workspace.append("links", {"label": "Product Page Settings", "link_to": "Webshop Product Settings", "link_type": "DocType", "card": "Storefront Design"})
    workspace.append("links", {"label": "Checkout Settings", "link_to": "Webshop Payment Settings", "link_type": "DocType", "card": "Storefront Design"})
    workspace.append("links", {"label": "SEO & Meta Tags", "link_to": "Webshop SEO Settings", "link_type": "DocType", "card": "Storefront Design"})
    workspace.append("links", {"label": "Footer Layout", "link_to": "Webshop Footer Settings", "link_type": "DocType", "card": "Storefront Design"})

    # Marketing & Support Card
    workspace.append("links", {"label": "Home Content", "link_to": "Webshop Content Settings", "link_type": "DocType", "card": "Marketing & Support"})
    workspace.append("links", {"label": "Hero Banners", "link_to": "Webshop Landing Section", "link_type": "DocType", "card": "Marketing & Support"})
    workspace.append("links", {"label": "Announcement Bar", "link_to": "Webshop Announcement Bar", "link_type": "DocType", "card": "Marketing & Support"})
    workspace.append("links", {"label": "Popups & Offers", "link_to": "Webshop Popup", "link_type": "DocType", "card": "Marketing & Support"})
    workspace.append("links", {"label": "Abandoned Cart Recovery", "link_to": "Webshop Abandoned Cart", "link_type": "DocType", "card": "Marketing & Support"})

    workspace.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Workspace 'Sync Webshop' updated with professional layout.")

if __name__ == "__main__":
    run_all()
