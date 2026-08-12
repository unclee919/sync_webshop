import frappe
from sync_webshop.api.utils import set_cors_headers

@frappe.whitelist(allow_guest=True)
def get_robots_txt():
    """Returns the robots.txt content from SEO settings."""
    set_cors_headers()
    try:
        seo_settings = frappe.get_single("Webshop SEO Settings")
        content = seo_settings.robots_txt or "User-agent: *\nAllow: /"
        
        # Add sitemap link if enabled
        if seo_settings.sitemap_enabled:
            base_url = frappe.utils.get_url()
            content += f"\n\nSitemap: {base_url}/api/method/sync_webshop.api.seo.get_sitemap"
            
        frappe.response.type = "binary"
        frappe.response.display = "inline"
        frappe.response.filename = "robots.txt"
        frappe.response.filecontent = content
    except Exception:
        frappe.response.filecontent = "User-agent: *\nAllow: /"

@frappe.whitelist(allow_guest=True)
def get_sitemap():
    """Generates a dynamic XML sitemap of products and categories."""
    set_cors_headers()
    try:
        seo_settings = frappe.get_single("Webshop SEO Settings")
        if not seo_settings.sitemap_enabled:
            frappe.throw("Sitemap is disabled.")
            
        base_url = frappe.utils.get_url()
        urls = []
        
        # Static pages
        for path in ["/", "/products", "/cart", "/login"]:
            urls.append(f"<url><loc>{base_url}{path}</loc><priority>0.8</priority></url>")
            
        # Categories
        categories = frappe.get_all("Item Group", filters={"show_in_website": 1}, fields=["name"])
        for cat in categories:
            urls.append(f"<url><loc>{base_url}/products?category={frappe.utils.data.quote(cat.name)}</loc><priority>0.7</priority></url>")
            
        # Products - Use whitelisted visibility field
        items = frappe.get_all("Item", filters={"disabled": 0, "published_in_website": 1}, fields=["item_code"])
        for item in items:
            urls.append(f"<url><loc>{base_url}/product/{frappe.utils.data.quote(item.item_code)}</loc><priority>0.9</priority></url>")
            
        xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml += "\n".join(urls)
        xml += "\n</urlset>"
        
        frappe.response.type = "binary"
        frappe.response.display = "inline"
        frappe.response.filename = "sitemap.xml"
        frappe.response.filecontent = xml
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sitemap generation failed")
        frappe.throw(f"Sitemap generation failed: {str(e)}")
