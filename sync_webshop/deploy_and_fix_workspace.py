import frappe
import json

def deploy_fix():
    print("=== 1. Ensuring Number Cards Exist ===")
    cards = [
        {
            "name": "Webshop Total Orders",
            "label": "Total Orders",
            "document_type": "Sales Order",
            "function": "Count",
            "is_standard": 0,
            "module": "Sync Webshop",
            "time_range": "All Time"
        },
        {
            "name": "Webshop Total Products",
            "label": "Catalog Products",
            "document_type": "Item",
            "function": "Count",
            "is_standard": 0,
            "module": "Sync Webshop",
            "time_range": "All Time"
        },
        {
            "name": "Webshop Total Customers",
            "label": "Active Customers",
            "document_type": "Customer",
            "function": "Count",
            "is_standard": 0,
            "module": "Sync Webshop",
            "time_range": "All Time"
        },
        {
            "name": "Total Revenue (SAR)",
            "label": "Total Revenue",
            "document_type": "Sales Order",
            "aggregate_function_based_on": "grand_total",
            "function": "Sum",
            "is_standard": 0,
            "module": "Sync Webshop",
            "time_range": "All Time"
        }
    ]
    
    for c in cards:
        if frappe.db.exists("Number Card", c["name"]):
            doc = frappe.get_doc("Number Card", c["name"])
            doc.update(c)
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.new_doc("Number Card")
            doc.update(c)
            doc.insert(ignore_permissions=True)
        print(f"[OK] Number Card: {c['name']}")

    print("=== 2. Ensuring Dashboard Chart Exists ===")
    chart_name = "Webshop Sales Trend"
    if frappe.db.exists("Dashboard Chart", chart_name):
        chart = frappe.get_doc("Dashboard Chart", chart_name)
    else:
        chart = frappe.new_doc("Dashboard Chart")
        chart.chart_name = chart_name
        chart.chart_type = "Group By"
        chart.document_type = "Sales Order"
        chart.group_by_based_on = "transaction_date"
        chart.group_by_type = "Month"
        chart.aggregate_function_based_on = "grand_total"
        chart.function = "Sum"
        chart.is_standard = 0
        chart.module = "Sync Webshop"
        chart.timespan = "Last Year"
        chart.insert(ignore_permissions=True)
    print(f"[OK] Dashboard Chart: {chart_name}")

    print("=== 3. Updating Workspace 'Sync Webshop' ===")
    ws_name = "Sync Webshop"
    if frappe.db.exists("Workspace", ws_name):
        ws = frappe.get_doc("Workspace", ws_name)
    else:
        ws = frappe.new_doc("Workspace")
        ws.name = ws_name

    ws.label = "Sync Webshop"
    ws.title = "Sync Webshop Command Center"
    ws.icon = "shop"
    ws.module = "Sync Webshop"
    ws.is_standard = 0
    ws.public = 1
    ws.sequence_id = 1.0

    content_blocks = [
        {"id": "h1", "type": "header", "data": {"text": "🚀 Sync Webshop Elite Command Center", "level": 2, "col": 12}},
        {"id": "p1", "type": "text", "data": {"text": "Welcome to your professional e-commerce operations hub. Monitor live revenue, manage catalog inventory, and configure AI & payment settings instantly.", "col": 12}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Webshop Total Orders", "col": 3}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Webshop Total Products", "col": 3}},
        {"id": "nc3", "type": "number_card", "data": {"number_card_name": "Webshop Total Customers", "col": 3}},
        {"id": "nc4", "type": "number_card", "data": {"number_card_name": "Total Revenue (SAR)", "col": 3}},
        
        {"id": "sp2", "type": "spacer", "data": {"col": 12}},
        {"id": "ch1", "type": "chart", "data": {"chart_name": "Webshop Sales Trend", "col": 12}},
        {"id": "sp3", "type": "spacer", "data": {"col": 12}},
        
        {"id": "h2", "type": "header", "data": {"text": "⚡ Quick Navigation & Management", "level": 4, "col": 12}},
        {"id": "sc1", "type": "shortcut", "data": {"shortcut_name": "Products", "col": 3}},
        {"id": "sc2", "type": "shortcut", "data": {"shortcut_name": "Orders", "col": 3}},
        {"id": "sc3", "type": "shortcut", "data": {"shortcut_name": "Customers", "col": 3}},
        {"id": "sc4", "type": "shortcut", "data": {"shortcut_name": "Theme Editor", "col": 3}},
        
        {"id": "sp4", "type": "spacer", "data": {"col": 12}},
        {"id": "c1", "type": "card", "data": {"card_name": "📦 Store Operations", "col": 6}},
        {"id": "c2", "type": "card", "data": {"card_name": "✨ Storefront, AI & Growth", "col": 6}},
    ]
    
    ws.content = json.dumps(content_blocks)
    
    ws.number_cards = []
    for c in cards:
        ws.append("number_cards", {"number_card_name": c["name"], "label": c["label"]})
        
    ws.charts = []
    ws.append("charts", {"chart_name": chart_name, "label": "Sales Trend"})

    ws.shortcuts = []
    shortcuts = [
        {"label": "Products", "type": "DocType", "link_to": "Item", "icon": "box"},
        {"label": "Orders", "type": "DocType", "link_to": "Sales Order", "icon": "shopping-cart"},
        {"label": "Customers", "type": "DocType", "link_to": "Customer", "icon": "user-check"},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "sliders"},
    ]
    for s in shortcuts:
        ws.append("shortcuts", s)
        
    ws.links = []
    links = [
        {"label": "📦 Store Operations", "type": "Card Break"},
        {"label": "Sales Orders", "link_type": "DocType", "link_to": "Sales Order"},
        {"label": "Items", "link_type": "DocType", "link_to": "Item"},
        {"label": "Item Groups", "link_type": "DocType", "link_to": "Item Group"},
        {"label": "Coupon Codes", "link_type": "DocType", "link_to": "Coupon Code"},
        {"label": "Product Reviews", "link_type": "DocType", "link_to": "Webshop Review"},
        
        {"label": "✨ Storefront, AI & Growth", "type": "Card Break"},
        {"label": "Theme Settings", "link_type": "DocType", "link_to": "Webshop Theme Settings"},
        {"label": "Content Settings", "link_type": "DocType", "link_to": "Webshop Content Settings"},
        {"label": "SEO Settings", "link_type": "DocType", "link_to": "Webshop SEO Settings"},
        {"label": "AI Chat Settings", "link_type": "DocType", "link_to": "Webshop AI Chat Settings"},
        {"label": "Paymob Settings", "link_type": "DocType", "link_to": "Webshop Paymob Settings"},
    ]
    for l in links:
        ws.append("links", l)
        
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    print("[OK] Workspace 'Sync Webshop' updated successfully.")

if __name__ == "__main__":
    deploy_fix()
