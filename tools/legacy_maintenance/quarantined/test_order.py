import frappe
import json
from sync_webshop.api.checkout import create_order

def run_test():
    try:
        customer = {
            "name": "Test Customer",
            "email": "test@example.com",
            "phone": "0551234567",
            "second_phone": "0557654321",
            "governorate": "All Territories",
            "city": "Saudi Arabia",
            "location": "Test Location"
        }
        items = [
            {"item_code": "SYNC-BASKET-001", "qty": 1}
        ]
        result = create_order(
            customer=customer,
            items=items,
            payment_method="cod",
            delivery_date=frappe.utils.add_days(frappe.utils.nowdate(), 3),
            fulfillment_method="Delivery"
        )
        print("SUCCESS: " + json.dumps(result))
    except Exception as e:
        print("ERROR: " + str(e))
        import traceback
        print(traceback.format_exc())
