import json
import re
from datetime import datetime

import frappe
from frappe.utils import flt, get_datetime, now_datetime, today

from sync_webshop.api.utils import full_url, require_catalog_access, set_cors_headers


def _single(doctype, defaults=None):
    try:
        return frappe.get_single(doctype)
    except Exception:
        return frappe._dict(defaults or {})


def _enabled(setting, field, default=0):
    return bool(setting.get(field, default))


def _price(item_code, price_list=None):
    filters = {'item_code': item_code, 'selling': 1}
    if price_list:
        filters['price_list'] = price_list
    return flt(frappe.db.get_value('Item Price', filters, 'price_list_rate') or 0)


def _stock(item_code):
    value = frappe.db.sql('select coalesce(sum(actual_qty), 0) from `tabBin` where item_code=%s', (item_code,))[0][0]
    return flt(value)


@frappe.whitelist(allow_guest=True)
def get_enterprise_settings():
    set_cors_headers()
    ai = _single('Webshop Enterprise AI Settings', {'auto_translate_enabled': 0, 'intelligent_merchandising': 0, 'voice_actions_enabled': 0})
    b2b = _single('Webshop B2B Wholesale Settings', {'b2b_enabled': 0, 'volume_pricing_enabled': 0, 'corporate_credit_enabled': 0, 'quick_order_enabled': 0})
    live = _single('Webshop Live Shopping Settings', {'live_stream_enabled': 0})
    flash = _single('Webshop Flash Sale Settings', {'flash_sale_enabled': 0, 'scarcity_threshold': 5, 'discount_percent': 0})
    recovery = _single('Webshop Recovery Settings', {'abandoned_cart_enabled': 0, 'delay_hours': 2, 'coupon_discount': 0})
    fraud = _single('Webshop Fraud Shield Settings', {'fraud_shield_enabled': 0, 'max_order_amount': 5000})
    infrastructure = _single('Webshop Infrastructure Settings', {'edge_cache_enabled': 0, 'auto_healing_enabled': 0})
    return {
        'ai': {'auto_translate_enabled': _enabled(ai, 'auto_translate_enabled'), 'intelligent_merchandising': _enabled(ai, 'intelligent_merchandising'), 'voice_actions_enabled': _enabled(ai, 'voice_actions_enabled')},
        'b2b': {'enabled': _enabled(b2b, 'b2b_enabled'), 'volume_pricing_enabled': _enabled(b2b, 'volume_pricing_enabled'), 'corporate_credit_enabled': _enabled(b2b, 'corporate_credit_enabled'), 'quick_order_enabled': _enabled(b2b, 'quick_order_enabled')},
        'live_shopping': {'enabled': _enabled(live, 'live_stream_enabled'), 'stream_url': live.get('stream_url'), 'title_en': live.get('stream_title_en'), 'title_ar': live.get('stream_title_ar')},
        'flash_sales': {'enabled': _enabled(flash, 'flash_sale_enabled'), 'scarcity_threshold': flt(flash.get('scarcity_threshold') or 5), 'discount_percent': flt(flash.get('discount_percent') or 0)},
        'recovery': {'enabled': _enabled(recovery, 'abandoned_cart_enabled'), 'delay_hours': flt(recovery.get('delay_hours') or 2), 'coupon_discount': flt(recovery.get('coupon_discount') or 0)},
        'fraud_shield': {'enabled': _enabled(fraud, 'fraud_shield_enabled'), 'max_order_amount': flt(fraud.get('max_order_amount') or 5000)},
        'infrastructure': {'edge_cache_enabled': _enabled(infrastructure, 'edge_cache_enabled'), 'auto_healing_enabled': _enabled(infrastructure, 'auto_healing_enabled')},
    }


