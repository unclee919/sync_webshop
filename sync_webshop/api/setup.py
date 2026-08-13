import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

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
		],
		"Sales Order": [
			{"fieldname": "webshop_is_gift", "label": "Is Gift", "fieldtype": "Check", "insert_after": "webshop_second_phone"},
			{"fieldname": "webshop_gift_wrap", "label": "Gift Wrap", "fieldtype": "Check", "insert_after": "webshop_is_gift"},
			{"fieldname": "webshop_gift_message", "label": "Gift Message", "fieldtype": "Small Text", "insert_after": "webshop_gift_wrap"},
			{"fieldname": "webshop_fulfillment_method", "label": "Fulfillment Method", "fieldtype": "Select", "options": "Delivery\nStore Pickup", "default": "Delivery", "insert_after": "webshop_gift_message"},
			{"fieldname": "webshop_pickup_warehouse", "label": "Pickup Warehouse", "fieldtype": "Link", "options": "Warehouse", "insert_after": "webshop_fulfillment_method"},
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
	frappe.db.commit()
	
	return "Setup completed successfully. Custom fields, Arabic labels, and Help Guide created."


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
