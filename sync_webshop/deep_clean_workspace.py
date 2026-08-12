import frappe
import json

def deep_clean():
    # 1. Delete Workspace and any custom/user overrides
    frappe.db.delete("Workspace", {"name": ["like", "%Sync Webshop%"]})
    frappe.db.delete("Custom DocPerm", {"parent": ["like", "%Workspace%"]})
    
    # 2. Also delete any file-based workspace that might conflict
    import os, shutil
    app_path = frappe.get_app_path("sync_webshop")
    ws_dir = os.path.join(app_path, "workspace")
    if os.path.exists(ws_dir):
        shutil.rmtree(ws_dir)
        print("Removed file-based workspace directory to prevent conflicts.")

    # 3. Create a fresh, database-managed Workspace
    ws = frappe.new_doc("Workspace")
    ws.name = "Sync Webshop"
    ws.label = "Sync Webshop"
    ws.title = "Sync Webshop"
    ws.icon = "shop"
    ws.module = "Sync Webshop"
    ws.is_standard = 0
    ws.public = 1
    ws.sequence_id = 1.0

    # Simple, highly reliable content blocks that match child table items
    content_blocks = [
        {"id": "h1", "type": "header", "data": {"text": "Sync Webshop Elite Command Center", "level": 2, "col": 12}},
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
        
        {"id": "h2", "type": "header", "data": {"text": "Quick Action Shortcuts", "level": 4, "col": 12}},
        {"id": "sc1", "type": "shortcut", "data": {"shortcut_name": "Products", "col": 3}},
        {"id": "sc2", "type": "shortcut", "data": {"shortcut_name": "Orders", "col": 3}},
        {"id": "sc3", "type": "shortcut", "data": {"shortcut_name": "Customers", "col": 3}},
        {"id": "sc4", "type": "shortcut", "data": {"shortcut_name": "Theme Editor", "col": 3}},
        
        {"id": "sp4", "type": "spacer", "data": {"col": 12}},
        
        {"id": "c1", "type": "card", "data": {"card_name": "Store Operations", "col": 6}},
        {"id": "c2", "type": "card", "data": {"card_name": "Storefront & AI", "col": 6}},
    ]
    
    ws.content = json.dumps(content_blocks)
    
    # Append Number Cards
    cards = [
        {"number_card_name": "Webshop Total Orders", "label": "Total Orders"},
        {"number_card_name": "Webshop Total Products", "label": "Catalog Products"},
        {"number_card_name": "Webshop Total Customers", "label": "Active Customers"},
        {"number_card_name": "Total Revenue (SAR)", "label": "Total Revenue"}
    ]
    for c in cards:
        ws.append("number_cards", c)
        
    # Append Charts
    charts = [
        {"chart_name": "Webshop Sales Trend", "label": "Sales Trend"}
    ]
    for ch in charts:
        ws.append("charts", ch)

    # Append Shortcuts
    shortcuts = [
        {"label": "Products", "type": "DocType", "link_to": "Item", "icon": "list"},
        {"label": "Orders", "type": "DocType", "link_to": "Sales Order", "icon": "file-text"},
        {"label": "Customers", "type": "DocType", "link_to": "Customer", "icon": "users"},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "layout"},
    ]
    for s in shortcuts:
        ws.append("shortcuts", s)
        
    # Append Links
    links = [
        {"label": "Store Operations", "type": "Card Break"},
        {"label": "Sales Orders", "link_type": "DocType", "link_to": "Sales Order"},
        {"label": "Items", "link_type": "DocType", "link_to": "Item"},
        {"label": "Item Groups", "link_type": "DocType", "link_to": "Item Group"},
        {"label": "Coupon Codes", "link_type": "DocType", "link_to": "Coupon Code"},
        {"label": "Product Reviews", "link_type": "DocType", "link_to": "Webshop Review"},
        
        {"label": "Storefront & AI", "type": "Card Break"},
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
    print("Deep clean workspace rebuild completed successfully.")

if __name__ == "__main__":
    deep_clean()
