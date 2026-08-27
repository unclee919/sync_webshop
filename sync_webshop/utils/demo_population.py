import json
from pathlib import Path

import frappe
from frappe.utils import now_datetime
from frappe.utils.file_manager import save_file


ASSET_DIR = Path('/tmp/sync_demo_assets')


def has_field(doctype, fieldname):
    try:
        return bool(frappe.get_meta(doctype).has_field(fieldname))
    except Exception:
        return False


def set_fields(doc, values):
    for fieldname, value in values.items():
        if has_field(doc.doctype, fieldname):
            setattr(doc, fieldname, value)


def existing(doctype, name):
    return bool(frappe.db.exists(doctype, name))


def save_single(doctype, values):
    doc = frappe.get_single(doctype)
    set_fields(doc, values)
    doc.save(ignore_permissions=True)
    return doc


def attach_asset(doctype, docname, filename):
    path = ASSET_DIR / filename
    if not path.exists():
        return None
    existing_file = frappe.db.get_value(
        'File',
        {
            'attached_to_doctype': doctype,
            'attached_to_name': docname,
            'file_name': filename,
        },
        'file_url',
    )
    if existing_file:
        return existing_file
    result = save_file(
        filename,
        path.read_bytes(),
        doctype,
        docname,
        is_private=0,
        decode=False,
    )
    return result.file_url


def ensure_brand(name):
    if not frappe.db.exists('Brand', name):
        doc = frappe.new_doc('Brand')
        doc.brand = name
        doc.insert(ignore_permissions=True)
    return frappe.get_doc('Brand', name)


def ensure_item_group(name, parent='All Item Groups', is_group=0):
    if existing('Item Group', name):
        doc = frappe.get_doc('Item Group', name)
    else:
        doc = frappe.new_doc('Item Group')
        doc.item_group_name = name
    set_fields(doc, {
        'item_group_name': name,
        'parent_item_group': parent,
        'is_group': is_group,
        'show_in_website': 1,
    })
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return doc


def ensure_item(item_code, values, image_filename=None):
    if existing('Item', item_code):
        doc = frappe.get_doc('Item', item_code)
    else:
        doc = frappe.new_doc('Item')
        doc.item_code = item_code
        doc.item_name = values.get('item_name', item_code)
    set_fields(doc, values)
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    if image_filename:
        image_url = attach_asset('Item', doc.name, image_filename)
        if image_url and has_field('Item', 'image'):
            frappe.db.set_value('Item', doc.name, 'image', image_url, update_modified=False)
            doc.image = image_url
    return doc


def ensure_price(item_code, rate, currency):
    price_list = 'Standard Selling'
    if not frappe.db.exists('Price List', price_list):
        doc = frappe.new_doc('Price List')
        doc.price_list_name = price_list
        set_fields(doc, {'selling': 1, 'currency': currency, 'enabled': 1})
        doc.insert(ignore_permissions=True)
    filters = {'item_code': item_code, 'price_list': price_list, 'selling': 1}
    name = frappe.db.get_value('Item Price', filters, 'name')
    if name:
        doc = frappe.get_doc('Item Price', name)
    else:
        doc = frappe.new_doc('Item Price')
        set_fields(doc, filters)
    set_fields(doc, {'price_list_rate': rate, 'currency': currency, 'selling': 1, 'enabled': 1})
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)


def append_rows(doc, table_field, rows):
    if not has_field(doc.doctype, table_field):
        return
    doc.set(table_field, [])
    for row in rows:
        doc.append(table_field, row)


def make_named_doc(doctype, filters, values, child_tables=None):
    name = frappe.db.get_value(doctype, filters, 'name') if filters else None
    if name:
        doc = frappe.get_doc(doctype, name)
    else:
        doc = frappe.new_doc(doctype)
    set_fields(doc, values)
    for table_field, rows in (child_tables or {}).items():
        append_rows(doc, table_field, rows)
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return doc


def _public_storefront_url():
    """Use the Desk-configured storefront URL when creating portable demo data."""
    configured = frappe.db.get_single_value("Webshop API Settings", "public_storefront_url")
    return str(configured or frappe.utils.get_url()).strip().rstrip("/")


