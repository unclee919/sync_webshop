import frappe

def setup_workspace():
    workspace_name = "Sync Webshop"
    
    # 1. Check if workspace exists
    ws_doc = None
    existing = frappe.get_all("Workspace", filters={"label": workspace_name}, limit=1)
    if existing:
        ws_doc = frappe.get_doc("Workspace", existing[0].name)
        ws_doc.links = []
        ws_doc.shortcuts = []
    else:
        ws_doc = frappe.new_doc("Workspace")
        ws_doc.label = workspace_name
        ws_doc.title = "Sync Webshop"
        ws_doc.icon = "shopping-cart"
        ws_doc.module = "Sync Webshop"
        ws_doc.is_standard = 0
        ws_doc.public = 1

    # Sections and Links
    links = [
        # Storefront Settings Section
        {"label": "Storefront Settings", "type": "Card Break"},
        {"label": "Content Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Content Settings"},
        {"label": "Theme Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Theme Settings"},
        {"label": "SEO Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop SEO Settings"},
        {"label": "Dashboard Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Dashboard Settings"},
        
        # AI & Support Section
        {"label": "AI & Customer Support", "type": "Card Break"},
        {"label": "AI Chat Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop AI Chat Settings"},
        {"label": "Product Reviews", "type": "Link", "link_type": "DocType", "link_to": "Webshop Review"},
        
        # Catalog & Sales Section
        {"label": "Catalog & Sales", "type": "Card Break"},
        {"label": "Products", "type": "Link", "link_type": "DocType", "link_to": "Item"},
        {"label": "Product Groups", "type": "Link", "link_type": "DocType", "link_to": "Item Group"},
        {"label": "Sales Orders", "type": "Link", "link_type": "DocType", "link_to": "Sales Order"},
        
        # Marketing & Growth Section
        {"label": "Marketing & Growth", "type": "Card Break"},
        {"label": "Coupon Codes", "type": "Link", "link_type": "DocType", "link_to": "Coupon Code"},
        {"label": "Abandoned Carts", "type": "Link", "link_type": "DocType", "link_to": "Webshop Abandoned Cart"},
        {"label": "Product Display Settings", "type": "Link", "link_type": "DocType", "link_to": "Webshop Product Settings"},
        
        # Logistics & Finance Section
        {"label": "Logistics & Finance", "type": "Card Break"},
        {"label": "Territories (Governorates/Cities)", "type": "Link", "link_type": "DocType", "link_to": "Territory"},
        {"label": "Paymob Integration", "type": "Link", "link_type": "DocType", "link_to": "Webshop Paymob Settings"},
        {"label": "Payment Transactions", "type": "Link", "link_type": "DocType", "link_to": "Webshop Paymob Transaction"},
    ]
    
    # Shortcuts for quick access
    shortcuts = [
        {"label": "Manage Catalog", "type": "DocType", "link_to": "Item", "icon": "list"},
        {"label": "View Orders", "type": "DocType", "link_to": "Sales Order", "icon": "file-text"},
        {"label": "AI Settings", "type": "DocType", "link_to": "Webshop AI Chat Settings", "icon": "cpu"},
        {"label": "Theme Editor", "type": "DocType", "link_to": "Webshop Theme Settings", "icon": "layout"},
    ]

    for link in links:
        ws_doc.append("links", link)
    
    for shortcut in shortcuts:
        ws_doc.append("shortcuts", shortcut)
    
    ws_doc.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Professional Workspace '{workspace_name}' updated/created successfully.")

if __name__ == "__main__":
    setup_workspace()
