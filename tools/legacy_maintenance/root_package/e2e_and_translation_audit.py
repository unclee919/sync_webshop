import frappe
import json

def audit_and_test():
    print("=== 1. E2E Customer Auth & Checkout Simulation ===")
    email = "e2e.tester@sync-webshop.com"
    phone = "+966551234567"
    full_name = "E2E Test Customer"

    # Simulate Customer Login / Creation
    customer = frappe.db.get_value("Customer", {"email_id": email}, ["name"])
    if not customer:
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": full_name,
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "All Territories",
            "email_id": email,
            "mobile_no": phone
        })
        cust.insert(ignore_permissions=True)
        customer_name = cust.name
        print(f"[Pass] Created test customer: {customer_name}")
    else:
        customer_name = customer
        print(f"[Pass] Existing test customer found: {customer_name}")

    # Get default company
    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, ["name"])

    # Simulate Sales Order creation (Checkout Flow)
    item_code = frappe.db.get_value("Item", {"published_in_website": 1}, ["item_code"])
    if item_code and company:
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "company": company,
            "customer": customer_name,
            "delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 3),
            "items": [
                {
                    "item_code": item_code,
                    "qty": 1,
                    "rate": 100.0
                }
            ]
        })
        so.insert(ignore_permissions=True)
        so.submit()
        print(f"[Pass] E2E Checkout Simulation: Created and submitted Sales Order {so.name} for company {company}")
    else:
        print("[Warning] No published items or company found for Sales Order simulation.")

    print("\n=== 2. Translation Records Audit ===")
    translations = frappe.get_all("Translation", filters={"language": "ar"}, fields=["source_text", "translated_text"])
    print(f"[Pass] Total Arabic translations loaded in core DocType: {len(translations)}")

    print("\n=== 3. Workspace Re-Design for Maximum Friendliness ===")
    workspace_name = "Sync Webshop"
    if frappe.db.exists("Workspace", workspace_name):
        frappe.delete_doc("Workspace", workspace_name, force=True)

    ws = frappe.new_doc("Workspace")
    ws.name = workspace_name
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

        # Number Cards
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Webshop Total Orders", "col": 3}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Webshop Total Products", "col": 3}},
        {"id": "nc3", "type": "number_card", "data": {"number_card_name": "Webshop Total Customers", "col": 3}},
        {"id": "nc4", "type": "number_card", "data": {"number_card_name": "Total Revenue (SAR)", "col": 3}},

        {"id": "sp2", "type": "spacer", "data": {"col": 12}},

        # Chart
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

    cards = [
        {"number_card_name": "Webshop Total Orders", "label": "Total Orders"},
        {"number_card_name": "Webshop Total Products", "label": "Catalog Products"},
        {"number_card_name": "Webshop Total Customers", "label": "Active Customers"},
        {"number_card_name": "Total Revenue (SAR)", "label": "Total Revenue"}
    ]
    for c in cards:
        ws.append("number_cards", c)

    charts = [
        {"chart_name": "Webshop Sales Trend", "label": "Sales Trend"}
    ]
    for ch in charts:
        ws.append("charts", ch)

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
    frappe.clear_cache()
    print("[Pass] Elite Friendly Workspace re-designed successfully.")

if __name__ == "__main__":
    audit_and_test()
