import json

import frappe
from frappe.utils import flt, getdate, today

from sync_webshop.api.catalog import _get_price_list
from sync_webshop.api.checkout import _find_or_create_customer, _get_default_company, _get_default_warehouse
from sync_webshop.api.utils import full_url, require_catalog_access, set_cors_headers


AUTO_REPEAT_FREQUENCIES = {"Daily", "Weekly", "Monthly", "Quarterly", "Half-yearly", "Yearly"}


def _supported_subscription_intervals(value):
    return [interval for interval in _csv(value) if interval in AUTO_REPEAT_FREQUENCIES]


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
    landing = _single('Webshop Content Settings', {'landing_builder_enabled': 0, 'landing_hero_heading_en': None, 'landing_hero_heading_ar': None, 'landing_featured_grid_title_en': None, 'landing_featured_grid_title_ar': None})
    commerce = _single('Webshop Content Settings', {'subscription_enabled': 0, 'subscription_discount_percent': 0, 'subscription_intervals': '', 'courier_provider': 'Manual', 'courier_auto_waybill': 0, 'currency_auto_detect': 1, 'supported_currencies': 'SAR'})
    returns = _single('Webshop Content Settings', {'return_window_days': 14})
    try:
        rates = json.loads(commerce.get('exchange_rates_json') or '{}')
        if not isinstance(rates, dict):
            rates = {}
    except Exception:
        rates = {}
    return {
        'landing': {
            'enabled': bool(landing.get('landing_builder_enabled', 0)),
            'hero_heading_en': landing.get('landing_hero_heading_en'),
            'hero_heading_ar': landing.get('landing_hero_heading_ar'),
            'featured_grid_title_en': landing.get('landing_featured_grid_title_en'),
            'featured_grid_title_ar': landing.get('landing_featured_grid_title_ar'),
        },
        'subscriptions': {
            'enabled': bool(commerce.get('subscription_enabled', 0)),
            'discount_percent': float(commerce.get('subscription_discount_percent') or 0),
            'intervals': _supported_subscription_intervals(commerce.get('subscription_intervals')),
        },
        'courier': {
            'provider': commerce.get('courier_provider') or 'Manual',
            'auto_waybill': bool(commerce.get('courier_auto_waybill', 0)),
            'configured': bool(commerce.get_password('courier_api_key') if commerce.get('courier_api_key') else False),
        },
        'returns': {
            'allowed_days': int(returns.get('return_window_days') or 14),
            'policy_text_en': returns.get('return_window_policy_text_en'),
            'policy_text_ar': returns.get('return_window_policy_text_ar'),
        },
        'currencies': {
            'auto_detect': bool(commerce.get('currency_auto_detect', 1)),
            'supported': _csv(commerce.get('supported_currencies')),
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
    settings = _single('Webshop Content Settings', {'subscription_enabled': 0})
    if not settings.get('subscription_enabled'):
        frappe.throw('Subscribe & Save is disabled in Desk settings.')
    if not frappe.db.exists('Item', item_code):
        frappe.throw('The selected item does not exist.')
    allowed = _supported_subscription_intervals(settings.get('subscription_intervals')) or ['Monthly']
    if interval not in allowed:
        frappe.throw('The selected delivery interval is not supported by standard Frappe Auto Repeat or is not enabled in Desk settings.')
    email = frappe.scrub(customer_email).replace('_', '.') if '@' not in customer_email else customer_email.strip().lower()
    price_list = _get_price_list()
    price = frappe.db.get_value('Item Price', {'item_code': item_code, 'price_list': price_list, 'selling': 1}, ['price_list_rate', 'currency'], as_dict=True)
    if not price or not flt(price.price_list_rate):
        frappe.throw('No selling price is configured for the selected item.')
    company = _get_default_company()
    if not company:
        frappe.throw('No default company is configured for subscriptions.')
    customer = _find_or_create_customer({'email': email, 'name': email.split('@')[0]})
    warehouse = _get_default_warehouse(company)
    discount = max(0, min(flt(settings.get('subscription_discount_percent')), 100))
    item = {'item_code': item_code, 'qty': 1, 'rate': flt(price.price_list_rate), 'discount_percentage': discount}
    if warehouse:
        item['warehouse'] = warehouse
    reference = frappe.get_doc({
        'doctype': 'Sales Order',
        'customer': customer,
        'company': company,
        'currency': price.currency or frappe.db.get_value('Company', company, 'default_currency') or 'SAR',
        'selling_price_list': price_list,
        'transaction_date': today(),
        'delivery_date': today(),
        'contact_email': email,
        'items': [item],
    })
    reference.flags.ignore_permissions = True
    reference.insert(ignore_permissions=True)
    repeat = frappe.get_doc({
        'doctype': 'Auto Repeat',
        'reference_doctype': 'Sales Order',
        'reference_document': reference.name,
        'frequency': interval,
        'start_date': today(),
        'submit_on_creation': 0,
        'disabled': 0,
    })
    repeat.insert(ignore_permissions=True)
    return {
        'ok': True,
        'name': repeat.name,
        'status': repeat.status,
        'next_delivery_date': repeat.next_schedule_date,
        'discount_percent': discount,
        'reference_document': reference.name,
    }


@frappe.whitelist()
def get_customer_subscriptions(customer_email):
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required to view subscriptions.')
    email = (customer_email or '').strip().lower()
    if not email:
        return []
    result = []
    repeats = frappe.get_all('Auto Repeat', filters={'reference_doctype': 'Sales Order'}, fields=['name', 'reference_document', 'frequency', 'status', 'disabled', 'next_schedule_date'], order_by='modified desc', limit_page_length=100)
    for repeat in repeats:
        if not repeat.reference_document or not frappe.db.exists('Sales Order', repeat.reference_document):
            continue
        order = frappe.get_doc('Sales Order', repeat.reference_document)
        if (order.contact_email or '').strip().lower() != email:
            continue
        first_item = order.items[0] if order.items else None
        result.append({
            'name': repeat.name,
            'item_code': first_item.item_code if first_item else None,
            'interval': repeat.frequency,
            'status': 'Paused' if repeat.status == 'Disabled' else repeat.status,
            'discount_percent': flt(first_item.discount_percentage) if first_item else 0,
            'next_delivery_date': repeat.next_schedule_date,
            'last_order': repeat.reference_document,
        })
    return result


@frappe.whitelist()
def prepare_courier_waybill(order_name):
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required to prepare a courier waybill.')
    settings = _single('Webshop Content Settings', {'courier_provider': 'Manual', 'courier_auto_waybill': 0})
    if not settings.get('courier_auto_waybill'):
        return {'ok': True, 'status': 'disabled', 'message': 'Automatic courier waybills are disabled in Desk.'}
    if not frappe.db.exists('Sales Order', order_name):
        frappe.throw('Sales Order not found.')
    provider = settings.get('courier_provider') or 'Manual'
    configured = bool(settings.get_password('courier_api_key') if settings.get('courier_api_key') else False)
    return {'ok': True, 'status': 'ready' if configured and provider != 'Manual' else 'safe_mode', 'provider': provider, 'order_name': order_name, 'message': 'Waybill plan prepared. External courier writes remain disabled until provider credentials are verified.'}


def process_due_subscriptions():
    """Compatibility status endpoint; standard Frappe Auto Repeat owns recurring scheduling."""
    return {'status': 'delegated_to_auto_repeat', 'count': 0}