@frappe.whitelist(allow_guest=True)
def get_intelligent_merchandising(limit=12):
    set_cors_headers()
    require_catalog_access()
    ai = _single('Webshop Enterprise AI Settings', {'intelligent_merchandising': 0})
    rows = frappe.get_all('Item', filters={'disabled': 0}, fields=['item_code', 'item_name', 'item_group', 'description', 'image'], limit_page_length=100, order_by='modified desc')
    sales_counts = {}
    if _enabled(ai, 'intelligent_merchandising'):
        sales_rows = frappe.db.sql('select item_code, sum(qty) as qty from `tabSales Order Item` soi inner join `tabSales Order` so on so.name=soi.parent where so.docstatus=1 group by item_code', as_dict=True)
        sales_counts = {row.item_code: flt(row.qty) for row in sales_rows}
    rows.sort(key=lambda row: sales_counts.get(row.item_code, 0), reverse=True)
    result = []
    for row in rows[:max(1, min(int(limit or 12), 30))]:
        result.append({**row, 'image': full_url(row.image), 'price': _price(row.item_code), 'currency': 'SAR', 'trend_score': sales_counts.get(row.item_code, 0)})
    return result


@frappe.whitelist()
def auto_translate_item(item_code):
    """Create a safe translation plan using editable Desk fields; no external provider or secret is called automatically."""
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required for AI translation.')
    settings = _single('Webshop Enterprise AI Settings', {'auto_translate_enabled': 0})
    if not _enabled(settings, 'auto_translate_enabled'):
        frappe.throw('AI auto-translation is disabled in Desk settings.')
    item = frappe.get_doc('Item', item_code)
    source = item.get('description') or item.get('item_name') or ''
    phrasebook = {'coffee': 'قهوة', 'beans': 'حبوب', 'natural': 'طبيعي', 'blend': 'خلطة', 'kettle': 'غلاية', 'cup': 'كوب', 'ceramic': 'سيراميك', 'gift': 'هدية', 'house': 'منزلي'}
    translated = ' '.join(phrasebook.get(token.lower().strip('.,'), token) for token in source.split())
    fields = {}
    for fieldname in ('description_ar', 'webshop_description_ar'):
        if item.meta.has_field(fieldname):
            fields[fieldname] = translated
    if fields:
        for fieldname, value in fields.items():
            item.set(fieldname, value)
        item.save(ignore_permissions=True)
    return {'ok': True, 'item_code': item_code, 'status': 'completed' if fields else 'desk_review_required', 'translated_text_ar': translated, 'updated_fields': list(fields)}


@frappe.whitelist(allow_guest=True)
def voice_action(command):
    set_cors_headers()
    settings = _single('Webshop Enterprise AI Settings', {'voice_actions_enabled': 0})
    if not _enabled(settings, 'voice_actions_enabled'):
        return {'ok': False, 'status': 'disabled', 'action': 'none'}
    text = str(command or '').strip().lower()
    if not text:
        return {'ok': False, 'status': 'empty', 'action': 'none'}
    if any(token in text for token in ('coupon', 'كوبون', 'خصم')):
        match = re.search(r'(?:coupon|كوبون)\s*([a-z0-9_-]+)', text)
        return {'ok': True, 'action': 'apply_coupon', 'coupon_code': match.group(1) if match else None}
    items = frappe.get_all('Item', filters={'disabled': 0}, fields=['item_code', 'item_name'], limit_page_length=200)
    for item in items:
        if item.item_name and item.item_name.lower() in text or item.item_code.lower() in text:
            if any(token in text for token in ('add', 'أضف', 'اشتر', 'buy')):
                return {'ok': True, 'action': 'add_to_cart', 'item_code': item.item_code}
            return {'ok': True, 'action': 'search', 'query': item.item_name, 'item_code': item.item_code}
    return {'ok': True, 'action': 'search', 'query': command}


