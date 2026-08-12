import frappe
import json

def elite_rebuild():
    if frappe.db.exists("Workspace", "Sync Webshop"):
        frappe.delete_doc("Workspace", "Sync Webshop", force=True)
        
    ws = frappe.new_doc("Workspace")
    ws.name = "Sync Webshop"
    ws.label = "Sync Webshop"
    ws.title = "Sync Webshop"
    ws.icon = "shop"
    ws.module = "Sync Webshop"
    ws.is_standard = 0
    ws.public = 1
    
    content_blocks = [
        {"id": "h1", "type": "header", "data": {"text": "Sync Webshop Elite Command Center", "level": 2, "col": 12}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        {"id": "h2", "type": "header", "data": {"text": "Quick Action Shortcuts", "level": 4, "col": 12}},
        {"id": "sc1", "type": "shortcut", "data": {"shortcut_name": "Products", "col": 3}},
        {"id": "sc2", "type": "shortcut", "data": {"shortcut_name": "Orders", "col": 3}},
        {"id": "sc3", "type": "shortcut", "data": {"shortcut_name": "Customers", "col": 3}},
        {"id": "sc4", "type": "shortcut", "data": {"shortcut_name": "Theme Editor", "col": 3}},
        {"id": "sp2", "type": "spacer", "data": {"col": 12}},
        {"id": "c1", "type": "card", "data": {"card_name": "Store Operations", "col": 6}},
        {"id": "c2", "type": "card", "data": {"card_name": "Storefront & AI", "col": 6}},
    ]
    
    ws.content = json.dumps(content_blocks)
    
    shortcuts = [
        {"label": "Products", "type": "DocType", "link_to": "Item", "icon": "list"},
        {"label": "Orders", "type": "DocType", "link_to": "Sales Order", "icon": "file-text"},
        {"label": "Customers", "type": "DocType", "link_to": "Customer", "icon": "users"},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "layout"},
    ]
    
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
    
    for s in shortcuts:
        ws.append("shortcuts", s)
    for l in links:
        ws.append("links", l)
        
    ws.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache()
    print("Elite Workspace rebuilt successfully.")

if __name__ == "__main__":
    elite_rebuild()
