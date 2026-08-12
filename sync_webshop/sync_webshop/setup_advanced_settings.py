import frappe

def create_single_doctype(name, description, fields):
    if not frappe.db.exists("Module Def", "Sync Webshop"):
        m = frappe.new_doc("Module Def")
        m.module_name = "Sync Webshop"
        m.app_name = "sync_webshop"
        m.insert(ignore_permissions=True)

    if frappe.db.exists("DocType", name):
        doc = frappe.get_doc("DocType", name)
        existing = {row.fieldname for row in doc.get("fields") or []}
        added = 0
        for field in fields:
            if field.get("fieldname") not in existing:
                doc.append("fields", field)
                added += 1
        if added:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"Updated DocType {name} with {added} configurable fields.")
        else:
            print(f"DocType {name} already exists.")
        return
    
    doc = frappe.new_doc("DocType")
    doc.name = name
    doc.module = "Sync Webshop"
    doc.custom = 1
    doc.issingle = 1
    doc.is_table = 0
    doc.editable_grid = 1
    doc.track_changes = 1
    doc.engine = "InnoDB"
    doc.description = description
    
    for f in fields:
        doc.append("fields", f)
        
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Created DocType: {name}")

def ensure_existing_fields(doctype_name, fields):
    if not frappe.db.exists("DocType", doctype_name):
        return
    doc = frappe.get_doc("DocType", doctype_name)
    existing = {row.fieldname for row in doc.get("fields") or []}
    added = 0
    for field in fields:
        if field.get("fieldname") not in existing:
            doc.append("fields", field)
            added += 1
    if added:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Updated DocType {doctype_name} with {added} fields.")


def create_review_doctype():
    name = "Webshop Review"
    fields = [
        {"fieldname": "item_code", "label": "Item", "fieldtype": "Link", "options": "Item", "reqd": 1},
        {"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer"},
        {"fieldname": "order_name", "label": "Verified Sales Order", "fieldtype": "Link", "options": "Sales Order"},
        {"fieldname": "rating", "label": "Rating", "fieldtype": "Int", "reqd": 1},
        {"fieldname": "review_title", "label": "Review Title", "fieldtype": "Data"},
        {"fieldname": "review_text", "label": "Review Text", "fieldtype": "Long Text"},
        {"fieldname": "display_name", "label": "Display Name", "fieldtype": "Data"},
        {"fieldname": "status", "label": "Moderation Status", "fieldtype": "Select", "options": "Pending\nApproved\nRejected", "default": "Pending"},
        {"fieldname": "verified_purchase", "label": "Verified Purchase", "fieldtype": "Check"},
    ]
    if frappe.db.exists("DocType", name):
        doc = frappe.get_doc("DocType", name)
        existing = {row.fieldname for row in doc.get("fields") or []}
        for field in fields:
            if field["fieldname"] not in existing:
                doc.append("fields", field)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"DocType {name} already exists.")
        return
    doc = frappe.new_doc("DocType")
    doc.name = name
    doc.module = "Sync Webshop"
    doc.custom = 1
    doc.issingle = 0
    doc.is_table = 0
    doc.track_changes = 1
    doc.autoname = "hash"
    for field in fields:
        doc.append("fields", field)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"Created DocType: {name}")


