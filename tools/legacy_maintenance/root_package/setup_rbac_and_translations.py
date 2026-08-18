import frappe

def setup_rbac_and_translations():
    # 1. Create Roles
    roles = ["Sync Webshop User", "Sync Webshop Manager"]
    for role_name in roles:
        if not frappe.db.exists("Role", role_name):
            r = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1
            })
            r.insert(ignore_permissions=True)
            print(f"Created Role: {role_name}")
        else:
            print(f"Role already exists: {role_name}")

    # 2. Set Permissions for Custom DocTypes
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
            frappe.db.delete("Custom DocPerm", {"parent": dt})

            manager_perm = frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": dt,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": "Sync Webshop Manager",
                "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1, "amend": 1, "print": 1, "email": 1, "export": 1, "report": 1, "share": 1
            })
            manager_perm.insert(ignore_permissions=True)

            user_perm = frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": dt,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": "Sync Webshop User",
                "read": 1, "write": 1, "create": 0, "delete": 0, "submit": 0, "cancel": 0, "print": 1, "report": 1
            })
            user_perm.insert(ignore_permissions=True)

    # 3. Add core translations (Translation DocType) with correct field names (source_text, translated_text)
    translations = [
        ("Sync Webshop Command Center", "مركز قيادة متجر المزامنة"),
        ("Quick Action Shortcuts", "اختصارات الإجراءات السريعة"),
        ("Store Operations", "عمليات المتجر"),
        ("Storefront & AI", "واجهة المتجر والذكاء الاصطناعي"),
        ("Products", "المنتجات"),
        ("Orders", "الطلبات"),
        ("Customers", "العملاء"),
        ("Theme Editor", "محرر المظهر"),
        ("Sales Orders", "أوامر المبيعات"),
        ("Items", "الأصناف"),
        ("Item Groups", "مجموعات الأصناف"),
        ("Coupon Codes", "كوبونات الخصم"),
        ("Product Reviews", "تقييمات المنتجات"),
        ("Theme Settings", "إعدادات المظهر"),
        ("Content Settings", "إعدادات المحتوى"),
        ("SEO Settings", "إعدادات محركات البحث"),
        ("AI Chat Settings", "إعدادات دردشة الذكاء الاصطناعي"),
        ("Paymob Settings", "إعدادات بايموب"),
        ("Total Orders", "إجمالي الطلبات"),
        ("Catalog Products", "منتجات الكتالوج"),
        ("Active Customers", "العملاء النشطون"),
        ("Total Revenue", "إجمالي الإيرادات"),
        ("Sales Trend", "اتجاه المبيعات")
    ]

    for source_text, target_text in translations:
        existing = frappe.db.exists("Translation", {"source_text": source_text, "language": "ar"})
        if not existing:
            t = frappe.get_doc({
                "doctype": "Translation",
                "language": "ar",
                "source_text": source_text,
                "translated_text": target_text,
                "contributed": 1
            })
            t.insert(ignore_permissions=True)
            print(f"Added translation: {source_text} -> {target_text}")

    frappe.db.commit()
    print("RBAC roles and core translations set up successfully.")

if __name__ == "__main__":
    setup_rbac_and_translations()
