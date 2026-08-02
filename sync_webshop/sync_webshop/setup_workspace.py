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
        doc = frappe.get_doc("Dashboard Chart", name)
    else:
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
    doc.save(ignore_permissions=True)
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
    if frappe.db.exists("Workspace", workspace_name):
        frappe.delete_doc("Workspace", workspace_name)
    
    workspace = frappe.new_doc("Workspace")
    workspace.label = workspace_name
    workspace.title = "Sync Webshop"
    workspace.icon = "shop"
    workspace.module = "Sync Webshop"
    workspace.public = 1
    workspace.is_standard = 0

    # Define blocks for v15
    blocks = [
        {"id": get_random_id(), "type": "header", "data": {"text": "<span class=\"h2\"><b>Sync Webshop Management</b></span>", "col": 12}},
        {"id": get_random_id(), "type": "chart", "data": {"chart_name": "Webshop Sales Trend", "col": 12}},
        {"id": get_random_id(), "type": "spacer", "data": {"col": 12}},
        
        {"id": get_random_id(), "type": "header", "data": {"text": "<span class=\"h4\"><b>Key Performance Indicators</b></span>", "col": 12}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Total Products", "col": 3}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Total Orders", "col": 3}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Total Customers", "col": 3}},
        {"id": get_random_id(), "type": "number_card", "data": {"number_card_name": "Webshop Abandoned Carts", "col": 3}},
        {"id": get_random_id(), "type": "spacer", "data": {"col": 12}},
        
        {"id": get_random_id(), "type": "header", "data": {"text": "<span class=\"h4\"><b>Quick Access</b></span>", "col": 12}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Item", "col": 3}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Sales Order", "col": 3}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Customer", "col": 3}},
        {"id": get_random_id(), "type": "shortcut", "data": {"shortcut_name": "Webshop Theme Settings", "col": 3}},
        {"id": get_random_id(), "type": "spacer", "data": {"col": 12}},
        
        {"id": get_random_id(), "type": "header", "data": {"text": "<span class=\"h4\"><b>Masters & Settings</b></span>", "col": 12}},
        {"id": get_random_id(), "type": "card", "data": {"card_name": "Sales & Customers", "col": 4}},
        {"id": get_random_id(), "type": "card", "data": {"card_name": "Webshop Settings", "col": 4}},
        {"id": get_random_id(), "type": "card", "data": {"card_name": "Content & Marketing", "col": 4}},
    ]
    workspace.content = json.dumps(blocks)

    # Shortcuts
    workspace.append("shortcuts", {"label": "Items", "type": "DocType", "link_to": "Item"})
    workspace.append("shortcuts", {"label": "Orders", "type": "DocType", "link_to": "Sales Order"})
    workspace.append("shortcuts", {"label": "Customers", "type": "DocType", "link_to": "Customer"})
    workspace.append("shortcuts", {"label": "Theme Settings", "type": "DocType", "link_to": "Webshop Theme Settings"})

    # Sales & Customers Card
    workspace.append("links", {"label": "Sales Order", "link_to": "Sales Order", "link_type": "DocType", "card": "Sales & Customers"})
    workspace.append("links", {"label": "Customer", "link_to": "Customer", "link_type": "DocType", "card": "Sales & Customers"})
    workspace.append("links", {"label": "Item", "link_to": "Item", "link_type": "DocType", "card": "Sales & Customers"})
    workspace.append("links", {"label": "Item Group", "link_to": "Item Group", "link_type": "DocType", "card": "Sales & Customers"})
    workspace.append("links", {"label": "Address", "link_to": "Address", "link_type": "DocType", "card": "Sales & Customers"})
    workspace.append("links", {"label": "Contact", "link_to": "Contact", "link_type": "DocType", "card": "Sales & Customers"})
    
    # Webshop Settings Card
    workspace.append("links", {"label": "Theme Settings", "link_to": "Webshop Theme Settings", "link_type": "DocType", "card": "Webshop Settings"})
    workspace.append("links", {"label": "Product Settings", "link_to": "Webshop Product Settings", "link_type": "DocType", "card": "Webshop Settings"})
    workspace.append("links", {"label": "Payment Settings", "link_to": "Webshop Payment Settings", "link_type": "DocType", "card": "Webshop Settings"})
    workspace.append("links", {"label": "API Settings", "link_to": "Webshop API Settings", "link_type": "DocType", "card": "Webshop Settings"})
    workspace.append("links", {"label": "SEO Settings", "link_to": "Webshop SEO Settings", "link_type": "DocType", "card": "Webshop Settings"})

    # Content & Marketing Card
    workspace.append("links", {"label": "Content Settings", "link_to": "Webshop Content Settings", "link_type": "DocType", "card": "Content & Marketing"})
    workspace.append("links", {"label": "Landing Sections", "link_to": "Webshop Landing Section", "link_type": "DocType", "card": "Content & Marketing"})
    workspace.append("links", {"label": "Announcement Bar", "link_to": "Webshop Announcement Bar", "link_type": "DocType", "card": "Content & Marketing"})
    workspace.append("links", {"label": "FAQ", "link_to": "Webshop FAQ", "link_type": "DocType", "card": "Content & Marketing"})
    workspace.append("links", {"label": "Popups", "link_to": "Webshop Popup", "link_type": "DocType", "card": "Content & Marketing"})
    workspace.append("links", {"label": "Abandoned Carts", "link_to": "Webshop Abandoned Cart", "link_type": "DocType", "card": "Content & Marketing"})

    workspace.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Workspace 'Sync Webshop' updated with public assets and standard doctypes.")

if __name__ == "__main__":
    run_all()
