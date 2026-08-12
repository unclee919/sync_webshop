import frappe
import json

def setup_workspace():
    workspace_name = "Sync Webshop"
    
    # 1. Ensure Module Def exists
    if not frappe.db.exists("Module Def", "Sync Webshop"):
        frappe.get_doc({
            "doctype": "Module Def",
            "module_name": "Sync Webshop",
            "app_name": "sync_webshop",
            "custom": 0
        }).insert()

    # 2. Define exactly what goes into the workspace
    # The IDs should be consistent to avoid duplication if possible, but for a fresh start we define new ones
    content_blocks = [
        {"id": "h1", "type": "header", "data": {"text": "Sync Webshop Command Center", "level": 2, "col": 12}},
        {"id": "s1", "type": "spacer", "data": {"col": 12}},
        {"id": "h2", "type": "header", "data": {"text": "Essential Shortcuts", "level": 4, "col": 12}},
        # These shortcut_names MUST match the 'label' in the shortcuts table
        {"id": "sc1", "type": "shortcut", "data": {"shortcut_name": "Products", "col": 3}},
        {"id": "sc2", "type": "shortcut", "data": {"shortcut_name": "Orders", "col": 3}},
        {"id": "sc3", "type": "shortcut", "data": {"shortcut_name": "Customers", "col": 3}},
        {"id": "sc4", "type": "shortcut", "data": {"shortcut_name": "Theme Editor", "col": 3}},
        {"id": "s2", "type": "spacer", "data": {"col": 12}},
        {"id": "h3", "type": "header", "data": {"text": "Store Operations", "level": 4, "col": 12}},
        # These card_names MUST match the 'label' in the links table where type is 'Card Break'
        {"id": "c1", "type": "card", "data": {"card_name": "Sales & Inventory", "col": 4}},
        {"id": "c2", "type": "card", "data": {"card_name": "Storefront Design", "col": 4}},
        {"id": "c3", "type": "card", "data": {"card_name": "Marketing & Support", "col": 4}},
    ]

    # 3. Prepare child table data
    shortcuts = [
        {"label": "Products", "type": "DocType", "link_to": "Item", "icon": "list"},
        {"label": "Orders", "type": "DocType", "link_to": "Sales Order", "icon": "file-text"},
        {"label": "Customers", "type": "DocType", "link_to": "Customer", "icon": "users"},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "layout"},
    ]

    links = [
        # Sales & Inventory Card
        {"label": "Sales & Inventory", "type": "Card Break"},
        {"label": "Sales Orders", "link_type": "DocType", "link_to": "Sales Order"},
        {"label": "Items", "link_type": "DocType", "link_to": "Item"},
        {"label": "Item Groups", "link_type": "DocType", "link_to": "Item Group"},
        {"label": "Stock Balance", "link_type": "Report", "link_to": "Stock Balance", "is_query_report": 1},
        
        # Storefront Design Card
        {"label": "Storefront Design", "type": "Card Break"},
        {"label": "Theme Settings", "link_type": "DocType", "link_to": "Webshop Theme Settings"},
        {"label": "Content Settings", "link_type": "DocType", "link_to": "Webshop Content Settings"},
        {"label": "Landing Sections", "link_type": "DocType", "link_to": "Webshop Landing Section"},
        {"label": "SEO Settings", "link_type": "DocType", "link_to": "Webshop SEO Settings"},
        
        # Marketing & Support Card
        {"label": "Marketing & Support", "type": "Card Break"},
        {"label": "AI Chat Settings", "link_type": "DocType", "link_to": "Webshop AI Chat Settings"},
        {"label": "Product Reviews", "link_type": "DocType", "link_to": "Webshop Review"},
        {"label": "Coupon Codes", "link_type": "DocType", "link_to": "Coupon Code"},
        {"label": "Abandoned Carts", "link_type": "DocType", "link_to": "Webshop Abandoned Cart"},
    ]

    # 4. Get or Create Workspace
    ws_doc = None
    if frappe.db.exists("Workspace", "Sync Webshop"):
        ws_doc = frappe.get_doc("Workspace", "Sync Webshop")
        ws_doc.links = []
        ws_doc.shortcuts = []
    else:
        ws_doc = frappe.new_doc("Workspace")
        ws_doc.name = "Sync Webshop"
        ws_doc.label = "Sync Webshop"
        ws_doc.title = "Sync Webshop"
        ws_doc.icon = "shop"
        ws_doc.module = "Sync Webshop"
        ws_doc.is_standard = 0
        ws_doc.public = 1

    ws_doc.content = json.dumps(content_blocks)
    
    for s in shortcuts:
        ws_doc.append("shortcuts", s)
    for l in links:
        ws_doc.append("links", l)

    ws_doc.save(ignore_permissions=True)
    
    # 5. Force module update for DocTypes to ensure they show up
    custom_doctypes = [
        "Webshop Content Settings", "Webshop Theme Settings", "Webshop SEO Settings",
        "Webshop Dashboard Settings", "Webshop AI Chat Settings", "Webshop Review",
        "Webshop Product Settings", "Webshop Paymob Settings", "Webshop Paymob Transaction",
        "Webshop Abandoned Cart", "Webshop Announcement Bar", "Webshop FAQ",
        "Webshop Popup", "Webshop Landing Section", "Webshop Landing Section Item",
        "Webshop Navigation Link", "Webshop Banner", "Webshop Featured Category",
        "Webshop Footer Column", "Webshop Footer Link", "Webshop Footer Settings",
        "Webshop Social Link", "Webshop Testimonial", "Webshop Trust Badge",
        "Webshop Wishlist", "Webshop Help Guide", "Webshop SEO Redirect", "Webshop Shipping Rule"
    ]
    for dt in custom_doctypes:
        if frappe.db.exists("DocType", dt):
            frappe.db.set_value("DocType", dt, "module", "Sync Webshop")

    frappe.db.commit()
    frappe.clear_cache()
    print("Professional Workspace 'Sync Webshop' has been completely rebuilt and DocType modules aligned.")

if __name__ == "__main__":
    setup_workspace()
