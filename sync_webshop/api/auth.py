import frappe
from sync_webshop.api.utils import set_cors_headers

@frappe.whitelist(allow_guest=True)
def customer_login():
    """Authenticates or registers a customer via phone and email, syncing with ERPNext Customer."""
    set_cors_headers()
    try:
        data = frappe.local.form_dict
        email = data.get("email")
        phone = data.get("phone")
        full_name = data.get("full_name", "Customer")
        
        if not email or not phone:
            frappe.throw("Email and phone number are required.")
            
        # Check if customer exists by email or phone in ERPNext
        customer = frappe.db.get_value("Customer", {"email_id": email}, ["name", "customer_name", "mobile_no"], as_dict=True)
        if not customer:
            customer = frappe.db.get_value("Customer", {"mobile_no": phone}, ["name", "customer_name", "mobile_no"], as_dict=True)
            
        if not customer:
            # Create new ERPNext Customer using 'Individual' customer group
            cust_doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": full_name,
                "customer_type": "Individual",
                "customer_group": "Individual",
                "territory": "All Territories",
                "email_id": email,
                "mobile_no": phone
            })
            cust_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            customer_name = cust_doc.name
        else:
            customer_name = customer.name
            
        return {
            "status": "success",
            "customer_id": customer_name,
            "email": email,
            "phone": phone,
            "full_name": full_name
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Customer login failed")
        return {"status": "error", "message": str(e)}
