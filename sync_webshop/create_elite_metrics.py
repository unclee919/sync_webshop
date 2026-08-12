import frappe
import json

def create_metrics():
    # 1. Create Number Cards
    cards = [
        {
            "name": "Webshop Total Orders",
            "label": "Total Orders",
            "document_type": "Sales Order",
            "function": "Count",
            "aggregate_function_based_on": "",
            "time_span": "Last Year",
            "is_standard": 1,
            "module": "Sync Webshop"
        },
        {
            "name": "Webshop Total Products",
            "label": "Catalog Products",
            "document_type": "Item",
            "function": "Count",
            "aggregate_function_based_on": "",
            "time_span": "Last Year",
            "is_standard": 1,
            "module": "Sync Webshop"
        },
        {
            "name": "Webshop Total Customers",
            "label": "Active Customers",
            "document_type": "Customer",
            "function": "Count",
            "aggregate_function_based_on": "",
            "time_span": "Last Year",
            "is_standard": 1,
            "module": "Sync Webshop"
        },
        {
            "name": "Webshop Revenue",
            "label": "Total Revenue (SAR)",
            "document_type": "Sales Order",
            "function": "Sum",
            "aggregate_function_based_on": "grand_total",
            "time_span": "Last Year",
            "is_standard": 1,
            "module": "Sync Webshop"
        }
    ]

    for c in cards:
        if not frappe.db.exists("Number Card", c["name"]):
            doc = frappe.get_doc({
                "doctype": "Number Card",
                **c
            })
            doc.insert(ignore_permissions=True)
            print(f"Created Number Card: {c['name']}")
        else:
            print(f"Number Card already exists: {c['name']}")

    # 2. Create Dashboard Chart for Sales Trend
    chart_name = "Webshop Sales Trend"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        chart_doc = frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": chart_name,
            "chart_type": "Count",
            "document_type": "Sales Order",
            "based_on": "transaction_date",
            "time_interval": "Monthly",
            "timespan": "Last Year",
            "value_based_on": "",
            "type": "Bar",
            "is_standard": 1,
            "module": "Sync Webshop"
        })
        chart_doc.insert(ignore_permissions=True)
        print(f"Created Dashboard Chart: {chart_name}")
    else:
        print(f"Dashboard Chart already exists: {chart_name}")

    frappe.db.commit()
    print("Elite metrics created successfully.")

if __name__ == "__main__":
    create_metrics()
