import hashlib
import json
import os

import frappe


def _allowed_origins():
    """Return the normalized CORS origin allow-list configured in Desk."""
    try:
        raw_origins = str(frappe.get_single("Webshop API Settings").get("allowed_origins") or "")
    except Exception:
        return set()
    return {line.strip().rstrip("/") for line in raw_origins.splitlines() if line.strip()}


def set_cors_headers():
    """Apply CORS only for origins explicitly configured in Webshop API Settings."""
    try:
        request = getattr(frappe, "request", None)
        if not request:
            return
        origin = str(request.headers.get("Origin") or "").strip().rstrip("/")
        if not origin or origin not in _allowed_origins():
            return
        headers = frappe.local.response.get("headers") or {}
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Frappe-CSRF-Token"
        frappe.local.response["headers"] = headers
    except Exception:
        # A response header failure must not make the storefront unavailable.
        pass


def guest_catalog_allowed():
    """Whether anonymous visitors may read theme, content, and catalog endpoints."""
    try:
        settings = frappe.get_single("Webshop API Settings")
        return bool(settings.enable_guest_catalog_access)
    except Exception:
        return False


def require_catalog_access():
    """Raise a permission error if anonymous catalog access has been disabled."""
    if frappe.session.user == "Guest" and not guest_catalog_allowed():
        frappe.throw("Guest access is disabled for this store. Please log in.", frappe.PermissionError)


def _webp_variant(file_url):
    """Return a generated WebP derivative when it exists; otherwise preserve the Desk URL."""
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
    """Return a safe storefront file URL from an Attach or Attach Image value."""
    if not file_url:
        return None
    if file_url.startswith(("http://", "https://")):
        return file_url
    if file_url.startswith("/files/"):
        return _webp_variant(file_url)
    url = frappe.utils.get_url(file_url)
    return url.replace(":8000", "")


def clear_webshop_cache(doc=None, method=None):
    """Invalidate all versioned storefront API caches after configurable records change."""
    try:
        cache = frappe.cache()
        version = int(cache.get_value("sync_webshop:cache_version") or 1)
        cache.set_value("sync_webshop:cache_version", version + 1)
    except Exception:
        # Cache invalidation must never prevent a Desk save.
        pass


def _cache_key(namespace, payload):
    try:
        version = frappe.cache().get_value("sync_webshop:cache_version") or 1
    except Exception:
        version = 1
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"sync_webshop:v{version}:{namespace}:{digest}"


def get_json_cache(namespace, payload):
    """Read a JSON cache entry without allowing Redis errors to break public APIs."""
    try:
        value = frappe.cache().get_value(_cache_key(namespace, payload))
        if not value:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)
    except Exception:
        return None


def set_json_cache(namespace, payload, value, expires_in_sec=60):
    """Write a JSON cache entry and return the original value."""
    try:
        frappe.cache().set_value(
            _cache_key(namespace, payload),
            json.dumps(value, default=str, separators=(",", ":")),
            expires_in_sec=expires_in_sec,
        )
    except Exception:
        pass
    return value
