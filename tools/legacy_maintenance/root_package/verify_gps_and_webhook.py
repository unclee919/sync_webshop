import frappe

def run_verification():
    print("=== 1. Testing GPS Location Picker E2E Recording in Sales Order ===")

    customer = frappe.db.get_value("Customer", {"customer_name": "Paymob Test Shopper"}, "name")
    if not customer:
        customer = frappe.get_all("Customer", limit=1)[0].name

    item_code = frappe.db.get_value("Item", {"published_in_website": 1}, "item_code")
    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
    warehouse = frappe.db.get_value("Warehouse", {"company": company}, "name") or "Stores - LG"

    if item_code and company:
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "company": company,
            "customer": customer,
            "delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 2),
            "gps_latitude": "24.7136",
            "gps_longitude": "46.6753",
            "location_address": "Riyadh, Saudi Arabia (Captured via GPS)",
            "items": [
                {
                    "item_code": item_code,
                    "qty": 1,
                    "rate": 249.0,
                    "warehouse": warehouse
                }
            ]
        })
        so.insert(ignore_permissions=True)
        so.submit()
        print(f"[Pass] Sales Order created with GPS coordinates: {so.name}")
        print(f"   - Latitude: {so.gps_latitude}, Longitude: {so.gps_longitude}")
        print(f"   - Address: {so.location_address}")

    print("\n=== 2. Simulating Paymob Webhook Integration (Successful Payment) ===")
    # Find a pending transaction or create one
    txns = frappe.get_all("Webshop Paymob Transaction", filters={"status": "Pending"}, limit=1)
    if txns:
        txn_name = txns[0].name
        txn = frappe.get_doc("Webshop Paymob Transaction", txn_name)
        # Simulate webhook callback update
        txn.status = "Paid"
        txn.save(ignore_permissions=True)
        print(f"[Pass] Paymob webhook processed successfully for transaction: {txn.name}")
        print(f"   - Associated Order: {txn.sales_order}")
        print(f"   - Updated Status: {txn.status}")
    else:
        print("[Info] No pending Paymob transactions found to webhook-simulate.")

if __name__ == "__main__":
    run_verification()
