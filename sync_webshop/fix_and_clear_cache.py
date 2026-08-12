import frappe

def fix_and_clear():
    # 1. Fix DocType modules
    custom_doctypes = frappe.get_all("DocType", filters={"name": ["like", "Webshop %"]})
    for dt in custom_doctypes:
        doc = frappe.get_doc("DocType", dt.name)
        if doc.module != "Sync Webshop":
            doc.module = "Sync Webshop"
            doc.save(ignore_permissions=True)
            print(f"Fixed module for {dt.name}")
    
    # 2. Fix Workspace module
    if frappe.db.exists("Workspace", "Sync Webshop"):
        ws = frappe.get_doc("Workspace", "Sync Webshop")
        ws.module = "Sync Webshop"
        ws.save(ignore_permissions=True)
        print("Fixed module for Workspace 'Sync Webshop'")
        
    # 3. Clear cache
    frappe.clear_cache()
    frappe.db.commit()
    print("Cache cleared and database committed.")

if __name__ == "__main__":
    fix_and_clear()