@frappe.whitelist(allow_guest=True)
def get_volume_price(item_code, qty=1):
    set_cors_headers()
    settings = _single('Webshop B2B Wholesale Settings', {'volume_pricing_enabled': 0})
    base = _price(item_code)
    if not _enabled(settings, 'volume_pricing_enabled') or not frappe.db.exists('DocType', 'Webshop Volume Pricing Rule'):
        return {'item_code': item_code, 'qty': flt(qty), 'base_price': base, 'discount_percent': 0, 'unit_price': base, 'currency': 'SAR'}
    rules = frappe.get_all('Webshop Volume Pricing Rule', filters={'enabled': 1, 'item_code': item_code}, fields=['minimum_qty', 'discount_percent', 'price_list'], order_by='minimum_qty desc')
    selected = next((rule for rule in rules if flt(qty) >= flt(rule.minimum_qty)), None)
    discount = flt(selected.discount_percent) if selected else 0
    unit = base * (1 - discount / 100)
    return {'item_code': item_code, 'qty': flt(qty), 'base_price': base, 'discount_percent': discount, 'unit_price': unit, 'currency': 'SAR'}


@frappe.whitelist(allow_guest=True)
def bulk_quick_order(lines):
    set_cors_headers()
    settings = _single('Webshop B2B Wholesale Settings', {'quick_order_enabled': 0})
    if not _enabled(settings, 'quick_order_enabled'):
        frappe.throw('Bulk quick order is disabled in Desk settings.')
    if isinstance(lines, str):
        lines = json.loads(lines or '[]')
    result = []
    for line in (lines or [])[:100]:
        code = str(line.get('item_code') or '').strip()
        qty = max(1, flt(line.get('qty') or 1))
        if not code or not frappe.db.exists('Item', code):
            result.append({'item_code': code, 'qty': qty, 'valid': False, 'reason': 'Item not found'})
            continue
        item = frappe.db.get_value('Item', code, ['item_code', 'item_name', 'image'], as_dict=True)
        pricing = get_volume_price(code, qty)
        result.append({**item, 'image': full_url(item.image) if item.image else None, 'qty': qty, 'valid': True, 'pricing': pricing})
    return {'ok': True, 'lines': result}


@frappe.whitelist(allow_guest=True)
def get_live_shopping():
    set_cors_headers()
    settings = _single('Webshop Live Shopping Settings', {'live_stream_enabled': 0})
    return {'enabled': _enabled(settings, 'live_stream_enabled'), 'stream_url': settings.get('stream_url'), 'title_en': settings.get('stream_title_en'), 'title_ar': settings.get('stream_title_ar')}


@frappe.whitelist(allow_guest=True)
def get_flash_sale_items(limit=12):
    set_cors_headers()
    settings = _single('Webshop Flash Sale Settings', {'flash_sale_enabled': 0, 'scarcity_threshold': 5, 'discount_percent': 0})
    if not _enabled(settings, 'flash_sale_enabled'):
        return []
    now = now_datetime()
    rows = []
    if frappe.db.exists('DocType', 'Webshop Flash Sale Item'):
        rows = frappe.get_all('Webshop Flash Sale Item', filters={'enabled': 1}, fields=['item_code', 'discount_percent', 'start_at', 'end_at'], limit_page_length=30)
    result = []
    for row in rows:
        if row.start_at and get_datetime(row.start_at) > now: continue
        if row.end_at and get_datetime(row.end_at) < now: continue
        if not frappe.db.exists('Item', row.item_code): continue
        stock = _stock(row.item_code)
        if stock <= 0: continue
        item = frappe.db.get_value('Item', row.item_code, ['item_code', 'item_name', 'image'], as_dict=True)
        base = _price(row.item_code)
        discount = flt(row.discount_percent or settings.get('discount_percent') or 0)
        result.append({**item, 'image': full_url(item.image) if item.image else None, 'price': base * (1 - discount / 100), 'old_price': base, 'discount_percent': discount, 'stock': stock, 'scarcity': stock <= flt(settings.get('scarcity_threshold') or 5), 'currency': 'SAR'})
    return result[:max(1, min(int(limit or 12), 24))]


