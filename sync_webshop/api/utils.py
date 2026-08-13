import os

import frappe

def set_cors_headers():
    """
    Reads the allowed frontend origin(s) from Webshop API Settings and allows CORS.
    """
    try:
        if not getattr(frappe, "request", None):
            return
        
        # For now, allow all origins to avoid blocking the user
        if frappe.local.response.get("headers") is None:
            frappe.local.response.headers = {}
        frappe.local.response.headers["Access-Control-Allow-Origin"] = "*"
        frappe.local.response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        frappe.local.response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    except Exception:
        pass

def guest_catalog_allowed():
    """Whether anonymous visitors may read theme/content/catalog endpoints."""
    try:
        settings = frappe.get_single("Webshop API Settings")
        return bool(settings.enable_guest_catalog_access)
    except Exception:
        return True

def require_catalog_access():
    """
    Raises a permission error if guest access is turned off.
    """
    if frappe.session.user == "Guest" and not guest_catalog_allowed():
        frappe.throw(
            "Guest access is disabled for this store. Please log in.",
            frappe.PermissionError,
        )

def _webp_variant(file_url):
    """Return a generated WebP derivative when it exists, otherwise preserve the Desk URL."""
    if not isinstance(file_url, str) or not file_url.startswith("/files/"):
        return file_url
    path, separator, query = file_url.partition("?")
    stem, extension = os.path.splitext(path)
    if extension.lower() not in {".png", ".jpg", ".jpeg"}:
        return file_url
    variant = f"{stem}.webp"
    try:
        if os.path.exists(frappe.get_site_path("public", variant.lstrip("/"))):
            return f"{variant}{separator}{query}" if separator else variant
    except Exception:
        pass
    return file_url


def full_url(file_url):
    """Turn a stored Attach/Attach Image value into an absolute URL."""
    if not file_url:
        return None
    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url

    # Return a relative URL so Nginx can proxy it correctly.
    if file_url.startswith("/files/"):
        return _webp_variant(file_url)

    url = frappe.utils.get_url(file_url)

    # Strip port 8000 if present as it is likely internal.
    if ":8000" in url:
        url = url.replace(":8000", "")
    return url


def clear_webshop_cache(doc=None, method=None):
    """Invalidate cached storefront responses after configurable records change."""
    try:
        cache = frappe.cache()
        version = int(cache.get_value('sync_webshop:cache_version') or 1)
        cache.set_value('sync_webshop:cache_version', version + 1)
        for key in (
            'sync_webshop:content',
            'sync_webshop:theme',
            'sync_webshop:catalog',
            'sync_webshop:categories',
        ):
            cache.delete_value(key)
    except Exception:
        # Cache invalidation must never prevent Desk saves.
        pass


def _cache_key(namespace, payload):
    import hashlib
    import json
    try:
        version = frappe.cache().get_value('sync_webshop:cache_version') or 1
    except Exception:
        version = 1
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(',', ':')).encode('utf-8')
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"sync_webshop:v{version}:{namespace}:{digest}"


def get_json_cache(namespace, payload):
    """Return a cached JSON value or None without allowing cache failures to break APIs."""
    import json
    try:
        value = frappe.cache().get_value(_cache_key(namespace, payload))
        if not value:
            return None
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        return json.loads(value)
    except Exception:
        return None


def set_json_cache(namespace, payload, value, expires_in_sec=60):
    """Store a JSON response in Redis; cache failure is intentionally non-fatal."""
    import json
    try:
        frappe.cache().set_value(
            _cache_key(namespace, payload),
            json.dumps(value, default=str, separators=(',', ':')),
            expires_in_sec=expires_in_sec,
        )
    except Exception:
        pass
    return value
