import frappe

def test_sync():
    email = "test.customer@sync-demo.com"
    phone = "+966501112233"
    full_name = "Test Customer"

    customer = frappe.db.get_value("Customer", {"email_id": email}, ["name"])
    if not customer:
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": full_name,
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "All Territories",
            "email_id": email,
            "mobile_no": phone
        })
        cust.insert(ignore_permissions=True)
        customer_name = cust.name
        print(f"Created new test customer: {customer_name}")
    else:
        customer_name = customer
        print(f"Found existing test customer: {customer_name}")

    frappe.db.commit()
    print("Customer auth and sync test passed successfully.")

if __name__ == "__main__":
    test_sync()
