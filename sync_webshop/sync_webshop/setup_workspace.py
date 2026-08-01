import frappe
from frappe.utils import nowdate, add_months

def create_number_card(label, doctype, function="Count", aggregate_function_based_on=None, filters=None):
    name = f"Webshop {label}"
    if not frappe.db.exists("Number Card", name):
        doc = frappe.get_doc({
            "doctype": "Number Card",
            "label": name,
            "document_type": doctype,
            "function": function,
            "aggregate_function_based_on": aggregate_function_based_on,
            "filters_json": frappe.as_json(filters) if filters else "[]"
        })
        doc.insert(ignore_permissions=True)
    return name

def create_dashboard_chart():
    name = "Webshop Sales Trend"
    if not frappe.db.exists("Dashboard Chart", name):
        doc = frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": name,
            "chart_type": "Count",
            "document_type": "Sales Order",
            "based_on": "transaction_date",
            "timespan": "Last Year",
            "time_interval": "Monthly",
            "type": "Line",
            "is_public": 1,
            "filters_json": "[]"
        })
        doc.insert(ignore_permissions=True)
    return name

def create_workspace():
    workspace_name = "Sync Webshop"
    if frappe.db.exists("Workspace", workspace_name):
        frappe.delete_doc("Workspace", workspace_name)
    
    workspace = frappe.get_doc({
        "doctype": "Workspace",
        "label": workspace_name,
        "title": "Sync Webshop",
        "icon": "shop",
        "module": "Sync Webshop",
        "public": 1,
        "is_standard": 0,
        "content": frappe.as_json([
            {"type": "header", "data": {"text": "Sync Webshop Management", "level": 2}},
            {"type": "chart", "data": {"chart_name": "Webshop Sales Trend"}},
            {"type": "spacer", "data": {}},
            {"type": "header", "data": {"text": "Key Performance Indicators", "level": 4}},
            {"type": "number_card", "data": {"number_card_name": "Webshop Total Products"}},
            {"type": "number_card", "data": {"number_card_name": "Webshop Total Orders"}},
            {"type": "number_card", "data": {"number_card_name": "Webshop Total Customers"}},
            {"type": "number_card", "data": {"number_card_name": "Webshop Abandoned Carts"}},
            {"type": "spacer", "data": {}},
            {"type": "header", "data": {"text": "Quick Access", "level": 4}},
            {"type": "card", "data": {"card_name": "Core Settings"}},
            {"type": "card", "data": {"card_name": "Store Content"}},
            {"type": "card", "data": {"card_name": "Advanced"}},
        ])
    })

    # Add Shortcuts
    workspace.append("shortcuts", {"label": "Content Settings", "type": "DocType", "link_to": "Webshop Content Settings"})
    workspace.append("shortcuts", {"label": "Theme Settings", "type": "DocType", "link_to": "Webshop Theme Settings"})
    workspace.append("shortcuts", {"label": "Product Settings", "type": "DocType", "link_to": "Webshop Product Settings"})
    workspace.append("shortcuts", {"label": "API Settings", "type": "DocType", "link_to": "Webshop API Settings"})

    # Add Links to Cards
    # Card: Core Settings
    workspace.append("links", {"label": "Webshop Theme Settings", "type": "Link", "link_to": "Webshop Theme Settings", "link_type": "DocType", "card": "Core Settings"})
    workspace.append("links", {"label": "Webshop Content Settings", "type": "Link", "link_to": "Webshop Content Settings", "link_type": "DocType", "card": "Core Settings"})
    workspace.append("links", {"label": "Webshop Product Settings", "type": "Link", "link_to": "Webshop Product Settings", "link_type": "DocType", "card": "Core Settings"})
    workspace.append("links", {"label": "Webshop Payment Settings", "type": "Link", "link_to": "Webshop Payment Settings", "link_type": "DocType", "card": "Core Settings"})
    
    # Card: Store Content
    workspace.append("links", {"label": "Webshop Landing Section", "type": "Link", "link_to": "Webshop Landing Section", "link_type": "DocType", "card": "Store Content"})
    workspace.append("links", {"label": "Webshop FAQ", "type": "Link", "link_to": "Webshop FAQ", "link_type": "DocType", "card": "Store Content"})
    workspace.append("links", {"label": "Webshop Announcement Bar", "type": "Link", "link_to": "Webshop Announcement Bar", "link_type": "DocType", "card": "Store Content"})
    workspace.append("links", {"label": "Webshop Popup", "type": "Link", "link_to": "Webshop Popup", "link_type": "DocType", "card": "Store Content"})

    # Card: Advanced
    workspace.append("links", {"label": "Webshop SEO Settings", "type": "Link", "link_to": "Webshop SEO Settings", "link_type": "DocType", "card": "Advanced"})
    workspace.append("links", {"label": "Webshop Shipping Rule", "type": "Link", "link_to": "Webshop Shipping Rule", "link_type": "DocType", "card": "Advanced"})
    workspace.append("links", {"label": "Webshop Abandoned Cart", "type": "Link", "link_to": "Webshop Abandoned Cart", "link_type": "DocType", "card": "Advanced"})
    workspace.append("links", {"label": "Webshop Wishlist", "type": "Link", "link_to": "Webshop Wishlist", "link_type": "DocType", "card": "Advanced"})

    workspace.insert(ignore_permissions=True)
    frappe.db.commit()

def run_all():
    create_number_card("Total Products", "Item")
    create_number_card("Total Orders", "Sales Order")
    create_number_card("Total Customers", "Customer")
    create_number_card("Abandoned Carts", "Webshop Abandoned Cart")
    create_dashboard_chart()
    create_workspace()
    print("Workspace setup completed successfully.")

if __name__ == "__main__":
    run_all()
