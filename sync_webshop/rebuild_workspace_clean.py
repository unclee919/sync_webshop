import frappe
import json

def rebuild():
    # 1. Delete all existing workspaces with our label
    existing = frappe.get_all("Workspace", filters={"name": ["in", ["Sync Webshop", "Sync Webshop Pro"]]})
    for e in existing:
        frappe.delete_doc("Workspace", e.name, force=True)
        print(f"Deleted old workspace: {e.name}")
        
    # 2. Create new workspace
    ws = frappe.new_doc("Workspace")
    ws.name = "Sync Webshop"
    ws.label = "Sync Webshop"
    ws.title = "Sync Webshop"
    ws.icon = "shop"
    ws.module = "Sync Webshop"
    ws.is_standard = 0
    ws.public = 1
    
    # Simple content blocks that avoid complex card/shortcut resolution issues in v15
    # We will use standard link groups
    content_blocks = [
        {"id": "h1", "type": "header", "data": {"text": "Sync Webshop Dashboard", "level": 2, "col": 12}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        {"id": "card1", "type": "card", "data": {"card_name": "Store Management", "col": 6}},
        {"id": "card2", "type": "card", "data": {"card_name": "Storefront Design", "col": 6}},
    ]
    
    ws.content = json.dumps(content_blocks)
    
    # Add links representing card headers and items
    links = [
        # Store Management Card
        {"label": "Store Management", "type": "Card Break"},
        {"label": "Sales Orders", "link_type": "DocType", "link_to": "Sales Order"},
        {"label": "Items", "link_type": "DocType", "link_to": "Item"},
        {"label": "Customers", "link_type": "DocType", "link_to": "Customer"},
        {"label": "Coupon Codes", "link_type": "DocType", "link_to": "Coupon Code"},
        
        # Storefront Design Card
        {"label": "Storefront Design", "type": "Card Break"},
        {"label": "Theme Settings", "link_type": "DocType", "link_to": "Webshop Theme Settings"},
        {"label": "Content Settings", "link_type": "DocType", "link_to": "Webshop Content Settings"},
        {"label": "SEO Settings", "link_type": "DocType", "link_to": "Webshop SEO Settings"},
        {"label": "AI Chat Settings", "link_type": "DocType", "link_to": "Webshop AI Chat Settings"},
    ]
    
    for l in links:
        ws.append("links", l)
        
    ws.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache()
    print("Clean workspace 'Sync Webshop' rebuilt successfully.")

if __name__ == "__main__":
    rebuild()
