import frappe
import os
import shutil

def run():
    # 1. Ensure "Sync Webshop" module is linked to "sync_webshop" app
    module_def = frappe.get_doc("Module Def", "Sync Webshop")
    module_def.app_name = "sync_webshop"
    module_def.save(ignore_permissions=True)

    # 2. Identify DocTypes that were wrongly exported to 'frappe' app
    frappe_app_path = frappe.get_app_path("frappe")
    wrong_path = os.path.join(frappe_app_path, "sync_webshop")

    correct_app_path = frappe.get_app_path("sync_webshop")
    correct_module_path = os.path.join(correct_app_path, "sync_webshop")

    if os.path.exists(wrong_path):
        print(f"Moving wrongly exported files from {wrong_path} to {correct_module_path}...")
        for item in os.listdir(wrong_path):
            src = os.path.join(wrong_path, item)
            dst = os.path.join(correct_module_path, item)

            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
            else:
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)

        # Remove the wrong directory
        shutil.rmtree(wrong_path)

    # 3. Update database records for ALL Webshop* DocTypes to be in Sync Webshop module and standard
    doctypes = frappe.get_all("DocType", filters={"name": ["like", "Webshop%"]}, pluck="name")
    for name in doctypes:
        print(f"Ensuring DocType {name} is in Sync Webshop module...")
        frappe.db.set_value("DocType", name, {
            "module": "Sync Webshop",
            "custom": 0
        })

        # Export to files to ensure consistency
        from frappe.modules.export_file import export_to_files
        export_to_files(record_list=[["DocType", name]], record_module="Sync Webshop")

    frappe.db.commit()
    return "Fix v2 complete"
