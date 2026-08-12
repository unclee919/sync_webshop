import frappe
import json

def setup_workspace():
    workspace_name = "Sync Webshop"
    
    # 1. Check if workspace exists
    ws_doc = None
    existing = frappe.get_all("Workspace", filters={"label": workspace_name}, limit=1)
    if existing:
        ws_doc = frappe.get_doc("Workspace", existing[0].name)
    else:
        ws_doc = frappe.new_doc("Workspace")
        ws_doc.label = workspace_name
        ws_doc.title = "Sync Webshop"
        ws_doc.icon = "shopping-cart"
        ws_doc.module = "Sync Webshop"
        ws_doc.is_standard = 0
        ws_doc.public = 1

    # Define content blocks for Frappe v15 Workspace
    # Shortcuts at the top, then cards/sections
    content_blocks = [
        # Shortcuts Header
        {"id": "shortcut_header", "type": "header", "data": {"text": "Quick Actions", "level": 3, "col": 12}},
        # Shortcuts
        {"id": "sc_item", "type": "shortcut", "data": {"shortcut_name": "Manage Catalog", "col": 3}},
        {"id": "sc_order", "type": "shortcut", "data": {"shortcut_name": "View Orders", "col": 3}},
        {"id": "sc_ai", "type": "shortcut", "data": {"shortcut_name": "AI Settings", "col": 3}},
        {"id": "sc_theme", "type": "shortcut", "data": {"shortcut_name": "Theme Editor", "col": 3}},
        
        # Spacer
        {"id": "spacer_1", "type": "spacer", "data": {"col": 12}},
        
        # Storefront Settings Card
        {"id": "card_storefront", "type": "card", "data": {"card_name": "Storefront Settings", "col": 4}},
        # AI & Support Card
        {"id": "card_ai", "type": "card", "data": {"card_name": "AI & Customer Support", "col": 4}},
        # Catalog & Sales Card
        {"id": "card_catalog", "type": "card", "data": {"card_name": "Catalog & Sales", "col": 4}},
        
        # Spacer
        {"id": "spacer_2", "type": "spacer", "data": {"col": 12}},
        
        # Marketing & Growth Card
        {"id": "card_marketing", "type": "card", "data": {"card_name": "Marketing & Growth", "col": 4}},
        # Logistics & Finance Card
        {"id": "card_logistics", "type": "card", "data": {"card_name": "Logistics & Finance", "col": 4}},
    ]

    ws_doc.content = json.dumps(content_blocks)
    
    # Clear and repopulate links & shortcuts child tables
    ws_doc.links = []
    ws_doc.shortcuts = []

    links = [
        # Storefront Settings
        {"label": "Content Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Content Settings", "only_for": ""},
        {"label": "Theme Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Theme Settings", "only_for": ""},
        {"label": "SEO Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop SEO Settings", "only_for": ""},
        {"label": "Dashboard Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Dashboard Settings", "only_for": ""},
        
        # AI & Support
        {"label": "AI Chat Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop AI Chat Settings", "only_for": ""},
        {"label": "Product Reviews", "type": "Link", "link_type": "DocType", "link_to": "Webshop Review", "only_for": ""},
        
        # Catalog & Sales
        {"label": "Products", "type": "Link", "link_type": "DocType", "link_to": "Item", "only_for": ""},
        {"label": "Product Groups", "type": "Link", "link_type": "DocType", "link_to": "Item Group", "only_for": ""},
        {"label": "Sales Orders", "type": "Link", "link_type": "DocType", "link_to": "Sales Order", "only_for": ""},
        
        # Marketing & Growth
        {"label": "Coupon Codes", "type": "Link", "link_type": "DocType", "link_to": "Coupon Code", "only_for": ""},
        {"label": "Abandoned Carts", "type": "Link", "link_type": "DocType", "link_to": "Webshop Abandoned Cart", "only_for": ""},
        {"label": "Product Display Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Product Settings", "only_for": ""},
        
        # Logistics & Finance
        {"label": "Territories", "type": "Link", "link_type": "DocType", "link_to": "Territory", "only_for": ""},
        {"label": "Paymob Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Paymob Settings", "only_for": ""},
        {"label": "Paymob Transactions", "type": "Link", "link_type": "DocType", "link_to": "Webshop Paymob Transaction", "only_for": ""},
    ]

    shortcuts = [
        {"label": "Manage Catalog", "type": "DocType", "link_to": "Item", "icon": "list", "doc_view": ""},
        {"label": "View Orders", "type": "DocType", "link_to": "Sales Order", "icon": "file-text", "doc_view": ""},
        {"label": "AI Settings", "type": "DocType", "link_to": "Webshop AI Chat Settings", "icon": "cpu", "doc_view": ""},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "layout", "doc_view": ""},
    ]

    for link in links:
        ws_doc.append("links", link)
    
    for sc in shortcuts:
        ws_doc.append("shortcuts", sc)

    ws_doc.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Professional Workspace '{workspace_name}' updated successfully with v15 content format.")

if __name__ == "__main__":
    setup_workspace()
