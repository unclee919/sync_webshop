import frappe

def apply_theme():
    theme_json = {"logo":"/files/stBnm71.jpg","favicon":"/files/yGTT3y7.jpg","layout_style":"Bold","primary_color":"#6F4E37","secondary_color":"#C9A66B","accent_color":"#2E2A25","background_color":"#f2f4f5","font_heading":"Playfair Display","font_body":"Cairo","hero_background_image":"/files/pono.jpeg","top_bar_bg_color":"#EC864B","top_bar_text_color":"#f58989","header_bg_color":"#39E4A5","header_text_color":"#852146","nav_bg_color":"#4463F0","nav_text_color":"#0f0f0f","footer_bg_color":"#761ACB","footer_text_color":"#ECAD4B"}
    
    doc = frappe.get_doc("Webshop Theme Settings")
    doc.update(theme_json)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Theme updated.")

def apply_content():
    content_json = {
        "site_name":"Dpono",
        "tagline_en":"Roasted this week, not last season.",
        "hero_quote_en":"Washed process, floral and citrusy — this lot came in three days ago.",
        "show_top_bar":1,
        "phone_number":"01111001318",
        "email_address":"un@gmail.com",
        "contact_address_en":"hk",
        "contact_address_ar":"jgfjhtyt",
        "top_bar_message_en":"tyyyyyyyyyy",
        "top_bar_message_ar":"kjhkjkj"
    }
    
    doc = frappe.get_single("Webshop Content Settings")
    doc.update(content_json)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Content updated.")

if __name__ == "__main__":
    apply_theme()
    apply_content()