@frappe.whitelist(allow_guest=True)
def get_fit_prediction(item_code, height=None, weight=None, room_width=None, room_depth=None):
    set_cors_headers()
    if not frappe.db.exists('Item', item_code):
        frappe.throw('Item not found.')
    item = frappe.db.get_value('Item', item_code, ['item_name', 'item_group', 'description'], as_dict=True)
    measurements = [flt(value) for value in (height, weight, room_width, room_depth) if value not in (None, '')]
    score = 0.85 if measurements else 0.6
    group = str(item.item_group or '').lower()
    if room_width and room_depth and any(token in group for token in ('furniture', 'home', 'living')):
        score = min(score, 0.9 if flt(room_width) >= 2 and flt(room_depth) >= 2 else 0.45)
    size = 'Standard fit' if not height else ('Regular fit' if flt(height) >= 160 else 'Compact fit')
    return {'ok': True, 'item_code': item_code, 'recommendation': size, 'confidence': score, 'disclaimer': 'Use as guidance only; final fit depends on the product specification configured in Desk.'}


@frappe.whitelist()
def evaluate_order_risk(order_name=None, amount=0, payment_attempts=0):
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required for risk evaluation.')
    settings = _single('Webshop Fraud Shield Settings', {'fraud_shield_enabled': 0, 'max_order_amount': 5000})
    if not _enabled(settings, 'fraud_shield_enabled'):
        return {'status': 'disabled', 'risk_score': 0, 'action': 'approve'}
    amount = flt(amount)
    signals = []
    if amount > flt(settings.get('max_order_amount') or 5000): signals.append('high_value')
    if flt(payment_attempts) >= 3: signals.append('multiple_failed_payments')
    action = 'review' if signals else 'approve'
    if frappe.db.exists('DocType', 'Webshop Fraud Rule'):
        rules = frappe.get_all('Webshop Fraud Rule', filters={'enabled': 1}, fields=['rule_key', 'threshold', 'action'])
        for rule in rules:
            if rule.rule_key == 'High Value' and amount >= flt(rule.threshold): action = str(rule.action or 'Review').lower()
    return {'status': 'evaluated', 'order_name': order_name, 'risk_score': min(100, len(signals) * 35), 'signals': signals, 'action': action}


@frappe.whitelist()
def get_enterprise_analytics():
    if frappe.session.user == 'Guest':
        frappe.throw('Authentication is required for enterprise analytics.')
    orders = frappe.db.sql('select count(*) as count, coalesce(sum(grand_total), 0) as revenue from `tabSales Order` where docstatus=1', as_dict=True)[0]
    return {'orders': int(orders.count or 0), 'revenue': flt(orders.revenue), 'currency': 'SAR', 'catalog_items': frappe.db.count('Item', {'disabled': 0}), 'pending_background_jobs': len(frappe.get_all('RQ Job', filters={'status': ['in', ['queued', 'started']]}, fields=['name'], limit_page_length=100)) if frappe.db.exists('DocType', 'RQ Job') else 0}


def process_abandoned_cart_recovery():
    settings = _single('Webshop Recovery Settings', {'abandoned_cart_enabled': 0})
    if not _enabled(settings, 'abandoned_cart_enabled'):
        return {'status': 'disabled', 'count': 0}
    frappe.logger('sync_webshop').info('Abandoned-cart recovery planning is enabled; outbound messages require configured provider credentials and consent.')
    return {'status': 'safe_mode', 'delay_hours': flt(settings.get('delay_hours') or 2), 'coupon_discount': flt(settings.get('coupon_discount') or 0), 'count': 0}


def run_enterprise_maintenance():
    settings = _single('Webshop Infrastructure Settings', {'edge_cache_enabled': 0, 'auto_healing_enabled': 0})
    result = {'status': 'ok', 'edge_cache_enabled': _enabled(settings, 'edge_cache_enabled'), 'auto_healing_enabled': _enabled(settings, 'auto_healing_enabled')}
    if _enabled(settings, 'auto_healing_enabled'):
        frappe.cache().set_value('sync_webshop_enterprise_last_health_check', now_datetime().isoformat())
    return result
