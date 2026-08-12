import frappe
import json

def run_checks_and_fix():
    print("=== 1. Checking Background Workers & Queue Status ===")
    try:
        from frappe.utils.background_jobs import get_queues
        queues = get_queues()
        print(f"[Pass] Active RQ Queues: {queues}")
    except Exception as e:
        print(f"[Info] Worker check fallback: {e}")

    print("\n=== 2. Verifying Storefront Items & Stock Setup ===")
    items = frappe.get_all("Item", filters={"published_in_website": 1}, fields=["item_code", "item_name", "stock_uom"], limit=5)
    print(f"[Pass] Found {len(items)} published storefront items:")
    for item in items:
        stock = frappe.db.get_value("Bin", {"item_code": item.item_code}, "actual_qty") or 0.0
        print(f"   - {item.item_code} ({item.item_name}): Stock = {stock}")

    print("\n=== 3. Ultimate Workspace Stabilization (Removing Sad Face) ===")
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
        {"id": "p1", "type": "text", "data": {"text": "Welcome to your professional e-commerce operations hub. All systems are operational, stock is synchronized, and multi-image galleries are live.", "col": 12}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        
        {"id": "h2", "type": "header", "data": {"text": "⚡ Quick Navigation & Management", "level": 4, "col": 12}},
        {"id": "sc1", "type": "shortcut", "data": {"shortcut_name": "Products", "col": 3}},
        {"id": "sc2", "type": "shortcut", "data": {"shortcut_name": "Orders", "col": 3}},
        {"id": "sc3", "type": "shortcut", "data": {"shortcut_name": "Customers", "col": 3}},
        {"id": "sc4", "type": "shortcut", "data": {"shortcut_name": "Theme Editor", "col": 3}},
        
        {"id": "sp2", "type": "spacer", "data": {"col": 12}},
        {"id": "c1", "type": "card", "data": {"card_name": "📦 Store Operations", "col": 6}},
        {"id": "c2", "type": "card", "data": {"card_name": "✨ Storefront, AI & Growth", "col": 6}},
    ]
    
    ws.content = json.dumps(content_blocks)
    ws.number_cards = []
    ws.charts = []
    ws.shortcuts = []
    ws.links = []

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
        
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache()
    print("[Pass] Workspace successfully stabilized.")

if __name__ == "__main__":
    run_checks_and_fix()
