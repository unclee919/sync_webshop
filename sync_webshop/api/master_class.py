import json

import frappe
from frappe.utils import add_months, getdate, today

from sync_webshop.api.utils import full_url, require_catalog_access, set_cors_headers


def _single(doctype, defaults=None):
    try:
        return frappe.get_single(doctype)
    except Exception:
        return frappe._dict(defaults or {})


def _csv(value):
    return [part.strip() for part in str(value or '').split(',') if part.strip()]


def _social_feed_rows(limit=12):
    if not frappe.db.exists('DocType', 'Webshop Social Feed'):
        return []
    rows = frappe.get_all(
        'Webshop Social Feed',
        filters={'enabled': 1},
        fields=['name', 'platform', 'post_image', 'caption', 'linked_item_code', 'modified'],
        order_by='modified desc',
        limit_page_length=max(1, min(int(limit or 12), 30)),
    )
    result = []
    for row in rows:
        item = None
        if row.linked_item_code and frappe.db.exists('Item', row.linked_item_code):
            item = frappe.db.get_value('Item', row.linked_item_code, ['item_code', 'item_name', 'image'], as_dict=True)
        result.append({
            'name': row.name,
            'platform': row.platform,
            'caption': row.caption,
            'image': full_url(row.post_image) if row.post_image else (full_url(item.image) if item and item.image else None),
            'linked_item_code': row.linked_item_code,
            'linked_item': {**item, 'image': full_url(item.image) if item and item.image else None} if item else None,
        })
    return result


@frappe.whitelist(allow_guest=True)
def get_master_class_settings():
    """Return all non-secret Master Class settings and content managed in Desk."""
    set_cors_headers()
    landing = _single('Webshop Landing Page Builder', {'enabled': 0})
    subscription = _single('Webshop Subscription Settings', {'enabled': 0, 'discount_percent': 0, 'intervals': ''})
    courier = _single('Webshop Courier Settings', {'provider': 'Manual', 'auto_waybill': 0})
    returns = _single('Webshop Return Policy', {'allowed_days': 14})
    currencies = _single('Webshop Currency Settings', {'auto_detect': 1, 'supported_currencies': 'SAR'})
    try:
        rates = json.loads(currencies.get('exchange_rates_json') or '{}')
        if not isinstance(rates, dict):
            rates = {}
    except Exception:
        rates = {}
    return {
        'landing': {
            'enabled': bool(landing.get('enabled', 0)),
            'hero_heading_en': landing.get('hero_heading_en'),
            'hero_heading_ar': landing.get('hero_heading_ar'),
            'featured_grid_title_en': landing.get('featured_grid_title_en'),
            'featured_grid_title_ar': landing.get('featured_grid_title_ar'),
        },
        'subscriptions': {
            'enabled': bool(subscription.get('enabled', 0)),
            'discount_percent': float(subscription.get('discount_percent') or 0),
            'intervals': _csv(subscription.get('intervals')),
        },
        'courier': {
            'provider': courier.get('provider') or 'Manual',
            'auto_waybill': bool(courier.get('auto_waybill', 0)),
            'configured': bool(courier.get_password('api_key') if courier.get('api_key') else False),
        },
        'returns': {
            'allowed_days': int(returns.get('allowed_days') or 14),
            'policy_text_en': returns.get('policy_text_en'),
            'policy_text_ar': returns.get('policy_text_ar'),
        },
        'currencies': {
            'auto_detect': bool(currencies.get('auto_detect', 1)),
            'supported': _csv(currencies.get('supported_currencies')),
            'rates': rates,
        },
        'social_feed': _social_feed_rows(),
    }


@frappe.whitelist(allow_guest=True)
def get_social_feed(limit=12):
    set_cors_headers()
    require_catalog_access()
    return _social_feed_rows(limit)


