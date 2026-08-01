import frappe
import json

def run():
    frappe.set_user("Administrator")
    
    # 1. Ensure Number Cards exist
    cards_data = [
        {
            "name": "Webshop Total Products",
            "label": "Total Products",
            "document_type": "Item",
            "function": "Count",
            "is_standard": 0
        },
        {
            "name": "Webshop Total Orders",
            "label": "Total Orders",
            "document_type": "Sales Order",
            "function": "Count",
            "is_standard": 0
        },
        {
            "name": "Webshop Total Customers",
            "label": "Total Customers",
            "document_type": "Customer",
            "function": "Count",
            "is_standard": 0
        },
        {
            "name": "Webshop Abandoned Carts",
            "label": "Abandoned Carts",
            "document_type": "Webshop Abandoned Cart",
            "function": "Count",
            "is_standard": 0
        }
    ]

    for data in cards_data:
        if frappe.db.exists("Number Card", data["name"]):
            frappe.delete_doc("Number Card", data["name"], ignore_permissions=True)
        doc = frappe.get_doc({"doctype": "Number Card", **data})
        doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    print("Number cards created and committed")

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
        "is_standard": 0,
        "type": "Line"
    }
    if frappe.db.exists("Dashboard Chart", chart_name):
        frappe.delete_doc("Dashboard Chart", chart_name, ignore_permissions=True)
    frappe.get_doc(chart_data).insert(ignore_permissions=True)
    
    frappe.db.commit()
    print("Dashboard chart created and committed")

    # 3. Setup Workspace
    ws_name = "Sync Webshop"
    
    if not frappe.db.exists("Workspace", ws_name):
        ws_doc = frappe.get_doc({
            "doctype": "Workspace",
            "label": ws_name,
            "public": 1,
            "icon": "shop"
        })
        ws_doc.insert(ignore_permissions=True)
    else:
        ws_doc = frappe.get_doc("Workspace", ws_name)

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
        {"data": {"card_name": "Catalog & Inventory"}, "type": "card"},
        {"data": {"card_name": "Sales & Orders"}, "type": "card"},
        {"data": {"card_name": "Store Configuration"}, "type": "card"},
        {"data": {"card_name": "Content & SEO"}, "type": "card"},
        {"data": {"card_name": "Webshop Extras"}, "type": "card"}
    ]

    links = [
        {"label": "Items", "link_to": "Item", "link_type": "DocType", "type": "Link", "card": "Catalog & Inventory"},
        {"label": "Item Groups", "link_to": "Item Group", "link_type": "DocType", "type": "Link", "card": "Catalog & Inventory"},
        {"label": "Price Lists", "link_to": "Price List", "link_type": "DocType", "type": "Link", "card": "Catalog & Inventory"},
        {"label": "Item Prices", "link_to": "Item Price", "link_type": "DocType", "type": "Link", "card": "Catalog & Inventory"},
        {"label": "Sales Orders", "link_to": "Sales Order", "link_type": "DocType", "type": "Link", "card": "Sales & Orders"},
        {"label": "Sales Invoices", "link_to": "Sales Invoice", "link_type": "DocType", "type": "Link", "card": "Sales & Orders"},
        {"label": "Customers", "link_to": "Customer", "link_type": "DocType", "type": "Link", "card": "Sales & Orders"},
        {"label": "Addresses", "link_to": "Address", "link_type": "DocType", "type": "Link", "card": "Sales & Orders"},
        {"label": "Contacts", "link_to": "Contact", "link_type": "DocType", "type": "Link", "card": "Sales & Orders"},
        {"label": "Webshop API Settings", "link_to": "Webshop API Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Theme Settings", "link_to": "Webshop Theme Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Product Settings", "link_to": "Webshop Product Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Payment Settings", "link_to": "Webshop Payment Settings", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Shipping Rule", "link_to": "Webshop Shipping Rule", "link_type": "DocType", "type": "Link", "card": "Store Configuration"},
        {"label": "Webshop Content Settings", "link_to": "Webshop Content Settings", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Landing Section", "link_to": "Webshop Landing Section", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Announcement Bar", "link_to": "Webshop Announcement Bar", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Popup", "link_to": "Webshop Popup", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop FAQ", "link_to": "Webshop FAQ", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop SEO Settings", "link_to": "Webshop SEO Settings", "link_type": "DocType", "type": "Link", "card": "Content & SEO"},
        {"label": "Webshop Abandoned Cart", "link_to": "Webshop Abandoned Cart", "link_type": "DocType", "type": "Link", "card": "Webshop Extras"},
        {"label": "Webshop Wishlist", "link_to": "Webshop Wishlist", "link_type": "DocType", "type": "Link", "card": "Webshop Extras"},
        {"label": "Webshop Testimonial", "link_to": "Webshop Testimonial", "link_type": "DocType", "type": "Link", "card": "Webshop Extras"},
        {"label": "Webshop Trust Badge", "link_to": "Webshop Trust Badge", "link_type": "DocType", "type": "Link", "card": "Webshop Extras"}
    ]

    shortcuts = [
        {"label": "Items", "link_to": "Item", "type": "DocType"},
        {"label": "Sales Orders", "link_to": "Sales Order", "type": "DocType"},
        {"label": "Content Settings", "link_to": "Webshop Content Settings", "type": "DocType"},
        {"label": "API Settings", "link_to": "Webshop API Settings", "type": "DocType"}
    ]

    ws_doc.content = json.dumps(content)
    ws_doc.set("links", links)
    ws_doc.set("shortcuts", shortcuts)
    ws_doc.set("number_cards", [])
    ws_doc.set("charts", [])
    ws_doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    # Manual SQL insert for child tables to bypass link validation
    frappe.db.sql("DELETE FROM `tabWorkspace Number Card` WHERE parent = %s", ws_name)
    frappe.db.sql("DELETE FROM `tabWorkspace Chart` WHERE parent = %s", ws_name)
    
    for i, card in enumerate(cards_data):
        name = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Number Card` (name, parent, parentfield, parenttype, number_card_name, idx, creation, modified)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (name, ws_name, 'number_cards', 'Workspace', card['name'], i + 1))
    
    name = frappe.generate_hash(length=10)
    frappe.db.sql("""
        INSERT INTO `tabWorkspace Chart` (name, parent, parentfield, parenttype, chart_name, idx, creation, modified)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
    """, (name, ws_name, 'charts', 'Workspace', chart_name, 1))

    frappe.db.commit()
    print("Workspace setup complete")
