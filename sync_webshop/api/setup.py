import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from sync_webshop.api.utils import clear_webshop_cache

@frappe.whitelist()
def run_setup():
	"""
	Creates custom fields required for Batch 2.
	This should be run once after deploying the code.
	"""
	# Check if user is System Manager
	if frappe.session.user == "Guest":
		frappe.throw("Guest users cannot run setup.")
		
	# In a real scenario, we might want to restrict this further
	# but for this task, we'll allow it if called correctly.
	
	custom_fields = {
		"Item": [
			{"fieldname": "webshop_stage_image", "label": "Webshop Stage Image", "fieldtype": "Attach Image", "insert_after": "image"},
			{"fieldname": "webshop_stage_image_2", "label": "Webshop Alternate Stage Image", "fieldtype": "Attach Image", "insert_after": "webshop_stage_image"},
			{"fieldname": "webshop_stage_label_en", "label": "Stage Label (English)", "fieldtype": "Data", "insert_after": "webshop_stage_image_2"},
			{"fieldname": "webshop_stage_label_ar", "label": "Stage Label (Arabic)", "fieldtype": "Data", "insert_after": "webshop_stage_label_en"},
			{"fieldname": "webshop_curated_tags", "label": "Curated For You Tags", "fieldtype": "Data", "insert_after": "webshop_stage_label_ar", "description": "Comma-separated business-neutral tags such as seasonal, staff picks, or everyday."},
			{"fieldname": "video_url", "label": "Product Hover Video URL", "fieldtype": "Data", "insert_after": "webshop_curated_tags"},
			{"fieldname": "webshop_search_keywords", "label": "Visual Search Keywords", "fieldtype": "Data", "insert_after": "video_url", "description": "Comma-separated business-neutral visual descriptors."},
			{"fieldname": "webshop_style_tags", "label": "Style Profile Tags", "fieldtype": "Data", "insert_after": "webshop_search_keywords", "description": "Comma-separated style tags used only for local catalog personalization."},
			{"fieldname": "webshop_material_variants", "label": "Material Variants", "fieldtype": "Table", "options": "Webshop Material Variant", "insert_after": "webshop_style_tags"},
			{"fieldname": "webshop_quote_enabled", "label": "Request Quote Enabled", "fieldtype": "Check", "insert_after": "webshop_material_variants"},
			{"fieldname": "webshop_quote_min_qty", "label": "Request Quote Minimum Quantity", "fieldtype": "Float", "insert_after": "webshop_quote_enabled"},
			{"fieldname": "webshop_quote_note_en", "label": "Quote Note (English)", "fieldtype": "Small Text", "insert_after": "webshop_quote_min_qty"},
			{"fieldname": "webshop_quote_note_ar", "label": "Quote Note (Arabic)", "fieldtype": "Small Text", "insert_after": "webshop_quote_note_en"},
			],
			"Item Group": [
				{"fieldname": "webshop_label_en", "label": "Storefront Label (English)", "fieldtype": "Data", "insert_after": "item_group_name"},
				{"fieldname": "webshop_label_ar", "label": "Storefront Label (Arabic)", "fieldtype": "Data", "insert_after": "webshop_label_en"},
				{"fieldname": "webshop_description_en", "label": "Storefront Description (English)", "fieldtype": "Small Text", "insert_after": "webshop_label_ar"},
				{"fieldname": "webshop_description_ar", "label": "Storefront Description (Arabic)", "fieldtype": "Small Text", "insert_after": "webshop_description_en"},
			],
			"Sales Order": [
			{"fieldname": "webshop_is_gift", "label": "Is Gift", "fieldtype": "Check", "insert_after": "webshop_second_phone"},
			{"fieldname": "webshop_gift_wrap", "label": "Gift Wrap", "fieldtype": "Check", "insert_after": "webshop_is_gift"},
			{"fieldname": "webshop_gift_message", "label": "Gift Message", "fieldtype": "Small Text", "insert_after": "webshop_gift_wrap"},
			{"fieldname": "webshop_fulfillment_method", "label": "Fulfillment Method", "fieldtype": "Select", "options": "Delivery\nStore Pickup", "default": "Delivery", "insert_after": "webshop_gift_message"},
			{"fieldname": "webshop_pickup_warehouse", "label": "Pickup Warehouse", "fieldtype": "Link", "options": "Warehouse", "insert_after": "webshop_fulfillment_method"},
			{"fieldname": "webshop_quote_request", "label": "Quote Request", "fieldtype": "Check", "insert_after": "webshop_pickup_warehouse"},
			{"fieldname": "webshop_quotation", "label": "Quotation", "fieldtype": "Link", "options": "Quotation", "insert_after": "webshop_quote_request"},
			{"fieldname": "webshop_tracking_latitude", "label": "Tracking Latitude", "fieldtype": "Float", "insert_after": "webshop_quotation"},
			{"fieldname": "webshop_tracking_longitude", "label": "Tracking Longitude", "fieldtype": "Float", "insert_after": "webshop_tracking_latitude"},
			{"fieldname": "webshop_courier_status", "label": "Courier Status", "fieldtype": "Data", "insert_after": "webshop_tracking_longitude"},
			{"fieldname": "webshop_courier_zone", "label": "Courier Zone", "fieldtype": "Data", "insert_after": "webshop_courier_status"},
			{"fieldname": "webshop_stops_remaining", "label": "Stops Remaining", "fieldtype": "Int", "insert_after": "webshop_courier_zone"},
			{"fieldname": "webshop_courier_tracking_url", "label": "Courier Tracking URL", "fieldtype": "Data", "insert_after": "webshop_stops_remaining"},
			{
				"fieldname": "tracking_number", 
				"label": "رقم التتبع (Tracking Number)", 
				"fieldtype": "Data", 
				"insert_after": "delivery_date"
			},
			{
				"fieldname": "webshop_payment_method", 
				"label": "طريقة الدفع (Payment Method)", 
				"fieldtype": "Data", 
				"insert_after": "payment_terms_template"
			},
			{
				"fieldname": "webshop_payment_status", 
				"label": "حالة الدفع (Payment Status)", 
				"fieldtype": "Data", 
				"insert_after": "webshop_payment_method"
			},
						{
				"fieldname": "stripe_payment_intent", 
				"label": "معرف دفع سترايب (Stripe Intent)", 
				"fieldtype": "Data", 
				"insert_after": "webshop_payment_status"
				},
			{
				"fieldname": "webshop_coupon_code",
				"label": "Coupon Code",
				"fieldtype": "Data",
				"insert_after": "stripe_payment_intent"
				},
			{
				"fieldname": "webshop_coupon_discount",
				"label": "Coupon Discount",
				"fieldtype": "Currency",
				"insert_after": "webshop_coupon_code"
				},
			{
				"fieldname": "webshop_governorate",
				"label": "Governorate",
				"fieldtype": "Link",
				"options": "Territory",
				"insert_after": "webshop_coupon_discount"
				},
			{
				"fieldname": "webshop_city",
				"label": "City",
				"fieldtype": "Link",
				"options": "Territory",
				"insert_after": "webshop_governorate"
				},
			{
				"fieldname": "webshop_location",
				"label": "Optional Location",
				"fieldtype": "Small Text",
				"insert_after": "webshop_city"
				},
			{
				"fieldname": "webshop_second_phone",
				"label": "Second Phone Number",
				"fieldtype": "Data",
				"insert_after": "webshop_location"
				},
		],
		"Quotation": [
			{"fieldname": "webshop_quote_request", "label": "Quote Request", "fieldtype": "Check"},
			{"fieldname": "webshop_quote_source", "label": "Quote Source", "fieldtype": "Data"},
		],
		"Delivery Note": [
			{
				"fieldname": "tracking_number", 
				"label": "رقم التتبع (Tracking Number)", 
				"fieldtype": "Data", 
				"insert_after": "delivery_date"
			},
		]
	}
	
	create_custom_fields(custom_fields)
	
	# Create Landing Sections if none exist
	if not frappe.db.count("Webshop Landing Section"):
		featured = frappe.get_doc({
			"doctype": "Webshop Landing Section",
			"section_title_en": "Featured Products",
			"section_title_ar": "المنتجات المميزة",
			"enabled": 1,
			"sort_order": 1,
			"items": []
		})
		featured.insert(ignore_permissions=True)
		
		offers = frappe.get_doc({
			"doctype": "Webshop Landing Section",
			"section_title_en": "Best Offers",
			"section_title_ar": "أفضل العروض",
			"enabled": 1,
			"sort_order": 2,
			"items": []
		})
		offers.insert(ignore_permissions=True)
		
	# Create a default Webshop Payment Settings record if it doesn't exist
	if not frappe.db.exists("Webshop Payment Settings", "Webshop Payment Settings"):
		doc = frappe.get_doc({
			"doctype": "Webshop Payment Settings",
			"cod_enabled": 1,
			"cod_label_en": "Cash on Delivery",
			"cod_label_ar": "الدفع عند الاستلام"
		})
		doc.insert(ignore_permissions=True)
		
	# Create a default Webshop Shipping Rule if none exists
	if not frappe.db.count("Webshop Shipping Rule"):
		doc = frappe.get_doc({
			"doctype": "Webshop Shipping Rule",
			"rule_name": "Standard Shipping",
			"enabled": 1,
			"shipping_cost": 5.0,
			"free_shipping_threshold": 50.0
		})
		doc.insert(ignore_permissions=True)
		
	# Create Help Guide content
	if not frappe.db.exists("Webshop Help Guide", "Webshop Help Guide"):
		doc = frappe.get_doc({"doctype": "Webshop Help Guide"})
		doc.insert(ignore_permissions=True)
	
	help_doc = frappe.get_single("Webshop Help Guide")
	help_doc.help_content = """
		<div dir="rtl" style="padding: 20px; font-family: Cairo, sans-serif;">
			<h2 style="color: #21504C; border-bottom: 2px solid #84B082; padding-bottom: 10px;">دليل أنواع الحقول في المتجر</h2>
			<p>هذا الجدول يوضح أنواع الحقول التي ستواجهها عند تعديل إعدادات المتجر ومعنى كل منها بالعربية:</p>
			<table class="table table-bordered" style="width: 100%; margin-top: 20px;">
				<thead>
					<tr style="background-color: #f8f9fa;">
						<th>نوع الحقل (Field Type)</th>
						<th>الترجمة بالعربية</th>
						<th>الاستخدام الشائع</th>
					</tr>
				</thead>
				<tbody>
					<tr><td><b>Data</b></td><td>بيانات / نص قصير</td><td>الأسماء، الأرقام، المفاتيح النصية.</td></tr>
					<tr><td><b>Int</b></td><td>رقم صحيح</td><td>الأبعاد (عرض/ارتفاع)، المسافات، الترتيب.</td></tr>
					<tr><td><b>Check</b></td><td>خيار تفعيل</td><td>تفعيل أو تعطيل ميزة معينة (صح/خطأ).</td></tr>
					<tr><td><b>Select</b></td><td>قائمة اختيار</td><td>اختيار واحد من خيارات محددة مسبقاً.</td></tr>
					<tr><td><b>Color</b></td><td>منتقي الألوان</td><td>تغيير ألوان الخلفية، النصوص، أو الأزرار.</td></tr>
					<tr><td><b>Attach Image</b></td><td>إرفاق صورة</td><td>رفع الشعار (Logo) أو صور الخلفيات.</td></tr>
					<tr><td><b>Currency</b></td><td>عملة</td><td>الأسعار، تكاليف الشحن، الخصومات.</td></tr>
					<tr><td><b>Date</b></td><td>تاريخ</td><td>تحديد أيام محددة للتوصيل أو العروض.</td></tr>
					<tr><td><b>Link</b></td><td>رابط سجل</td><td>ربط الحقل ببيانات أخرى (مثل اختيار منتج).</td></tr>
					<tr><td><b>Table</b></td><td>جدول</td><td>إضافة قائمة من العناصر (مثل قائمة منتجات).</td></tr>
					<tr><td><b>Section Break</b></td><td>فاصل قسم</td><td>تنظيم الإعدادات تحت عنوان جانبي.</td></tr>
				</tbody>
			</table>
			<div style="margin-top: 30px; padding: 15px; background-color: #e8f5e9; border-radius: 8px;">
				<h4 style="color: #2e7d32;">نصيحة للمدير:</h4>
				<p>دائماً تأكد من الضغط على زر <b>Save</b> بعد أي تعديل في الإعدادات لتظهر النتائج فوراً على المتجر.</p>
			</div>
		</div>
	"""
	help_doc.save(ignore_permissions=True)

	# Create the two app roles used to separate configuration users from managers.
	for role_name, desk_access in (("Sync Webshop User", 1), ("Sync Webshop Manager", 1)):
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": desk_access}).insert(ignore_permissions=True)

	# Seed safe defaults for every new Elite settings Single. Secrets remain empty and are entered only in Desk.
	elite_defaults = {
		"Webshop AI Vision Settings": {"visual_search_enabled": 1, "auto_tagging_enabled": 1, "ai_model_name": "gpt-5-mini", "confidence_threshold": 0.85, "nlp_enabled": 1, "welcome_message_en": "Hello! I am your AI shopping assistant. How can I help you discover the right product?", "welcome_message_ar": "مرحباً! أنا مساعد التسوق الذكي. كيف يمكنني مساعدتك في اكتشاف المنتج المناسب؟"},
		"Webshop Marketplace Settings": {"amazon_sa_enabled": 0, "noon_enabled": 0, "sync_interval_minutes": 30},
		"Webshop Regional Payment Settings": {"regional_live_mode": 0, "tabby_enabled": 1, "tamara_enabled": 1, "mada_enabled": 1, "apple_pay_enabled": 1},
		"Webshop PWA Settings": {"pwa_enabled": 1, "app_short_name": "Sync Webshop", "theme_color": "#173F3A", "offline_message_en": "You are currently offline. Browsing cached catalog.", "offline_message_ar": "أنت غير متصل بالإنترنت حالياً. يتم تصفح الكتالوج المحفوظ."},
	}
	for doctype, values in elite_defaults.items():
		if frappe.db.exists("DocType", doctype):
			doc = frappe.get_single(doctype)
			changed = False
			for fieldname, value in values.items():
				if not doc.get(fieldname):
					doc.set(fieldname, value)
					changed = True
			if changed:
				doc.save(ignore_permissions=True)

	if frappe.db.exists("DocType", "Webshop Storefront Profile") and not frappe.db.exists("Webshop Storefront Profile", {"store_key": "sync-coffee-house"}):
		frappe.get_doc({"doctype": "Webshop Storefront Profile", "name": "Sync Coffee House", "profile_name": "Sync Coffee House", "store_key": "sync-coffee-house", "enabled": 1, "is_default": 1, "label_en": "Sync Coffee House", "label_ar": "مقهى سينك", "accent_color": "#C5A059"}).insert(ignore_permissions=True)

	frappe.db.commit()
	clear_webshop_cache()
	return "Setup completed successfully. Custom fields, Arabic labels, Elite settings, roles, and Help Guide created."