@frappe.whitelist(allow_guest=True)
def get_personalized_landing(style_profile=None, limit=8):
    """Apply a privacy-first local style profile to catalog ranking without storing the profile."""
    set_cors_headers()
    require_catalog_access()
    tags = style_profile or ''
    if isinstance(style_profile, dict):
        tags = ','.join(str(value) for value in style_profile.values())
    rows = frappe.get_all('Item', filters={'disabled': 0}, fields=['item_code', 'item_name', 'item_group', 'image', 'description'], limit_page_length=100, order_by='modified desc')
    tokens = {token.strip().lower() for token in str(tags).split(',') if token.strip()}
    rows.sort(key=lambda row: sum(token in f"{row.item_name} {row.item_group} {row.description or ''}".lower() for token in tokens), reverse=True)
    result = []
    for row in rows[:max(1, min(int(limit or 8), 24))]:
        rate = frappe.db.get_value('Item Price', {'item_code': row.item_code, 'selling': 1}, 'price_list_rate') or 0
        result.append({**row, 'image': full_url(row.image), 'price': rate, 'currency': 'SAR'})
    return result


@frappe.whitelist()
def create_subscription(customer_email, item_code, interval='Monthly'):
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required to create a subscription.')
    settings = _single('Webshop Subscription Settings', {'enabled': 0})
    if not settings.get('enabled'):
        frappe.throw('Subscribe & Save is disabled in Desk settings.')
    if not frappe.db.exists('Item', item_code):
        frappe.throw('The selected item does not exist.')
    allowed = _csv(settings.get('intervals')) or ['Monthly']
    if interval not in allowed:
        frappe.throw('The selected delivery interval is not enabled in Desk settings.')
    doc = frappe.new_doc('Webshop Subscription')
    doc.customer_email = frappe.scrub(customer_email).replace('_', '.') if '@' not in customer_email else customer_email.strip().lower()
    doc.item_code = item_code
    doc.interval = interval
    doc.status = 'Active'
    doc.discount_percent = float(settings.get('discount_percent') or 0)
    doc.next_delivery_date = today()
    doc.insert(ignore_permissions=True)
    return {'ok': True, 'name': doc.name, 'status': doc.status, 'next_delivery_date': doc.next_delivery_date, 'discount_percent': doc.discount_percent}


@frappe.whitelist()
def get_customer_subscriptions(customer_email):
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required to view subscriptions.')
    email = (customer_email or '').strip().lower()
    if not email:
        return []
    return frappe.get_all('Webshop Subscription', filters={'customer_email': email}, fields=['name', 'item_code', 'interval', 'status', 'discount_percent', 'next_delivery_date', 'last_order'], order_by='modified desc')


@frappe.whitelist()
def prepare_courier_waybill(order_name):
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required to prepare a courier waybill.')
    settings = _single('Webshop Courier Settings', {'provider': 'Manual', 'auto_waybill': 0})
    if not settings.get('auto_waybill'):
        return {'ok': True, 'status': 'disabled', 'message': 'Automatic courier waybills are disabled in Desk.'}
    if not frappe.db.exists('Sales Order', order_name):
        frappe.throw('Sales Order not found.')
    provider = settings.get('provider') or 'Manual'
    configured = bool(settings.get_password('api_key') if settings.get('api_key') else False)
    return {'ok': True, 'status': 'ready' if configured and provider != 'Manual' else 'safe_mode', 'provider': provider, 'order_name': order_name, 'message': 'Waybill plan prepared. External courier writes remain disabled until provider credentials are verified.'}


def process_due_subscriptions():
    """Scheduled, idempotent planning hook; it never creates an order without a configured payment/customer workflow."""
    settings = _single('Webshop Subscription Settings', {'enabled': 0})
    if not settings.get('enabled') or not frappe.db.exists('DocType', 'Webshop Subscription'):
        return {'status': 'disabled', 'count': 0}
    due = frappe.get_all('Webshop Subscription', filters={'status': 'Active', 'next_delivery_date': ['<=', today()]}, fields=['name', 'interval', 'next_delivery_date'], limit_page_length=100)
    for row in due:
        next_date = getdate(row.next_delivery_date or today())
        months = {'Monthly': 1, 'Every 2 Months': 2, 'Quarterly': 3}.get(row.interval, 1)
        frappe.db.set_value('Webshop Subscription', row.name, 'next_delivery_date', add_months(next_date, months))
    frappe.db.commit()
    return {'status': 'planned', 'count': len(due)}
