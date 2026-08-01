import frappe
import json

def run():
    # 1. Ensure Number Cards exist
    cards_data = [
        {
            "name": "Webshop Total Products",
            "label": "Webshop Total Products",
            "document_type": "Item",
            "function": "Count",
            "module": "Sync Webshop"
        },
        {
            "name": "Webshop Total Orders",
            "label": "Webshop Total Orders",
            "document_type": "Sales Order",
            "function": "Count",
            "module": "Sync Webshop"
        },
        {
            "name": "Webshop Total Customers",
            "label": "Webshop Total Customers",
            "document_type": "Customer",
            "function": "Count",
            "module": "Sync Webshop"
        },
        {
            "name": "Webshop Abandoned Carts",
            "label": "Webshop Abandoned Carts",
            "document_type": "Webshop Abandoned Cart",
            "function": "Count",
            "module": "Sync Webshop"
        }
    ]

    for data in cards_data:
        if frappe.db.exists("Number Card", data["name"]):
            frappe.delete_doc("Number Card", data["name"], ignore_permissions=True)
        doc = frappe.get_doc({"doctype": "Number Card", **data})
        doc.insert(ignore_permissions=True)

    # 2. Ensure Dashboard Chart exists
    chart_name = "Webshop Sales Trend"
    chart_data = {
        "doctype": "Dashboard Chart",
        "chart_name": chart_name,
        "chart_type": "Sum",
        "document_type": "Sales Order",
        "based_on": "transaction_date",
        "value_based_on": "grand_total",
        "timeseries": 1,
        "time_interval": "Daily",
        "number_of_periods": 30,
        "filters_json": json.dumps([]),
        "module": "Sync Webshop",
        "type": "Line"
    }
    if frappe.db.exists("Dashboard Chart", chart_name):
        frappe.delete_doc("Dashboard Chart", chart_name, ignore_permissions=True)
    frappe.get_doc(chart_data).insert(ignore_permissions=True)

    # 3. Setup Workspace
    ws_name = "Sync Webshop"
    
    content = [
        {"data": {"level": 2, "text": "Sync Webshop Management"}, "type": "header"},
        {"data": {"chart_name": chart_name}, "type": "chart"},
        {"data": {}, "type": "spacer"},
        {"data": {"level": 4, "text": "Key Performance Indicators"}, "type": "header"},
        {"data": {"number_card_name": "Webshop Total Products"}, "type": "number_card"},
        {"data": {"number_card_name": "Webshop Total Orders"}, "type": "number_card"},
        {"data": {"number_card_name": "Webshop Total Customers"}, "type": "number_card"},
        {"data": {"number_card_name": "Webshop Abandoned Carts"}, "type": "number_card"},
        {"data": {}, "type": "spacer"},
        {"data": {"level": 4, "text": "Quick Access"}, "type": "header"},
        {"data": {"card_name": "Store Configuration"}, "type": "card"},
        {"data": {"card_name": "Content & SEO"}, "type": "card"},
        {"data": {"card_name": "Sales & Customers"}, "type": "card"}
    ]

    links = [
        # Store Configuration
        {"label": "Webshop API Settings", "link_to": "Webshop API Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Theme Settings", "link_to": "Webshop Theme Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Product Settings", "link_to": "Webshop Product Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Payment Settings", "link_to": "Webshop Payment Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Shipping Rule", "link_to": "Webshop Shipping Rule", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        
        # Content & SEO
        {"label": "Webshop Content Settings", "link_to": "Webshop Content Settings", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Landing Section", "link_to": "Webshop Landing Section", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Announcement Bar", "link_to": "Webshop Announcement Bar", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Popup", "link_to": "Webshop Popup", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop FAQ", "link_to": "Webshop FAQ", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop SEO Settings", "link_to": "Webshop SEO Settings", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        
        # Sales & Customers
        {"label": "Webshop Abandoned Cart", "link_to": "Webshop Abandoned Cart", "link_type": "DocType", "type": "Link", "card": "Sales & Customers"},
        {"label": "Webshop Wishlist", "link_to": "Webshop Wishlist", "link_type": "DocType", "type": "Link", "card": "Sales & Customers"},
        {"label": "Webshop Testimonial", "link_to": "Webshop Testimonial", "link_type": "DocType", "type": "Link", "card": "Sales & Customers"},
        {"label": "Webshop Trust Badge", "link_to": "Webshop Trust Badge", "link_type": "DocType", "type": "Link", "card": "Sales & Customers"}
    ]

    shortcuts = [
        {"label": "Content Settings", "link_to": "Webshop Content Settings", "type": "DocType"},
        {"label": "Theme Settings", "link_to": "Webshop Theme Settings", "type": "DocType"},
        {"label": "Product Settings", "link_to": "Webshop Product Settings", "type": "DocType"},
        {"label": "API Settings", "link_to": "Webshop API Settings", "type": "DocType"}
    ]

    if not frappe.db.exists("Workspace", ws_name):
        ws_doc = frappe.get_doc({
            "doctype": "Workspace",
            "label": ws_name,
            "module": "Sync Webshop",
            "public": 1,
            "icon": "shop"
        })
        ws_doc.insert(ignore_permissions=True)
    else:
        ws_doc = frappe.get_doc("Workspace", ws_name)

    ws_doc.content = json.dumps(content)
    ws_doc.set("links", links)
    ws_doc.set("shortcuts", shortcuts)
    ws_doc.set("number_cards", [{"number_card_name": c["name"]} for c in cards_data])
    ws_doc.set("charts", [{"chart_name": chart_name}])
    ws_doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Workspace setup complete")