def run_all():
    frappe.init(site="erpnext.localhost", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()

    # 0. Existing content settings extensions
    ensure_existing_fields("Webshop Content Settings", [
        {"fieldname": "mega_menu_enabled", "label": "Mega Menu Enabled", "fieldtype": "Check", "default": "1"},
        {"fieldname": "mega_menu_max_categories", "label": "Mega Menu Maximum Root Categories", "fieldtype": "Int", "default": "12"},
        {"fieldname": "mega_menu_title_en", "label": "Mega Menu Title (English)", "fieldtype": "Data", "default": "Browse categories"},
        {"fieldname": "mega_menu_title_ar", "label": "Mega Menu Title (Arabic)", "fieldtype": "Data", "default": "تصفح الأقسام"},
        {"fieldname": "mega_menu_featured_image", "label": "Mega Menu Featured Image", "fieldtype": "Attach Image"},
        {"fieldname": "mega_menu_featured_title_en", "label": "Mega Menu Featured Title (English)", "fieldtype": "Data"},
        {"fieldname": "mega_menu_featured_title_ar", "label": "Mega Menu Featured Title (Arabic)", "fieldtype": "Data"},
        {"fieldname": "mega_menu_featured_url", "label": "Mega Menu Featured URL", "fieldtype": "Data"},
    ])

    # 1. Paymob Settings
    paymob_fields = [
        {"fieldname": "enabled", "label": "Enabled", "fieldtype": "Check", "default": "0"},
        {"fieldname": "secret_key", "label": "Secret Key", "fieldtype": "Password"},
        {"fieldname": "public_key", "label": "Public Key", "fieldtype": "Data"},
        {"fieldname": "hmac_secret", "label": "HMAC Secret", "fieldtype": "Password"},
        {"fieldname": "card_integration_id", "label": "Card Integration ID", "fieldtype": "Data"},
        {"fieldname": "wallet_integration_id", "label": "Wallet Integration ID", "fieldtype": "Data"},
        {"fieldname": "kiosk_integration_id", "label": "Kiosk Integration ID", "fieldtype": "Data"},
        {"fieldname": "payment_methods", "label": "Additional Payment Method IDs", "fieldtype": "Data"},
        {"fieldname": "checkout_mode", "label": "Checkout Mode", "fieldtype": "Select", "options": "redirect\npixel", "default": "redirect"},
        {"fieldname": "label_en", "label": "English Label", "fieldtype": "Data", "default": "Paymob"},
        {"fieldname": "label_ar", "label": "Arabic Label", "fieldtype": "Data", "default": "الدفع عبر Paymob"},
    ]
    create_single_doctype("Webshop Paymob Settings", "Paymob Payment Gateway Configuration", paymob_fields)

    transaction_fields = [
        {"fieldname": "sales_order", "label": "Sales Order", "fieldtype": "Link", "options": "Sales Order"},
        {"fieldname": "intention_id", "label": "Intention ID", "fieldtype": "Data", "unique": 1},
        {"fieldname": "transaction_id", "label": "Transaction ID", "fieldtype": "Data"},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency"},
        {"fieldname": "currency", "label": "Currency", "fieldtype": "Data"},
        {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending\nPaid\nFailed\nRefunded", "default": "Pending"},
        {"fieldname": "hmac_verified", "label": "HMAC Verified", "fieldtype": "Check"},
        {"fieldname": "customer_email", "label": "Customer Email", "fieldtype": "Data"},
        {"fieldname": "raw_response", "label": "Raw Response", "fieldtype": "Long Text"},
        {"fieldname": "raw_callback", "label": "Raw Callback", "fieldtype": "Long Text"},
    ]
    create_single_doctype("Webshop Paymob Transaction", "Paymob Payment Transaction Ledger", transaction_fields)

    # 2. AI Chat Settings
    ai_fields = [
        {"fieldname": "enabled", "label": "Enabled", "fieldtype": "Check", "default": "0"},
        {"fieldname": "provider", "label": "Provider", "fieldtype": "Select", "options": "OpenAI\nManus\nCustom", "default": "OpenAI"},
        {"fieldname": "api_key", "label": "API Key", "fieldtype": "Password"},
        {"fieldname": "api_base_url", "label": "API Base URL", "fieldtype": "Data", "default": "https://api.openai.com/v1"},
        {"fieldname": "model", "label": "Model Name", "fieldtype": "Data", "default": "gpt-5-mini"},
        {"fieldname": "system_prompt", "label": "System Prompt", "fieldtype": "Small Text", "default": "You are a helpful and professional customer support AI assistant for our webshop. Help users find products, check order status, and answer questions about store policies."},
        {"fieldname": "greeting_message", "label": "Greeting Message", "fieldtype": "Data", "default": "Hello! How can I help you with your shopping today?"},
        {"fieldname": "primary_color", "label": "Widget Primary Color", "fieldtype": "Color", "default": "#10b981"},
        {"fieldname": "allow_guest", "label": "Allow Guest Chat", "fieldtype": "Check", "default": "1"},
        {"fieldname": "rate_limit_per_minute", "label": "Messages per Minute", "fieldtype": "Int", "default": "20"},
        {"fieldname": "max_message_length", "label": "Maximum Message Length", "fieldtype": "Int", "default": "2000"},
        {"fieldname": "max_tokens", "label": "Maximum Response Tokens", "fieldtype": "Int", "default": "500"},
        {"fieldname": "temperature", "label": "Response Temperature", "fieldtype": "Float", "default": "0.2"},
    ]
    create_single_doctype("Webshop AI Chat Settings", "AI Chat Widget Configuration", ai_fields)

    # 3. Dashboard Settings
    dashboard_fields = [
        {"fieldname": "enable_analytics", "label": "Enable Order Analytics", "fieldtype": "Check", "default": "1"},
        {"fieldname": "enable_loyalty", "label": "Enable Loyalty Points", "fieldtype": "Check", "default": "1"},
        {"fieldname": "enable_profile_edit", "label": "Enable Profile Editing", "fieldtype": "Check", "default": "1"},
        {"fieldname": "enable_rma", "label": "Enable RMA / Returns", "fieldtype": "Check", "default": "1"},
        {"fieldname": "enable_tracking_timeline", "label": "Enable Visual Order Timeline", "fieldtype": "Check", "default": "1"},
        {"fieldname": "enable_addresses", "label": "Enable Saved Addresses", "fieldtype": "Check", "default": "1"},
        {"fieldname": "tracking_labels_en", "label": "Tracking Labels (English JSON)", "fieldtype": "Long Text", "default": '{"placed":"Order placed","confirmed":"Confirmed","processing":"Preparing","shipped":"Shipped","delivered":"Delivered"}'},
        {"fieldname": "tracking_labels_ar", "label": "Tracking Labels (Arabic JSON)", "fieldtype": "Long Text", "default": '{"placed":"تم تقديم الطلب","confirmed":"تم التأكيد","processing":"قيد التجهيز","shipped":"تم الشحن","delivered":"تم التسليم"}'},
    ]
    create_single_doctype("Webshop Dashboard Settings", "Customer Portal Dashboard Configuration", dashboard_fields)

    ensure_existing_fields("Webshop Product Settings", [
        {"fieldname": "reviews_enabled", "label": "Product Reviews Enabled", "fieldtype": "Check", "default": "1"},
        {"fieldname": "reviews_require_approval", "label": "Require Review Approval", "fieldtype": "Check", "default": "1"},
        {"fieldname": "reviews_allow_guest", "label": "Allow Guest Reviews", "fieldtype": "Check", "default": "0"},
        {"fieldname": "reviews_title_en", "label": "Reviews Title (English)", "fieldtype": "Data", "default": "Customer reviews"},
        {"fieldname": "reviews_title_ar", "label": "Reviews Title (Arabic)", "fieldtype": "Data", "default": "آراء العملاء"},
        {"fieldname": "enable_recently_viewed", "label": "Enable Recently Viewed", "fieldtype": "Check", "default": "1"},
        {"fieldname": "recently_viewed_limit", "label": "Recently Viewed Limit", "fieldtype": "Int", "default": "8"},
        {"fieldname": "recently_viewed_title_en", "label": "Recently Viewed Title (English)", "fieldtype": "Data", "default": "Recently viewed"},
        {"fieldname": "recently_viewed_title_ar", "label": "Recently Viewed Title (Arabic)", "fieldtype": "Data", "default": "شوهدت مؤخراً"},
    ])
    create_review_doctype()

    print("All advanced settings DocTypes verified/created.")
    frappe.destroy()

if __name__ == "__main__":
    run_all()