@frappe.whitelist()
def seed_phase3_demo():
    """Seed safe, business-neutral sample data for Elite Phase 3 verification."""
    if frappe.session.user == "Guest":
        frappe.throw("Guest users cannot seed demo settings.")
    if frappe.db.exists("DocType", "Webshop Content Settings"):
        settings = frappe.get_single("Webshop Content Settings")
        values = {
            "visual_search_enabled": 1,
            "visual_search_ai_enabled": 0,
            "performance_adaptive_media_enabled": 1,
            "performance_lazy_spatial_enabled": 1,
            "pickup_enabled": 1,
            "membership_enabled": 1,
            "visual_search_title_en": "Search by image",
            "visual_search_title_ar": "البحث بالصورة",
            "pickup_title_en": "Store pickup",
            "pickup_title_ar": "الاستلام من المتجر",
            "membership_title_en": "Your membership",
            "membership_title_ar": "عضويتك",
            "presence_material_studio_enabled": 1,
            "style_quiz_enabled": 1,
            "quote_requests_enabled": 1,
            "quote_request_title_en": "Request a tailored quote",
            "quote_request_title_ar": "اطلب عرض سعر مخصص",
            "live_tracking_map_enabled": 1,
            "social_proof_enabled": 1,
            "social_proof_viewer_enabled": 1,
        }
        for fieldname, value in values.items():
            if settings.meta.has_field(fieldname):
                settings.set(fieldname, value)
        settings.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Paymob Settings"):
        paymob = frappe.get_single("Webshop Paymob Settings")
        for fieldname, value in {
            "online_payment_enabled": 1,
            "online_label_en": "Online payment",
            "online_label_ar": "الدفع الإلكتروني",
            "online_note_en": "Pay securely with the methods enabled in Paymob.",
            "online_note_ar": "ادفع بأمان باستخدام طرق الدفع المفعلة في Paymob.",
        }.items():
            if paymob.meta.has_field(fieldname):
                paymob.set(fieldname, value)
        paymob.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Membership Tier"):
        tiers = [
            {"tier_name": "Starter", "tier_code": "STARTER", "minimum_spend": 0, "discount_percent": 0, "badge_color": "#9CA3AF", "perks_en": "Welcome benefits", "perks_ar": "مزايا الترحيب", "sort_order": 30},
            {"tier_name": "Preferred", "tier_code": "PREFERRED", "minimum_spend": 500, "discount_percent": 5, "badge_color": "#C8A96B", "perks_en": "Priority support and member offers", "perks_ar": "دعم أولوية وعروض للأعضاء", "sort_order": 20},
            {"tier_name": "Circle", "tier_code": "CIRCLE", "minimum_spend": 1500, "discount_percent": 10, "badge_color": "#0F766E", "perks_en": "Early access and complimentary delivery", "perks_ar": "وصول مبكر وتوصيل مجاني", "sort_order": 10},
        ]
        for tier in tiers:
            existing = frappe.db.get_value("Webshop Membership Tier", {"tier_code": tier["tier_code"]}, "name")
            doc = frappe.get_doc("Webshop Membership Tier", existing) if existing else frappe.new_doc("Webshop Membership Tier")
            doc.update(tier)
            doc.enabled = 1
            doc.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Tracking Settings"):
        tracking = frappe.get_single("Webshop Tracking Settings")
        tracking.update({"enabled": 1, "map_enabled": 1, "courier_name": "Configured courier", "tracking_url_template": "", "title_en": "Your delivery, in view", "title_ar": "شاهد مسار توصيلك"})
        tracking.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Style Quiz Question"):
        questions = [
            {"question_key": "mood", "question_en": "Which mood feels most like your space?", "question_ar": "أي أجواء تشبه مساحتك أكثر؟", "options_json": '[{"label_en":"Quiet and natural","label_ar":"هادئة وطبيعية","tag":"natural"},{"label_en":"Warm and expressive","label_ar":"دافئة ومعبرة","tag":"warm"},{"label_en":"Clean and modern","label_ar":"نظيفة وعصرية","tag":"modern"}]', "sort_order": 10},
            {"question_key": "pace", "question_en": "What do you value most?", "question_ar": "ما الذي تقدره أكثر؟", "options_json": '[{"label_en":"Daily ease","label_ar":"سهولة يومية","tag":"everyday"},{"label_en":"Craft and detail","label_ar":"الحرفة والتفاصيل","tag":"crafted"},{"label_en":"A bold point of view","label_ar":"رؤية جريئة","tag":"statement"}]', "sort_order": 20},
        ]
        for row in questions:
            existing = frappe.db.get_value("Webshop Style Quiz Question", {"question_key": row["question_key"]}, "name")
            doc = frappe.get_doc("Webshop Style Quiz Question", existing) if existing else frappe.new_doc("Webshop Style Quiz Question")
            doc.update(row); doc.enabled = 1; doc.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Social Proof Event"):
        events = [
            {"event_type": "Purchase", "city_en": "Riyadh", "city_ar": "الرياض", "label_en": "A considered everyday essential", "label_ar": "اختيار يومي بعناية", "minutes_ago": 8, "viewer_count": 0, "sort_order": 10},
            {"event_type": "Viewer Pulse", "city_en": "", "city_ar": "", "label_en": "A few customers are viewing this edit", "label_ar": "بعض العملاء يشاهدون هذه المجموعة", "minutes_ago": 0, "viewer_count": 4, "sort_order": 20},
        ]
        for row in events:
            existing = frappe.db.get_value("Webshop Social Proof Event", {"event_type": row["event_type"], "sort_order": row["sort_order"]}, "name")
            doc = frappe.get_doc("Webshop Social Proof Event", existing) if existing else frappe.new_doc("Webshop Social Proof Event")
            doc.update(row); doc.enabled = 1; doc.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Item"):
        sample = frappe.db.get_value("Item", {"item_code": "SYNC-KIT-001", "disabled": 0}, "name") or frappe.db.get_value("Item", {"disabled": 0}, "name")
        if sample:
            item = frappe.get_doc("Item", sample)
            if item.meta.has_field("webshop_style_tags"):
                item.webshop_style_tags = "everyday, natural, crafted"
            if item.meta.has_field("webshop_quote_enabled"):
                item.webshop_quote_enabled = 1
            if item.meta.has_field("webshop_quote_min_qty"):
                item.webshop_quote_min_qty = 10
            if item.meta.has_field("webshop_quote_note_en"):
                item.webshop_quote_note_en = "For teams, projects, and considered spaces, request a tailored proposal."
            if item.meta.has_field("webshop_quote_note_ar"):
                item.webshop_quote_note_ar = "للفرق والمشاريع والمساحات المميزة، اطلب عرضاً مخصصاً."
            if item.meta.has_field("webshop_material_variants") and not item.get("webshop_material_variants"):
                item.append("webshop_material_variants", {"material_name": "Natural oak", "material_name_ar": "بلوط طبيعي", "swatch_color": "#C8A96B", "enabled": 1, "sort_order": 10})
                item.append("webshop_material_variants", {"material_name": "Charcoal", "material_name_ar": "فحمي", "swatch_color": "#334155", "enabled": 1, "sort_order": 20})
            item.save(ignore_permissions=True)

    columns = set(frappe.db.get_table_columns("Item")) if frappe.db.exists("DocType", "Item") else set()
    if "webshop_search_keywords" in columns:
        items = frappe.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name", "item_group", "webshop_search_keywords", "webshop_curated_tags"], limit_page_length=20, order_by="modified desc")
        for row in items:
            item = frappe.get_doc("Item", row.name)
            if not item.webshop_search_keywords:
                item.webshop_search_keywords = ", ".join(filter(None, [item.item_name, item.item_group, item.webshop_curated_tags or "everyday essentials"]))
            if not item.webshop_curated_tags:
                item.webshop_curated_tags = "everyday, staff picks"
            item.save(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()
    return {"ok": True, "message": "Elite Phase 3 demo settings and sample data seeded safely."}


@frappe.whitelist()
def seed_coffee_shop_demo():
    """Seed a reversible, business-neutral Coffee Shop profile for multi-business QA."""
    if frappe.session.user == "Guest":
        frappe.throw("Guest users cannot seed demo settings.")

    settings = frappe.get_single("Webshop Content Settings")
    profile = {
        "business_vertical": "Coffee Shop",
        "business_vertical_label_en": "Coffee & brew",
        "business_vertical_label_ar": "القهوة وأدوات التحضير",
        "business_intro_en": "Small-batch coffee, considered brewing tools, and a calmer daily ritual.",
        "business_intro_ar": "قهوة محمصة بعناية وأدوات تحضير مختارة لطقس يومي أكثر هدوءاً.",
        "catalog_unit_label_en": "item",
        "catalog_unit_label_ar": "قطعة",
        "site_name": "Sync Coffee House",
        "site_name_en": "Sync Coffee House",
        "site_name_ar": "بيت قهوة سينك",
        "tagline_en": "Small-batch coffee for better daily rituals.",
        "tagline_ar": "قهوة محمصة بعناية لطقوس يومية أجمل.",
        "hero_quote_en": "Brew something worth slowing down for.",
        "hero_quote_ar": "حضّر لحظتك على مهل.",
        "about_text_en": "A Desk-configured coffee shop demo with beans, brewing tools, and considered café details.",
        "about_text_ar": "عرض تجريبي لمقهى يتم التحكم به من لوحة Desk ويضم البن وأدوات التحضير وتفاصيل المقهى.",
    }
    for fieldname, value in profile.items():
        if settings.meta.has_field(fieldname):
            settings.set(fieldname, value)
    settings.save(ignore_permissions=True)

    parent_group = frappe.db.get_value("Item Group", {"parent_item_group": ["is", "not set"], "is_group": 1}, "name") or frappe.db.get_value("Item Group", {}, "name")
    if not parent_group:
        parent_group = "All Item Groups"
    groups = [
        ("Coffee Beans", "حبوب القهوة"),
        ("Brewing Gear", "أدوات التحضير"),
        ("Cafe Goods", "مستلزمات المقهى"),
    ]
    group_descriptions = {
        "Coffee Beans": ("Beans for espresso, filter, and slower mornings.", "حبوب للإسبريسو والترشيح ولصباحات أكثر هدوءاً."),
        "Brewing Gear": ("Considered tools for a more precise brew.", "أدوات مختارة لتحضير أكثر دقة."),
        "Cafe Goods": ("Cups and details for the café ritual.", "أكواب وتفاصيل لطقس المقهى."),
    }
    for group_name, group_ar in groups:
        existing_group = frappe.db.exists("Item Group", group_name)
        group = frappe.get_doc("Item Group", existing_group) if existing_group else frappe.new_doc("Item Group")
        group.item_group_name = group_name
        group.parent_item_group = parent_group
        group.is_group = 0
        if group.meta.has_field("show_in_website"):
            group.show_in_website = 1
        if group.meta.has_field("item_group_name_ar"):
            group.item_group_name_ar = group_ar
        if group.meta.has_field("webshop_label_en"):
            group.webshop_label_en = group_name
        if group.meta.has_field("webshop_label_ar"):
            group.webshop_label_ar = group_ar
        description_en, description_ar = group_descriptions[group_name]
        if group.meta.has_field("webshop_description_en"):
            group.webshop_description_en = description_en
        if group.meta.has_field("webshop_description_ar"):
            group.webshop_description_ar = description_ar
        group.save(ignore_permissions=True)

    items = [
        {"item_code": "COFFEE-ETHIOPIA-001", "item_name": "Ethiopia Natural Coffee Beans", "item_group": "Coffee Beans", "description": "Floral, fruit-forward beans for filter brewing and slow mornings.", "price": 68, "image": "/files/pouch733759733759.png", "style_tags": "natural, crafted, bright", "keywords": "coffee, beans, Ethiopia, filter, floral"},
        {"item_code": "COFFEE-HOUSE-001", "item_name": "Sync House Blend Beans", "item_group": "Coffee Beans", "description": "A balanced daily blend with chocolate notes and a smooth finish.", "price": 54, "image": "/files/kit2a65be.png", "style_tags": "everyday, warm, crafted", "keywords": "coffee, beans, house blend, chocolate, espresso"},
        {"item_code": "COFFEE-KETTLE-001", "item_name": "Brushed Steel Pour-Over Kettle", "item_group": "Brewing Gear", "description": "A precise gooseneck kettle for calm, controlled pour-over brewing.", "price": 249, "image": "/files/lampa1dbe8a1dbe8.png", "style_tags": "modern, crafted, statement", "keywords": "kettle, pour over, brewing, coffee gear"},
        {"item_code": "COFFEE-CUP-001", "item_name": "Stoneware Espresso Cup", "item_group": "Cafe Goods", "description": "A tactile stoneware cup for espresso, cortado, or a small daily pause.", "price": 39, "image": "/files/mug1a117f1a117f.png", "style_tags": "natural, everyday, warm", "keywords": "espresso cup, ceramic, cafe, coffee cup"},
    ]
    price_list = frappe.get_single("Webshop API Settings").default_price_list or "Standard Selling"
    for row in items:
        if frappe.db.exists("Item", row["item_code"]):
            item = frappe.get_doc("Item", row["item_code"])
        else:
            item = frappe.new_doc("Item")
            item.item_code = row["item_code"]
            item.item_name = row["item_name"]
            item.item_group = row["item_group"]
            item.stock_uom = "Nos"
            item.is_stock_item = 1
        item.description = row["description"]
        item.image = row["image"]
        for fieldname, value in {
            "webshop_style_tags": row["style_tags"],
            "webshop_curated_tags": "coffee, staff picks, everyday",
            "webshop_search_keywords": row["keywords"],
        }.items():
            if item.meta.has_field(fieldname):
                item.set(fieldname, value)
        item.save(ignore_permissions=True)
        price_filters = {"item_code": item.item_code, "price_list": price_list, "selling": 1}
        price_name = frappe.db.get_value("Item Price", price_filters, "name")
        price_doc = frappe.get_doc("Item Price", price_name) if price_name else frappe.new_doc("Item Price")
        price_doc.item_code = item.item_code
        price_doc.price_list = price_list
        price_doc.price_list_rate = row["price"]
        price_doc.selling = 1
        price_doc.currency = "SAR"
        price_doc.save(ignore_permissions=True)

    if frappe.db.exists("DocType", "Webshop Style Quiz Question"):
        questions = [
            {"question_key": "roast", "question_en": "Which cup sounds like you today?", "question_ar": "أي فنجان يناسبك اليوم؟", "options_json": '[{"label_en":"Bright and floral","label_ar":"مشرق وزهري","tag":"bright"},{"label_en":"Balanced and chocolatey","label_ar":"متوازن وشوكولاتي","tag":"warm"},{"label_en":"Bold and concentrated","label_ar":"قوي ومركز","tag":"statement"}]', "sort_order": 10},
            {"question_key": "ritual", "question_en": "How do you like to brew?", "question_ar": "كيف تحب تحضير قهوتك؟", "options_json": '[{"label_en":"Slow pour-over","label_ar":"ترشيح بطيء","tag":"crafted"},{"label_en":"Quick espresso","label_ar":"إسبريسو سريع","tag":"everyday"},{"label_en":"A shared café moment","label_ar":"لحظة مقهى مشتركة","tag":"warm"}]', "sort_order": 20},
        ]
        for row in questions:
            existing = frappe.db.get_value("Webshop Style Quiz Question", {"question_key": row["question_key"]}, "name")
            doc = frappe.get_doc("Webshop Style Quiz Question", existing) if existing else frappe.new_doc("Webshop Style Quiz Question")
            doc.update(row)
            doc.enabled = 1
            doc.save(ignore_permissions=True)

    frappe.db.commit()
    clear_webshop_cache()
    frappe.clear_cache()
    return {"ok": True, "business_vertical": "Coffee Shop", "items": [row["item_code"] for row in items], "item_groups": [row[0] for row in groups]}
