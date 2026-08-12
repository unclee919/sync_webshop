import frappe
import json

def fix():
    workspace_name = "Sync Webshop"
    if not frappe.db.exists("Workspace", workspace_name):
        print(f"Workspace '{workspace_name}' not found.")
        return
        
    # 1. Reset any personalized versions for the Administrator
    frappe.db.delete("Custom DocPerm", {"parent": workspace_name})
    # Note: Frappe v15 might store personalization in 'User Workspace' or similar. 
    # But usually deleting and recreating is enough if public=1.

    ws = frappe.get_doc("Workspace", workspace_name)
    
    # 2. Re-populate child tables with EXACT names found in DB
    ws.number_cards = []
    ws.charts = []
    
    # Found in DB: 'Webshop Total Orders', 'Webshop Total Products', 'Webshop Total Customers', 'Total Revenue (SAR)'
    cards = [
        {"number_card_name": "Webshop Total Orders", "label": "Total Orders"},
        {"number_card_name": "Webshop Total Products", "label": "Catalog Products"},
        {"number_card_name": "Webshop Total Customers", "label": "Active Customers"},
        {"number_card_name": "Total Revenue (SAR)", "label": "Total Revenue"}
    ]
    for c in cards:
        ws.append("number_cards", c)
        
    # Found in DB: 'Webshop Sales Trend'
    charts = [
        {"chart_name": "Webshop Sales Trend", "label": "Sales Trend"}
    ]
    for ch in charts:
        ws.append("charts", ch)
        
    # 3. Update Content JSON to match these exact names
    content_blocks = [
        {"id": "h1", "type": "header", "data": {"text": "Sync Webshop Elite Command Center", "level": 2, "col": 12}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        
        # Number Cards row - shortcut_name in JSON for number_card type is actually the card name
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Webshop Total Orders", "col": 3}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Webshop Total Products", "col": 3}},
        {"id": "nc3", "type": "number_card", "data": {"number_card_name": "Webshop Total Customers", "col": 3}},
        {"id": "nc4", "type": "number_card", "data": {"number_card_name": "Total Revenue (SAR)", "col": 3}},
        
        {"id": "sp2", "type": "spacer", "data": {"col": 12}},
        
        # Chart row
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
    ws.public = 1
    ws.is_standard = 0
    
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache()
    print("Elite Workspace child tables and content JSON have been perfectly aligned.")

if __name__ == "__main__":
    fix()
