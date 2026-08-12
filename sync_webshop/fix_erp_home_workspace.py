import frappe


def fix():
    user_name = "Administrator"
    target_workspace = "Sync Webshop"

    if not frappe.db.exists("Workspace", target_workspace):
        target_workspace = "Home"

    frappe.db.set_value("User", user_name, "home_page", target_workspace, update_modified=False)
    frappe.db.commit()
    frappe.clear_cache(user=user_name)
    frappe.clear_cache()

    return {
        "user": user_name,
        "home_page": target_workspace,
        "workspace_exists": bool(frappe.db.exists("Workspace", target_workspace)),
    }