def populate_demo():
    frappe.reload_doc('webshop', 'doctype', 'webshop_content_settings')

    currency = frappe.db.get_value('Price List', 'Standard Selling', 'currency') or 'SAR'
    if not frappe.db.exists('Currency', currency):
        currency = 'SAR'

    # Catalog hierarchy.
    ensure_brand('Sync Demo')
    ensure_item_group('Sync Demo Catalog', 'All Item Groups', 1)
    ensure_item_group('Home Living', 'Sync Demo Catalog', 1)
    ensure_item_group('Daily Essentials', 'Sync Demo Catalog', 1)
    ensure_item_group('Gifts & Accessories', 'Sync Demo Catalog', 1)

    products = [
        ('SYNC-JAR-001', 'Sage Lid Storage Jar', 'Home Living', 89, 'reference_product.png', 'A calm, practical ceramic storage jar for counters, shelves, and everyday organization.', 4.9),
        ('SYNC-MUG-001', 'Sage Handle Ceramic Mug', 'Home Living', 49, 'ceramic_mug.png', 'A tactile ceramic mug designed for a quiet coffee or tea ritual.', 4.8),
        ('SYNC-BASKET-001', 'Woven Everyday Basket', 'Home Living', 129, 'woven_basket.png', 'A lightweight woven basket for blankets, accessories, or small household essentials.', 4.7),
        ('SYNC-LAMP-001', 'Soft Glow Table Lamp', 'Home Living', 219, 'desk_lamp.png', 'A warm table lamp that adds a soft, welcoming glow to a reading corner or entryway.', 4.9),
        ('SYNC-POUCH-001', 'Sage Trim Travel Pouch', 'Gifts & Accessories', 69, 'travel_pouch.png', 'A structured canvas pouch for cables, cosmetics, stationery, and travel essentials.', 4.6),
        ('SYNC-KIT-001', 'Everyday Welcome Kit', 'Daily Essentials', 299, 'home_hero.png', 'A curated starter bundle with useful pieces for a calmer everyday routine.', 4.9),
    ]
    item_names = []
    for code, name, group, rate, image, description, rating in products:
        values = {
            'item_code': code,
            'item_name': name,
            'item_group': group,
            'description': description,
            'stock_uom': 'Nos',
            'is_stock_item': 0,
            'is_sales_item': 1,
            'disabled': 0,
            'show_in_website': 1,
            'webshop_rating': rating,
            'brand': 'Sync Demo',
        }
        item = ensure_item(code, values, image)
        ensure_price(item.name, rate, currency)
        item_names.append(item.name)

    # Single settings: intentionally safe demo values; payment secrets remain empty and Stripe disabled.
    public_storefront_url = _public_storefront_url()
    save_single('Webshop API Settings', {
        'api_user': 'Guest',
        'enable_guest_catalog_access': 1,
        'default_price_list': 'Standard Selling',
        'allowed_origins': public_storefront_url,
        'public_storefront_url': public_storefront_url,
    })

    content = save_single('Webshop Content Settings', {
        'site_name': 'Sync Demo Market',
        'tagline_en': 'Everyday essentials, thoughtfully selected.',
        'tagline_ar': 'احتياجات يومية مختارة بعناية.',
        'hero_quote_en': 'Small details. Better everyday living.',
        'hero_quote_ar': 'تفاصيل صغيرة. حياة يومية أفضل.',
        'phone_number': '+966 55 123 4567',
        'email_address': 'hello@sync-demo.example',
        'contact_address_en': 'King Fahd Road, Riyadh, Saudi Arabia',
        'contact_address_ar': 'طريق الملك فهد، الرياض، المملكة العربية السعودية',
        'show_top_bar': 1,
        'top_bar_message_en': 'Free delivery on demo orders over SAR 250',
        'top_bar_message_ar': 'توصيل مجاني للطلبات التجريبية التي تزيد عن ٢٥٠ ريال',
        'about_text_en': '<p>Sync Demo Market is a sample catalog that demonstrates how Frappe Desk content controls the storefront.</p>',
        'about_text_ar': '<p>متجر تجريبي يوضح كيف تتحكم لوحة Frappe Desk في محتوى المتجر.</p>',
        'footer_text_en': 'A flexible storefront for modern businesses.',
        'footer_text_ar': 'واجهة متجر مرنة للأعمال الحديثة.',
        'show_category_sidebar': 1,
        'show_price_filter': 1,
        'show_brand_filter': 1,
        'sidebar_width': 240,
        'seo_meta_description_en': 'Sync Demo Market: practical home, lifestyle, and everyday essentials with a professional bilingual shopping experience.',
        'seo_meta_description_ar': 'متجر سينك التجريبي: مستلزمات منزلية ويومية مع تجربة تسوق احترافية ثنائية اللغة.',
        'seo_keywords': 'home essentials, lifestyle, gifts, Riyadh, متجر, مستلزمات منزلية',
        'show_whatsapp_button': 1,
        'whatsapp_number': '966551234567',
        'whatsapp_message': 'Hello Sync Demo Market, I need help with a product.',
        'show_back_to_top': 1,
        'min_delivery_days': 1,
        'max_delivery_days': 5,
        'header_contact_number': '+966 55 123 4567',
        'need_help_text_en': 'Need help?',
        'need_help_text_ar': 'تحتاج مساعدة؟',
        'support_center_text_en': 'Support',
        'support_center_text_ar': 'الدعم',
        'browse_categories_text_en': 'Browse categories',
        'browse_categories_text_ar': 'تصفح الفئات',
        'all_categories_text_en': 'All categories',
        'all_categories_text_ar': 'كل الفئات',
        'search_placeholder_en': 'Search products, categories and more',
        'search_placeholder_ar': 'ابحث عن المنتجات والفئات والمزيد',
        'wishlist_text_en': 'Wishlist',
        'wishlist_text_ar': 'المفضلة',
        'cart_text_en': 'Cart',
        'cart_text_ar': 'السلة',
        'account_text_en': 'Account',
        'account_text_ar': 'الحساب',
        'shop_now_text_en': 'Shop now',
        'shop_now_text_ar': 'تسوق الآن',
        'best_categories_text_en': 'Shop by category',
        'best_categories_text_ar': 'تسوق حسب الفئة',
        'view_all_text_en': 'View all',
        'view_all_text_ar': 'عرض الكل',
        'new_badge_text_en': 'New',
        'new_badge_text_ar': 'جديد',
        'add_to_cart_text_en': 'Add',
        'add_to_cart_text_ar': 'أضف',
        'item_code_label_en': 'Item code',
        'item_code_label_ar': 'رمز المنتج',
        'category_label_en': 'Category',
        'category_label_ar': 'الفئة',
        'unit_label_en': 'Unit',
        'unit_label_ar': 'الوحدة',
        'added_text_en': 'Added to cart',
        'added_text_ar': 'تمت الإضافة إلى السلة',
        'checkout_title_en': 'Secure checkout',
        'checkout_title_ar': 'إتمام الدفع الآمن',
        'order_success_title_en': 'Thank you for your order',
        'order_success_title_ar': 'شكراً لطلبك',
        'continue_shopping_text_en': 'Continue shopping',
        'continue_shopping_text_ar': 'متابعة التسوق',
        'contact_us_text_en': 'Contact us',
        'contact_us_text_ar': 'تواصل معنا',
        'track_order_text_en': 'Track order',
        'track_order_text_ar': 'تتبع الطلب',
        'open_menu_text_en': 'Open menu',
        'open_menu_text_ar': 'فتح القائمة',
        'home_text_en': 'Home',
        'home_text_ar': 'الرئيسية',
        'all_products_text_en': 'All products',
        'all_products_text_ar': 'كل المنتجات',
        'why_us_text_en': 'Why shop with us',
        'why_us_text_ar': 'لماذا نحن',
        'search_button_text_en': 'Search',
        'search_button_text_ar': 'بحث',
        'category_label_short_en': 'Featured',
        'category_label_short_ar': 'مختارات',
        'product_label_short_en': 'Product',
        'product_label_short_ar': 'منتج',
        'enable_quick_view': 1,
        'enable_faceted_search': 1,
    })
    append_rows(content, 'banners', [
        {'image': '/files/sync-demo-home-hero.png', 'title': 'Small details. Better everyday living.', 'subtitle': 'Curated essentials for your home, routine, and thoughtful gifting.', 'link_url': '/products', 'sort_order': 1, 'is_active': 1},
        {'image': '/files/sync-demo-home-hero.png', 'title': 'A calmer way to discover useful things.', 'subtitle': 'Browse practical pieces selected for modern businesses and homes.', 'link_url': '/products', 'sort_order': 2, 'is_active': 1},
    ])
    append_rows(content, 'featured_categories', [
        {'item_group': 'Home Living', 'display_label_en': 'Home Living', 'display_label_ar': 'المنزل والمعيشة', 'image': '/files/sync-demo-home-hero.png', 'sort_order': 1, 'is_active': 1},
        {'item_group': 'Daily Essentials', 'display_label_en': 'Daily Essentials', 'display_label_ar': 'الاحتياجات اليومية', 'image': '/files/sync-demo-mug.png', 'sort_order': 2, 'is_active': 1},
        {'item_group': 'Gifts & Accessories', 'display_label_en': 'Gifts & Accessories', 'display_label_ar': 'الهدايا والإكسسوارات', 'image': '/files/sync-demo-pouch.png', 'sort_order': 3, 'is_active': 1},
    ])
    append_rows(content, 'nav_links', [
        {'label_en': 'Home Living', 'label_ar': 'المنزل والمعيشة', 'link_url': '/products?category=Home%20Living', 'item_group': 'Home Living', 'is_external': 0, 'show_in_navbar': 1, 'show_in_browse_menu': 1, 'sort_order': 1},
        {'label_en': 'Daily Essentials', 'label_ar': 'الاحتياجات اليومية', 'link_url': '/products?category=Daily%20Essentials', 'item_group': 'Daily Essentials', 'is_external': 0, 'show_in_navbar': 1, 'show_in_browse_menu': 1, 'sort_order': 2},
        {'label_en': 'Gifts & Accessories', 'label_ar': 'الهدايا والإكسسوارات', 'link_url': '/products?category=Gifts%20%26%20Accessories', 'item_group': 'Gifts & Accessories', 'is_external': 0, 'show_in_navbar': 1, 'show_in_browse_menu': 1, 'sort_order': 3},
    ])
    append_rows(content, 'social_links', [
        {'platform': 'Instagram', 'link_url': 'https://instagram.com/', 'icon': 'instagram'},
        {'platform': 'Facebook', 'link_url': 'https://facebook.com/', 'icon': 'facebook'},
        {'platform': 'TikTok', 'link_url': 'https://tiktok.com/', 'icon': 'tiktok'},
    ])
    append_rows(content, 'testimonials', [
        {'quote_en': 'The storefront makes it easy to discover useful products without feeling crowded.', 'quote_ar': 'واجهة المتجر تجعل اكتشاف المنتجات المفيدة سهلاً ومنظماً.', 'author': 'Noura A.', 'author_title': 'Demo customer', 'sort_order': 1, 'is_active': 1},
        {'quote_en': 'The Arabic and English experience feels clear and consistent on mobile.', 'quote_ar': 'التجربة العربية والإنجليزية واضحة ومتناسقة على الهاتف.', 'author': 'Omar K.', 'author_title': 'Demo customer', 'sort_order': 2, 'is_active': 1},
    ])
    append_rows(content, 'trust_badges', [
        {'icon': 'Delivery', 'label_en': 'Reliable delivery', 'label_ar': 'توصيل موثوق', 'description_en': 'Clear delivery expectations from checkout to doorstep.', 'description_ar': 'توقعات واضحة للتوصيل من الدفع حتى الاستلام.', 'sort_order': 1, 'is_active': 1},
        {'icon': 'Quality', 'label_en': 'Thoughtful selection', 'label_ar': 'اختيارات بعناية', 'description_en': 'Products organized around real everyday needs.', 'description_ar': 'منتجات منظمة حول الاحتياجات اليومية الحقيقية.', 'sort_order': 2, 'is_active': 1},
        {'icon': 'Payment', 'label_en': 'Flexible payment', 'label_ar': 'دفع مرن', 'description_en': 'Cash on delivery is enabled for this demo.', 'description_ar': 'الدفع عند الاستلام مفعّل لهذا العرض التجريبي.', 'sort_order': 3, 'is_active': 1},
        {'icon': 'Support', 'label_en': 'Human support', 'label_ar': 'دعم بشري', 'description_en': 'Reach the demo team by phone or WhatsApp.', 'description_ar': 'تواصل مع فريق العرض عبر الهاتف أو واتساب.', 'sort_order': 4, 'is_active': 1},
    ])
    content.save(ignore_permissions=True)

    # Product rails used by the homepage.
    make_named_doc(
        'Webshop Landing Section',
        {'section_title_en': 'New arrivals'},
        {'section_title_en': 'New arrivals', 'section_title_ar': 'وصل حديثاً', 'enabled': 1, 'sort_order': 1, 'section_subtitle_en': 'Useful pieces for a more considered everyday.', 'section_subtitle_ar': 'قطع مفيدة ليوم أكثر ترتيباً.'},
        {'items': [{'item_code': code} for code in item_names[:4]]},
    )
    make_named_doc(
        'Webshop Landing Section',
        {'section_title_en': 'Gifts and useful details'},
        {'section_title_en': 'Gifts and useful details', 'section_title_ar': 'هدايا وتفاصيل مفيدة', 'enabled': 1, 'sort_order': 2, 'section_subtitle_en': 'Simple ideas for thoughtful giving.', 'section_subtitle_ar': 'أفكار بسيطة لهدايا مدروسة.'},
        {'items': [{'item_code': code} for code in item_names[2:]]},
    )

    theme = save_single('Webshop Theme Settings', {
        'layout_style': 'Oasis',
        'primary_color': '#173F3A',
        'secondary_color': '#6E9274',
        'accent_color': '#D6A85E',
        'background_color': '#F8F6F0',
        'top_bar_bg_color': '#173F3A',
        'top_bar_text_color': '#FFFFFF',
        'header_bg_color': '#FFFFFF',
        'header_text_color': '#173F3A',
        'nav_bg_color': '#FFFFFF',
        'nav_text_color': '#173F3A',
        'footer_bg_color': '#173F3A',
        'footer_text_color': '#FFFFFF',
        'font_heading': 'Poppins',
        'font_body': 'Inter',
        'header_max_width': 1240,
        'header_height': 84,
        'header_padding_vertical': 16,
        'header_padding_horizontal': 20,
        'logo_height': 48,
        'search_bar_max_width': 620,
        'search_bar_height': 48,
        'nav_bar_height': 54,
        'hero_height': 480,
        'hero_width': 1240,
    })
    hero_url = attach_asset('Webshop Theme Settings', theme.name, 'home_hero.png')
    if hero_url and has_field('Webshop Theme Settings', 'hero_background_image'):
        frappe.db.set_value('Webshop Theme Settings', theme.name, 'hero_background_image', hero_url, update_modified=False)

    footer = save_single('Webshop Content Settings', {
        'footer_enabled': 1,
        'footer_copyright_en': '© 2026 Sync Demo Market. All rights reserved.',
        'footer_copyright_ar': '© ٢٠٢٦ متجر سينك التجريبي. جميع الحقوق محفوظة.',
    })
    footer_url = attach_asset('Webshop Content Settings', footer.name, 'home_hero.png')
    if footer_url and has_field('Webshop Content Settings', 'footer_logo'):
        frappe.db.set_value('Webshop Content Settings', footer.name, 'footer_logo', footer_url, update_modified=False)

    make_named_doc('Webshop Footer Column', {'title_en': 'Explore'}, {'title_en': 'Explore', 'title_ar': 'استكشف', 'sort_order': 1, 'enabled': 1}, {'links': [
        {'label_en': 'Home', 'label_ar': 'الرئيسية', 'link_url': '/', 'is_external': 0},
        {'label_en': 'All products', 'label_ar': 'كل المنتجات', 'link_url': '/products', 'is_external': 0},
        {'label_en': 'Contact us', 'label_ar': 'تواصل معنا', 'link_url': '/contact-us', 'is_external': 0},
    ]})
    make_named_doc('Webshop Footer Column', {'title_en': 'Customer care'}, {'title_en': 'Customer care', 'title_ar': 'خدمة العملاء', 'sort_order': 2, 'enabled': 1}, {'links': [
        {'label_en': 'Track order', 'label_ar': 'تتبع الطلب', 'link_url': '/track', 'is_external': 0},
        {'label_en': 'Wishlist', 'label_ar': 'المفضلة', 'link_url': '/wishlist', 'is_external': 0},
        {'label_en': 'Why shop with us', 'label_ar': 'لماذا نحن', 'link_url': '/features', 'is_external': 0},
    ]})

    save_single('Webshop Content Settings', {
        'announcement_enabled': 1,
        'announcement_message_en': 'Welcome to the Sync Demo Market — all content is managed from Frappe Desk.',
        'announcement_message_ar': 'مرحباً بك في متجر سينك التجريبي — كل المحتوى يُدار من Frappe Desk.',
        'announcement_background_color': '#D6A85E',
        'announcement_text_color': '#173F3A',
        'announcement_link_url': '/products',
        'announcement_show_close_button': 1,
    })
    save_single('Webshop Payment Settings', {
        'stripe_enabled': 0,
        'stripe_mode': 'Test',
        'cod_enabled': 1,
        'cod_label_en': 'Cash on Delivery',
        'cod_label_ar': 'الدفع عند الاستلام',
    })
    save_single('Webshop Product Settings', {
        'enable_zoom': 1,
        'show_related_products': 1,
        'related_products_title_en': 'You may also like',
        'related_products_title_ar': 'قد يعجبك أيضاً',
        'show_sidebar': 1,
    })
    save_single('Webshop Content Settings', {
        'meta_title_en': 'Sync Demo Market | Everyday essentials',
        'meta_title_ar': 'متجر سينك التجريبي | احتياجات يومية',
        'meta_description_en': 'Discover practical home, lifestyle, gift, and everyday products in a clear bilingual storefront.',
        'meta_description_ar': 'اكتشف منتجات منزلية ويومية وهدايا في متجر ثنائي اللغة واضح واحترافي.',
        'og_title_en': 'Sync Demo Market',
        'og_title_ar': 'متجر سينك التجريبي',
        'og_description_en': 'Everyday essentials, thoughtfully selected.',
        'og_description_ar': 'احتياجات يومية مختارة بعناية.',
        'canonical_url': f'{public_storefront_url}/',
        'robots_txt': 'User-agent: *\nAllow: /',
        'sitemap_enabled': 1,
        'structured_data': json.dumps({'@context': 'https://schema.org', '@type': 'Store', 'name': 'Sync Demo Market', 'url': f'{public_storefront_url}/'}, ensure_ascii=False),
    })
    seo = frappe.get_single('Webshop Content Settings')
    append_rows(seo, 'redirects', [
        {'source_url': '/demo', 'target_url': '/products', 'redirect_type': '301'},
    ])
    seo.save(ignore_permissions=True)
    seo_url = attach_asset('Webshop Content Settings', seo.name, 'home_hero.png')
    if seo_url and has_field('Webshop Content Settings', 'og_image'):
        frappe.db.set_value('Webshop Content Settings', seo.name, 'og_image', seo_url, update_modified=False)

    save_single('Webshop Content Settings', {
        'help_content': '<h2>Sync Demo Market</h2><p>Use Frappe Desk to update banners, categories, navigation, theme colors, pricing, and product availability. This record is safe demo content.</p>',
    })

    make_named_doc('Webshop FAQ', {'question_en': 'How is delivery configured?'}, {'question_en': 'How is delivery configured?', 'question_ar': 'كيف يتم إعداد التوصيل؟', 'answer_en': 'Delivery windows and shipping rules are controlled from Frappe Desk.', 'answer_ar': 'يتم التحكم في أوقات التوصيل وقواعد الشحن من Frappe Desk.', 'sort_order': 1, 'is_active': 1})
    make_named_doc('Webshop FAQ', {'question_en': 'Can I change the homepage content?'}, {'question_en': 'Can I change the homepage content?', 'question_ar': 'هل يمكنني تغيير محتوى الصفحة الرئيسية؟', 'answer_en': 'Yes. Banners, category tiles, product rails, trust badges, and testimonials are managed in Webshop Content Settings.', 'answer_ar': 'نعم. تتم إدارة اللافتات والفئات والمنتجات وشارات الثقة وآراء العملاء من إعدادات محتوى المتجر.', 'sort_order': 2, 'is_active': 1})
    make_named_doc('Webshop Shipping Rule', {'rule_name': 'Demo Standard Delivery'}, {'rule_name': 'Demo Standard Delivery', 'enabled': 1, 'shipping_cost': 25, 'free_shipping_threshold': 250})
    make_named_doc('Webshop Shipping Rule', {'rule_name': 'Demo Free Delivery'}, {'rule_name': 'Demo Free Delivery', 'enabled': 1, 'shipping_cost': 0, 'free_shipping_threshold': 250})
    make_named_doc('Webshop Popup', {'title_en': 'Welcome to Sync Demo Market'}, {'enabled': 1, 'title_en': 'Welcome to Sync Demo Market', 'title_ar': 'مرحباً بك في متجر سينك التجريبي', 'content_en': '<p>Explore the sample catalog and see how every storefront section is controlled from Frappe Desk.</p>', 'content_ar': '<p>استكشف الكتالوج التجريبي وشاهد كيف يتم التحكم في أقسام المتجر من Frappe Desk.</p>', 'popup_type': 'Offer', 'link_url': '/products', 'button_text_en': 'Explore products', 'button_text_ar': 'استكشف المنتجات', 'delay_seconds': 8, 'show_once_per_session': 1})

    frappe.db.commit()
    return {
        'status': 'ok',
        'currency': currency,
        'item_groups': ['Sync Demo Catalog', 'Home Living', 'Daily Essentials', 'Gifts & Accessories'],
        'items': item_names,
        'message': 'Sync Webshop demo data and configuration populated successfully.',
        'timestamp': str(now_datetime()),
    }
