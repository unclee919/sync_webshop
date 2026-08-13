# Copyright (c) 2026, Sync Webshop and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist(allow_guest=True)
def get_ecosystem_settings():
    return {
        "ai": {
            "rag_support_enabled": bool(frappe.db.get_single_value("Webshop Ecosystem AI Settings", "rag_support_enabled")),
            "demand_forecaster_enabled": bool(frappe.db.get_single_value("Webshop Ecosystem AI Settings", "demand_forecaster_enabled")),
            "marketing_hub_enabled": bool(frappe.db.get_single_value("Webshop Ecosystem AI Settings", "marketing_hub_enabled")),
        },
        "marketplace": {
            "multi_vendor_enabled": bool(frappe.db.get_single_value("Webshop Marketplace Vendor Settings", "multi_vendor_enabled")),
            "commission_percent": float(frappe.db.get_single_value("Webshop Marketplace Vendor Settings", "commission_percent") or 15.0),
            "affiliate_enabled": bool(frappe.db.get_single_value("Webshop Marketplace Vendor Settings", "affiliate_enabled")),
        },
        "fintech": {
            "gift_cards_enabled": bool(frappe.db.get_single_value("Webshop Fintech Settings", "gift_cards_enabled")),
            "subscription_box_enabled": bool(frappe.db.get_single_value("Webshop Fintech Settings", "subscription_box_enabled")),
        },
        "omnichannel": {
            "bopis_enabled": bool(frappe.db.get_single_value("Webshop Omnichannel Settings", "bopis_enabled")),
            "kiosk_mode_enabled": bool(frappe.db.get_single_value("Webshop Omnichannel Settings", "kiosk_mode_enabled")),
        }
    }

@frappe.whitelist(allow_guest=True)
def rag_support_query(question):
    if not question:
        return {"answer": "Please ask a question about our products, shipping, or returns."}
    q = question.lower()
    if "shipping" in q or "delivery" in q:
        return {"answer": "We offer reliable shipping across the region with clear tracking from dispatch to delivery. Standard delivery takes 2-4 business days."}
    if "return" in q:
        return {"answer": "Items can be returned within 14 days of receipt, provided they are in their original condition and packaging."}
    if "coffee" in q or "bean" in q:
        return {"answer": "Our specialty coffee beans are ethically sourced, freshly roasted, and available for single purchase or flexible 'Subscribe & Save' delivery."}
    return {"answer": f"Thank you for your question regarding '{question}'. Our autonomous support agent and team are ready to assist you via WhatsApp or phone."}

@frappe.whitelist(allow_guest=True)
def get_branches():
    return [
        {"name": "Riyadh Flagship Branch", "city": "Riyadh", "address": "King Fahd Road, Al Olaya", "stock_status": "Fully Stocked", "ready_in": "Ready in 1 hour"},
        {"name": "Jeddah Corniche Hub", "city": "Jeddah", "address": "Al Corniche Road", "stock_status": "Available", "ready_in": "Ready in 2 hours"},
        {"name": "Dubai Financial Centre", "city": "Dubai", "address": "DIFC Gate Avenue", "stock_status": "Limited Stock", "ready_in": "Ready in 1 hour"},
    ]

@frappe.whitelist(allow_guest=True)
def redeem_gift_card(code):
    if not code:
        return {"valid": False, "message": "Gift card code is required."}
    card = frappe.db.get_value("Webshop Gift Card", {"code": code, "status": "Active"}, ["name", "remaining_balance"], as_dict=True)
    if not card:
        return {"valid": False, "message": "Invalid or expired gift card code."}
    return {"valid": True, "remaining_balance": float(card.remaining_balance or 0), "message": "Gift card applied successfully."}
