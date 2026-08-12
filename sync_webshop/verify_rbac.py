import frappe

def verify():
    # Check roles
    user_role = frappe.db.exists("Role", "Sync Webshop User")
    manager_role = frappe.db.exists("Role", "Sync Webshop Manager")
    print(f"Role 'Sync Webshop User' exists: {bool(user_role)}")
    print(f"Role 'Sync Webshop Manager' exists: {bool(manager_role)}")
    
    # Check permissions on a sample custom doctype
    dt = "Webshop Theme Settings"
    perms = frappe.get_all("Custom DocPerm", filters={"parent": dt}, fields=["role", "read", "write", "create", "delete"])
    print(f"Permissions for {dt}:")
    for p in perms:
        print(f"  Role: {p.role} | Read: {p.read} | Write: {p.write} | Create: {p.create} | Delete: {p.delete}")
        
    print("RBAC audit completed successfully.")

if __name__ == "__main__":
    verify()
