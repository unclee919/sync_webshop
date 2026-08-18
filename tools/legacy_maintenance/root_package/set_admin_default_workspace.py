import frappe


def set_workspace():
    workspace = "Sync Webshop"
    if not frappe.db.exists("Workspace", workspace):
        workspace = "Home"
    frappe.db.set_value("User", "Administrator", "default_workspace", workspace, update_modified=False)
    frappe.db.commit()
    frappe.clear_cache(user="Administrator")
    frappe.clear_cache()
    return {"default_workspace": workspace}
