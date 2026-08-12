import frappe
import json

def hard_reset():
    print("=== 1. Wiping old Workspaces, Number Cards, and Charts ===")
    frappe.db.sql("DELETE FROM `tabWorkspace` WHERE name LIKE '%Webshop%' OR label LIKE '%Webshop%'")
    frappe.db.sql("DELETE FROM `tabNumber Card` WHERE name LIKE '%Webshop%' OR label LIKE '%Orders%' OR label LIKE '%Products%' OR label LIKE '%Customers%' OR label LIKE '%Revenue%' OR name LIKE '%Elite%'")
    frappe.db.sql("DELETE FROM `tabDashboard Chart` WHERE name LIKE '%Webshop%' OR name LIKE '%Elite%'")
    frappe.db.commit()

    print("=== 2. Creating Fresh Number Cards ===")
    for name, label, dt, func, agg in [
        ("Total Orders", "Total Orders", "Sales Order", "Count", None),
        ("Catalog Products", "Catalog Products", "Item", "Count", None),
        ("Active Customers", "Active Customers", "Customer", "Count", None),
        ("Total Revenue", "Total Revenue", "Sales Order", "Sum", "grand_total")
    ]:
        nc = frappe.new_doc("Number Card")
        nc.name = name
        nc.label = label
        nc.document_type = dt
        nc.function = func
        if agg:
            nc.aggregate_function_based_on = agg
        nc.is_standard = 0
        nc.module = "Sync Webshop"
        nc.time_range = "All Time"
        nc.insert(ignore_permissions=True)

    print("=== 3. Creating Fresh Dashboard Chart ===")
    ch1 = frappe.new_doc("Dashboard Chart")
    ch1.name = "Sales Trend"
    ch1.chart_name = "Sales Trend"
    ch1.chart_type = "Sum"
    ch1.document_type = "Sales Order"
    ch1.based_on = "transaction_date"
    ch1.value_based_on = "grand_total"
    ch1.is_standard = 0
    ch1.module = "Sync Webshop"
    ch1.timespan = "Last Year"
    ch1.filters_json = "{}"
    ch1.insert(ignore_permissions=True)

    print("=== 4. Creating Clean Workspace 'Sync Webshop' ===")
    ws = frappe.new_doc("Workspace")
    ws.name = "Sync Webshop"
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
        
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Total Orders", "col": 3}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Catalog Products", "col": 3}},
        {"id": "nc3", "type": "number_card", "data": {"number_card_name": "Active Customers", "col": 3}},
        {"id": "nc4", "type": "number_card", "data": {"number_card_name": "Total Revenue", "col": 3}},
        
        {"id": "sp2", "type": "spacer", "data": {"col": 12}},
        {"id": "ch1", "type": "chart", "data": {"chart_name": "Sales Trend", "col": 12}},
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
    
    ws.append("number_cards", {"number_card_name": "Total Orders", "label": "Total Orders"})
    ws.append("number_cards", {"number_card_name": "Catalog Products", "label": "Catalog Products"})
    ws.append("number_cards", {"number_card_name": "Active Customers", "label": "Active Customers"})
    ws.append("number_cards", {"number_card_name": "Total Revenue", "label": "Total Revenue"})
    
    ws.append("charts", {"chart_name": "Sales Trend", "label": "Sales Trend"})

    shortcuts = [
        {"label": "Products", "type": "DocType", "link_to": "Item", "icon": "box"},
        {"label": "Orders", "type": "DocType", "link_to": "Sales Order", "icon": "shopping-cart"},
        {"label": "Customers", "type": "DocType", "link_to": "Customer", "icon": "user-check"},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "sliders"},
    ]
    for s in shortcuts:
        ws.append("shortcuts", s)
        
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
        
    ws.insert(ignore_permissions=True)
    frappe.db.commit()
    print("[Pass] Hard-reset workspace created successfully.")

if __name__ == "__main__":
    hard_reset()
