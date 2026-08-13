import frappe
from sync_webshop.api.utils import get_json_cache, set_cors_headers, full_url, set_json_cache
from sync_webshop.api.catalog import _get_price_list
from sync_webshop.api.theme import get_theme

@frappe.whitelist(allow_guest=True)
def get_content():
	"""
	Returns this server's text content and settings.
	"""
	set_cors_headers()
	cached = get_json_cache("content_elite_v2", {})
	if cached is not None:
		return cached
	try:
		settings = frappe.get_single("Webshop Content Settings")
	except Exception:
		settings = frappe._dict({
			"site_name": "Sync Webshop",
			"banners": [],
			"featured_categories": [],
			"testimonials": [],
			"trust_badges": [],
			"nav_links": [],
			"social_links": []
		})
	
	def active_sorted(rows):
		if not rows: return []
		active = [r for r in rows if r.get("is_active")]
		return sorted(active, key=lambda r: r.get("sort_order") or 0)

	banners = [
		{
			"image": full_url(row.image),
			"title": row.title,
			"subtitle": row.subtitle,
			"link_url": row.link_url,
		}
		for row in active_sorted(settings.get("banners"))
	]

	featured_categories = [
		{
			"item_group": row.item_group,
			"label_en": row.display_label_en or row.item_group,
			"label_ar": row.display_label_ar,
			"image": full_url(row.image),
		}
		for row in active_sorted(settings.get("featured_categories"))
	]

	testimonials = [
		{
			"quote_en": row.quote_en,
			"quote_ar": row.quote_ar,
			"author": row.author,
			"author_title": row.author_title,
		}
		for row in active_sorted(settings.get("testimonials"))
	]

	trust_badges = [
		{
			"icon": row.icon,
			"label_en": row.label_en,
			"label_ar": row.label_ar,
			"description_en": row.description_en,
			"description_ar": row.description_ar,
		}
		for row in active_sorted(settings.get("trust_badges"))
	]

	nav_links = []
	if settings.get("nav_links"):
		sorted_links = sorted(settings.nav_links, key=lambda x: x.sort_order or 0)
		for row in sorted_links:
			link_url = row.link_url
			if row.item_group and not link_url:
				link_url = f"/products?category={row.item_group}"
			
			nav_links.append({
				"label_en": row.label_en,
				"label_ar": row.label_ar,
				"link_url": link_url,
				"item_group": row.item_group,
				"is_external": row.is_external,
				"show_in_navbar": row.show_in_navbar,
				"show_in_browse_menu": row.show_in_browse_menu,
				"sort_order": row.sort_order
			})

	social_links = [
		{
			"platform": row.platform,
			"link_url": row.link_url,
			"icon": row.icon
		}
		for row in settings.get("social_links", [])
	]

	landing_sections = []
	try:
		sections = frappe.get_all(
			"Webshop Landing Section",
			filters={"enabled": 1},
			fields=["name", "section_title_en", "section_title_ar", "section_subtitle_en", "section_subtitle_ar", "sort_order"],
			order_by="sort_order asc"
		)
		price_list = _get_price_list()
		currency = frappe.db.get_value("Price List", price_list, "currency") or "SAR"

		for sec in sections:
			sec_doc = frappe.get_doc("Webshop Landing Section", sec.name)
			items_list = []
			for itm_row in sec_doc.items:
				item_code = itm_row.item_code
				if not frappe.db.exists("Item", item_code):
					continue
				item_doc = frappe.get_doc("Item", item_code)
				rate = frappe.db.get_value(
					"Item Price",
					{"price_list": price_list, "item_code": item_code, "selling": 1},
					"price_list_rate"
				) or 0
				items_list.append({
					"item_code": item_code,
					"item_name": item_doc.item_name,
					"description": item_doc.description,
					"image": full_url(item_doc.image),
					"price": rate,
					"currency": currency,
					"rating": getattr(item_doc, "webshop_rating", 5.0) or 5.0
				})
			landing_sections.append({
				"title_en": sec.section_title_en,
				"title_ar": sec.section_title_ar,
				"subtitle_en": sec.section_subtitle_en,
				"subtitle_ar": sec.section_subtitle_ar,
				"sort_order": sec.sort_order,
				"items": items_list
			})
	except Exception:
		pass

	footer_settings_data = {}
	try:
		footer_settings = frappe.get_single("Webshop Footer Settings")
		columns = frappe.get_all(
			"Webshop Footer Column",
			filters={"enabled": 1},
			fields=["name", "title_en", "title_ar", "sort_order"],
			order_by="sort_order asc"
		)
		cols_data = []
		for col in columns:
			col_doc = frappe.get_doc("Webshop Footer Column", col.name)
			links_data = [
				{
					"label_en": l.label_en,
					"label_ar": l.label_ar,
					"link_url": l.link_url,
					"is_external": l.is_external
				} for l in col_doc.links
			]
			cols_data.append({
				"title_en": col.title_en,
				"title_ar": col.title_ar,
				"sort_order": col.sort_order,
				"links": links_data
			})
		footer_settings_data = {
			"enabled": footer_settings.enabled,
			"footer_logo": full_url(footer_settings.footer_logo) if footer_settings.footer_logo else None,
			"copyright_en": footer_settings.copyright_en,
			"copyright_ar": footer_settings.copyright_ar,
			"columns": cols_data
		}
	except Exception:
		pass

	announcement_data = {}
	try:
		announcement = frappe.get_single("Webshop Announcement Bar")
		if announcement.enabled:
			announcement_data = {
				"message_en": announcement.message_en,
				"message_ar": announcement.message_ar,
				"background_color": announcement.background_color,
				"text_color": announcement.text_color,
				"link_url": announcement.link_url,
				"show_close_button": announcement.show_close_button
			}
	except Exception:
		pass

	product_settings_data = {}
	try:
		product_settings = frappe.get_single("Webshop Product Settings")
		product_settings_data = {
			"enable_zoom": product_settings.enable_zoom,
			"enable_immersive_viewer": getattr(product_settings, "enable_immersive_viewer", 1),
			"enable_video_hover": getattr(product_settings, "enable_video_hover", 1),
			"complete_the_look_enabled": getattr(product_settings, "complete_the_look_enabled", 1),
			"complete_the_look_title_en": getattr(product_settings, "complete_the_look_title_en", "Complete the look"),
			"complete_the_look_title_ar": getattr(product_settings, "complete_the_look_title_ar", "أكمل الإطلالة"),
			"show_related_products": product_settings.show_related_products,
			"related_products_title_en": product_settings.related_products_title_en,
			"related_products_title_ar": product_settings.related_products_title_ar,
			"show_sidebar": product_settings.show_sidebar,
			"reviews_enabled": getattr(product_settings, "reviews_enabled", 1),
			"reviews_title_en": getattr(product_settings, "reviews_title_en", "Customer reviews"),
			"reviews_title_ar": getattr(product_settings, "reviews_title_ar", "آراء العملاء"),
			"enable_recently_viewed": getattr(product_settings, "enable_recently_viewed", 1),
			"recently_viewed_limit": getattr(product_settings, "recently_viewed_limit", 8) or 8,
			"recently_viewed_title_en": getattr(product_settings, "recently_viewed_title_en", "Recently viewed"),
							"recently_viewed_title_ar": getattr(product_settings, "recently_viewed_title_ar", "شوهدت مؤخراً"),
				"ar_enabled": getattr(product_settings, "ar_enabled", 1),
				"ar_ios_model_url": getattr(product_settings, "ar_ios_model_url", ""),
				"ar_android_model_url": getattr(product_settings, "ar_android_model_url", ""),
				"three_d_model_url": getattr(product_settings, "three_d_model_url", ""),
				"exploded_view_enabled": getattr(product_settings, "exploded_view_enabled", 1),
				"exploded_view_title_en": getattr(product_settings, "exploded_view_title_en", "Inspect the details"),
				"exploded_view_title_ar": getattr(product_settings, "exploded_view_title_ar", "استكشف التفاصيل"),
				"fit_guide_enabled": getattr(product_settings, "fit_guide_enabled", 1),
				"fit_guide_title_en": getattr(product_settings, "fit_guide_title_en", "Find your best fit"),
				"fit_guide_title_ar": getattr(product_settings, "fit_guide_title_ar", "اعثر على المقاس المناسب"),

		}
	except Exception:
		pass

	stories_data = []
	try:
		stories = frappe.get_all(
			"Webshop Story",
			filters={"is_active": 1},
			fields=["image", "title_en", "title_ar", "subtitle_en", "subtitle_ar", "link_url", "accent_color", "sort_order"],
			order_by="sort_order asc",
		)
		stories_data = [
			{
				"image": full_url(story.image) if story.image else None,
				"title_en": story.title_en,
				"title_ar": story.title_ar,
				"subtitle_en": story.subtitle_en,
				"subtitle_ar": story.subtitle_ar,
				"link_url": story.link_url,
				"accent_color": story.accent_color,
				"sort_order": story.sort_order,
				"is_active": 1,
			}
			for story in stories
		]
	except Exception:
		pass

	editorial_collections = []
	try:
		collections = frappe.get_all(
			"Webshop Editorial Collection",
			filters={"is_published": 1},
			fields=["name", "slug", "title_en", "title_ar", "intro_en", "intro_ar", "cover_image", "cover_image_alt_en", "cover_image_alt_ar", "accent_color", "cta_text_en", "cta_text_ar", "cta_url", "sort_order"],
			order_by="sort_order asc, modified desc",
		)
		for collection in collections:
			hotspot_rows = []
			try:
				hotspot_rows = frappe.get_all(
					"Webshop Editorial Hotspot",
					filters={"parent": collection.name, "parenttype": "Webshop Editorial Collection", "parentfield": "hotspots", "enabled": 1},
					fields=["section_sort_order", "label_en", "label_ar", "description_en", "description_ar", "item_code", "link_url", "x_percent", "y_percent", "sort_order"],
					order_by="sort_order asc",
				)
			except Exception:
				hotspot_rows = []
			hotspots_by_section = {}
			for hotspot in hotspot_rows:
				featured = None
				if hotspot.item_code:
					featured = frappe.db.get_value("Item", hotspot.item_code, ["item_code", "item_name", "image", "item_group"], as_dict=True)
				entry = {
					"label_en": hotspot.label_en, "label_ar": hotspot.label_ar,
					"description_en": hotspot.description_en, "description_ar": hotspot.description_ar,
					"link_url": hotspot.link_url, "x_percent": max(0, min(100, float(hotspot.x_percent or 50))),
					"y_percent": max(0, min(100, float(hotspot.y_percent or 50))),
					"featured_item": {**featured, "image": full_url(featured.image) if featured and featured.image else None} if featured else None,
				}
				hotspots_by_section.setdefault(int(hotspot.section_sort_order or 0), []).append(entry)
			sections = frappe.get_all(
				"Webshop Editorial Section",
				filters={"parent": collection.name, "parenttype": "Webshop Editorial Collection"},
				fields=["layout", "eyebrow_en", "eyebrow_ar", "title_en", "title_ar", "body_en", "body_ar", "image", "image_2", "item_code", "link_url", "cta_text_en", "cta_text_ar", "sort_order"],
				order_by="sort_order asc",
			)
			serialized_sections = []
			for section in sections:
				featured_item = None
				if section.item_code:
					featured_item = frappe.db.get_value("Item", section.item_code, ["item_code", "item_name", "image", "item_group"], as_dict=True)
				serialized_sections.append({
					"layout": section.layout,
					"eyebrow_en": section.eyebrow_en,
					"eyebrow_ar": section.eyebrow_ar,
					"title_en": section.title_en,
					"title_ar": section.title_ar,
					"body_en": section.body_en,
					"body_ar": section.body_ar,
					"image": full_url(section.image) if section.image else None,
					"image_2": full_url(section.image_2) if section.image_2 else None,
					"item_code": section.item_code,
					"link_url": section.link_url,
					"cta_text_en": section.cta_text_en,
					"cta_text_ar": section.cta_text_ar,
					"sort_order": section.sort_order,
					"hotspots": hotspots_by_section.get(int(section.sort_order or 0), []),
					"featured_item": {**featured_item, "image": full_url(featured_item.image) if featured_item and featured_item.image else None} if featured_item else None,
				})
			editorial_collections.append({
				"slug": collection.slug,
				"title_en": collection.title_en,
				"title_ar": collection.title_ar,
				"intro_en": collection.intro_en,
				"intro_ar": collection.intro_ar,
				"cover_image": full_url(collection.cover_image) if collection.cover_image else None,
				"cover_image_alt_en": collection.cover_image_alt_en,
				"cover_image_alt_ar": collection.cover_image_alt_ar,
				"accent_color": collection.accent_color,
				"cta_text_en": collection.cta_text_en,
				"cta_text_ar": collection.cta_text_ar,
				"cta_url": collection.cta_url,
				"sections": serialized_sections,
				"hotspots_enabled": bool(settings.get("lookbook_hotspots_enabled", 1)),
			})
	except Exception:
		pass

	popups_data = []
	try:
		popups = frappe.get_all(
			"Webshop Popup",
			filters={"enabled": 1},
			fields=["*"]
		)
		popups_data = [
			{
				"title_en": p.title_en,
				"title_ar": p.title_ar,
				"content_en": p.content_en,
				"content_ar": p.content_ar,
				"image": full_url(p.image) if p.image else None,
				"popup_type": p.popup_type,
				"link_url": p.link_url,
				"button_text_en": p.button_text_en,
				"button_text_ar": p.button_text_ar,
				"delay_seconds": p.delay_seconds,
				"show_once_per_session": p.show_once_per_session
			} for p in popups
		]
	except Exception:
		pass

	seo_data = {}
	try:
		seo_settings = frappe.get_single("Webshop SEO Settings")
		seo_data = {
			"meta_title_en": seo_settings.meta_title_en,
			"meta_title_ar": seo_settings.meta_title_ar,
			"meta_description_en": seo_settings.meta_description_en,
			"meta_description_ar": seo_settings.meta_description_ar,
			"og_title_en": seo_settings.og_title_en,
			"og_title_ar": seo_settings.og_title_ar,
			"og_description_en": seo_settings.og_description_en,
			"og_description_ar": seo_settings.og_description_ar,
			"og_image": full_url(seo_settings.og_image) if seo_settings.og_image else None,
			"canonical_url": seo_settings.canonical_url,
			"robots_txt": seo_settings.robots_txt,
			"sitemap_enabled": seo_settings.sitemap_enabled,
			"structured_data": seo_settings.structured_data,
			"redirects": [
				{
					"source_url": r.source_url,
					"target_url": r.target_url,
					"redirect_type": r.redirect_type
				} for r in seo_settings.redirects
			]
		}
	except Exception:
		pass

	faqs = []
	try:
		faqs = frappe.get_all(
			"Webshop FAQ",
			filters={"is_active": 1},
			fields=["question_en", "question_ar", "answer_en", "answer_ar", "sort_order"],
			order_by="sort_order asc"
		)
	except Exception:
		pass

	response = {
		"site_name": settings.site_name,
		"contact_us_text_en": settings.get("contact_us_text_en"),
		"contact_us_text_ar": settings.get("contact_us_text_ar"),
		"track_order_text_en": settings.get("track_order_text_en"),
		"track_order_text_ar": settings.get("track_order_text_ar"),
		"open_menu_text_en": settings.get("open_menu_text_en"),
		"open_menu_text_ar": settings.get("open_menu_text_ar"),
		"home_text_en": settings.get("home_text_en"),
		"home_text_ar": settings.get("home_text_ar"),
		"all_products_text_en": settings.get("all_products_text_en"),
		"all_products_text_ar": settings.get("all_products_text_ar"),
		"why_us_text_en": settings.get("why_us_text_en"),
		"why_us_text_ar": settings.get("why_us_text_ar"),
		"search_button_text_en": settings.get("search_button_text_en"),
		"search_button_text_ar": settings.get("search_button_text_ar"),
		"category_label_short_en": settings.get("category_label_short_en"),
		"category_label_short_ar": settings.get("category_label_short_ar"),
		"product_label_short_en": settings.get("product_label_short_en"),
		"product_label_short_ar": settings.get("product_label_short_ar"),
		"enable_quick_view": settings.get("enable_quick_view", 1),
		"enable_faceted_search": settings.get("enable_faceted_search", 1),
		"show_category_sidebar": settings.show_category_sidebar,
		"show_price_filter": settings.show_price_filter,
		"show_brand_filter": settings.show_brand_filter,
		"sidebar_width": settings.sidebar_width or 220,
		"tagline_en": settings.tagline_en,
		"tagline_ar": settings.tagline_ar,
		"hero_quote_en": settings.hero_quote_en,
		"hero_quote_ar": settings.hero_quote_ar,
		"about_text_en": settings.about_text_en,
		"about_text_ar": settings.about_text_ar,
		"footer_text_en": settings.footer_text_en,
		"footer_text_ar": settings.footer_text_ar,
		"phone_number": settings.phone_number,
		"email_address": settings.email_address,
		"contact_address_en": settings.contact_address_en,
		"contact_address_ar": settings.contact_address_ar,
		"show_top_bar": settings.show_top_bar,
		"top_bar_message_en": settings.top_bar_message_en,
		"top_bar_message_ar": settings.top_bar_message_ar,
		"seo_meta_description_en": settings.seo_meta_description_en,
		"seo_meta_description_ar": settings.seo_meta_description_ar,
		"seo_og_image": full_url(settings.seo_og_image) if settings.seo_og_image else None,
		            "seo_keywords": settings.seo_keywords,
            "enable_analytics_tracking": bool(settings.get("enable_analytics_tracking", 0)),
            "ga4_measurement_id": settings.get("ga4_measurement_id") if settings.get("enable_analytics_tracking", 0) else None,
            "facebook_pixel_id": settings.get("facebook_pixel_id") if settings.get("enable_analytics_tracking", 0) else None,
            "tiktok_pixel_id": settings.get("tiktok_pixel_id") if settings.get("enable_analytics_tracking", 0) else None,
            "analytics_events_enabled": bool(settings.get("analytics_events_enabled", 1)) and bool(settings.get("enable_analytics_tracking", 0)),
            "show_whatsapp_button": settings.show_whatsapp_button,

		"whatsapp_number": settings.whatsapp_number,
		"whatsapp_message": settings.whatsapp_message,
		"show_back_to_top": settings.show_back_to_top,
		"nav_links": nav_links,
		"social_links": social_links,
		"banners": banners,
		"featured_categories": featured_categories,
		"testimonials": testimonials,
		"trust_badges": trust_badges,
		"landing_sections": landing_sections,
		"theme": get_theme(),
		"footer_settings": footer_settings_data,
		"announcement": announcement_data,
		"product_settings": product_settings_data,
		"recommendations_title_en": settings.get("recommendations_title_en") or "Picked for you",
		"recommendations_title_ar": settings.get("recommendations_title_ar") or "مختارات لك",
		"recommendations_enabled": settings.get("recommendations_enabled", 1),
		"popups": popups_data,
		"seo": seo_data,
		"faqs": faqs,
		"enable_user_registration": settings.get("enable_user_registration", 1),
		"enable_wishlist": settings.get("enable_wishlist", 1),
		"mega_menu_enabled": settings.get("mega_menu_enabled", 1),
		"mega_menu_max_categories": settings.get("mega_menu_max_categories", 12),
		"mega_menu_title_en": settings.get("mega_menu_title_en") or "Browse categories",
		"mega_menu_title_ar": settings.get("mega_menu_title_ar") or "تصفح الأقسام",
		"mega_menu_featured_image": full_url(settings.get("mega_menu_featured_image")) if settings.get("mega_menu_featured_image") else None,
		"mega_menu_featured_title_en": settings.get("mega_menu_featured_title_en"),
		"mega_menu_featured_title_ar": settings.get("mega_menu_featured_title_ar"),
		"mega_menu_featured_url": settings.get("mega_menu_featured_url"),
					"stories": stories_data,
			"editorial_collections": editorial_collections,

		"stories_enabled": settings.get("stories_enabled", 1),
		"stories_title_en": settings.get("stories_title_en") or "The edit, in moments",
		"stories_title_ar": settings.get("stories_title_ar") or "مختارات في لحظات",
		"mobile_quick_actions_enabled": settings.get("mobile_quick_actions_enabled", 1),
		"complete_the_look_enabled": settings.get("complete_the_look_enabled", 1),
		"complete_the_look_title_en": settings.get("complete_the_look_title_en") or "Complete the look",
					"complete_the_look_title_ar": settings.get("complete_the_look_title_ar") or "أكمل الإطلالة",
			"experience_settings": {
				"sensory_ui_enabled": settings.get("sensory_ui_enabled", 1),
				"cinematic_transitions_enabled": settings.get("cinematic_transitions_enabled", 1),
				"lookbook_hotspots_enabled": settings.get("lookbook_hotspots_enabled", 1),
				"curated_for_you_enabled": settings.get("curated_for_you_enabled", 1),
				"curated_for_you_title_en": settings.get("curated_for_you_title_en") or "Curated for you",
				"curated_for_you_title_ar": settings.get("curated_for_you_title_ar") or "مختارات لك",
				"express_checkout_enabled": settings.get("express_checkout_enabled", 1),
				"express_checkout_title_en": settings.get("express_checkout_title_en") or "A faster way to checkout",
				"express_checkout_title_ar": settings.get("express_checkout_title_ar") or "طريقة أسرع لإتمام الطلب",
				"express_checkout_subtitle_en": settings.get("express_checkout_subtitle_en") or "Use your saved details and continue in one fluid step.",
				"express_checkout_subtitle_ar": settings.get("express_checkout_subtitle_ar") or "استخدم بياناتك المحفوظة وأكمل طلبك بخطوة سلسة.",
				"express_checkout_cta_en": settings.get("express_checkout_cta_en") or "Checkout faster",
				"express_checkout_cta_ar": settings.get("express_checkout_cta_ar") or "إتمام أسرع",
				"gifting_enabled": settings.get("gifting_enabled", 1),
				"gifting_title_en": settings.get("gifting_title_en") or "Make it a gift",
				"gifting_title_ar": settings.get("gifting_title_ar") or "اجعلها هدية",
				"gifting_message_placeholder_en": settings.get("gifting_message_placeholder_en") or "Add a personal note",
				"gifting_message_placeholder_ar": settings.get("gifting_message_placeholder_ar") or "أضف رسالة شخصية",
				"gifting_wrap_label_en": settings.get("gifting_wrap_label_en") or "Add gift wrapping",
				"gifting_wrap_label_ar": settings.get("gifting_wrap_label_ar") or "إضافة تغليف هدايا",
				"visual_search_enabled": settings.get("visual_search_enabled", 0),
				"visual_search_ai_enabled": settings.get("visual_search_ai_enabled", 0),
				"visual_search_title_en": settings.get("visual_search_title_en") or "Search by image",
				"visual_search_title_ar": settings.get("visual_search_title_ar") or "البحث بالصورة",
				"visual_search_hint_en": settings.get("visual_search_hint_en") or "Upload a product photo to find similar items",
				"visual_search_hint_ar": settings.get("visual_search_hint_ar") or "ارفع صورة منتج للعثور على منتجات مشابهة",
				"performance_adaptive_media_enabled": settings.get("performance_adaptive_media_enabled", 1),
				"performance_lazy_spatial_enabled": settings.get("performance_lazy_spatial_enabled", 1),
				"pickup_enabled": settings.get("pickup_enabled", 0),
				"pickup_title_en": settings.get("pickup_title_en") or "Store pickup",
				"pickup_title_ar": settings.get("pickup_title_ar") or "الاستلام من المتجر",
				"pickup_note_en": settings.get("pickup_note_en") or "Choose an available warehouse and collect your order there.",
				"pickup_note_ar": settings.get("pickup_note_ar") or "اختر مستودعاً متاحاً لاستلام طلبك منه.",
				"membership_enabled": settings.get("membership_enabled", 1),
				"membership_title_en": settings.get("membership_title_en") or "Your membership",
				"membership_title_ar": settings.get("membership_title_ar") or "عضويتك",
			},
			"ultra_settings": {
				"adaptive_palette_enabled": settings.get("adaptive_palette_enabled", 1),
				"circadian_theme_enabled": settings.get("circadian_theme_enabled", 1),
				"circadian_morning_start": settings.get("circadian_morning_start", 7),
				"circadian_evening_start": settings.get("circadian_evening_start", 18),
				"shared_transitions_enabled": settings.get("shared_transitions_enabled", 1),
				"magnetic_cursor_enabled": settings.get("magnetic_cursor_enabled", 1),
				"predictive_prefetch_enabled": settings.get("predictive_prefetch_enabled", 1),
				"palette_transition_ms": settings.get("palette_transition_ms", 520),
			},

	}
	return set_json_cache("content_elite_v4", {}, response, expires_in_sec=120)
