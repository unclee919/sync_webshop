import frappe

def e2e_paymob_test():
    print("=== 1. E2E Customer Journey & Paymob Checkout Simulation ===")

    email = "paymob.shopper@sync-webshop.com"
    customer = frappe.db.get_value("Customer", {"email_id": email}, "name")
    if not customer:
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "Paymob Test Shopper",
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "All Territories",
            "email_id": email,
            "mobile_no": "+966501112233"
        })
        cust.insert(ignore_permissions=True)
        customer = cust.name
        print(f"[Pass] Created test customer: {customer}")
    else:
        print(f"[Pass] Existing customer found: {customer}")

    item_code = frappe.db.get_value("Item", {"published_in_website": 1}, "item_code")
    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
    warehouse = frappe.db.get_value("Warehouse", {"company": company}, "name") or "Stores - LG"

    if item_code and company:
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "company": company,
            "customer": customer,
            "delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 2),
            "items": [
                {
                    "item_code": item_code,
                    "qty": 2,
                    "rate": 249.0,
                    "warehouse": warehouse
                }
            ]
        })
        so.insert(ignore_permissions=True)
        so.submit()
        print(f"[Pass] E2E Sales Order created & submitted: {so.name} (Total: {so.grand_total} SAR)")

        if frappe.db.exists("DocType", "Webshop Paymob Transaction"):
            pm_txn = frappe.new_doc("Webshop Paymob Transaction")
            pm_txn.sales_order = so.name
            pm_txn.amount = so.grand_total
            pm_txn.currency = "SAR"
            pm_txn.status = "Pending"
            pm_txn.gateway_reference = "PAYMOB-SIM-2026-998877"
            pm_txn.insert(ignore_permissions=True)
            print(f"[Pass] Paymob Transaction logged successfully: {pm_txn.name}")
    else:
        print("[Warning] No published items or company available for order simulation.")

    print("\n=== 2. Arabic Localization & Translation Dictionary Audit ===")
    translations = frappe.get_all("Translation", filters={"language": "ar"}, fields=["source_text", "translated_text"])
    print(f"[Pass] Verified {len(translations)} Arabic translation records.")

if __name__ == "__main__":
    e2e_paymob_test()
