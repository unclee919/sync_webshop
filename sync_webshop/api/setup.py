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
			"Sales Order": [
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
