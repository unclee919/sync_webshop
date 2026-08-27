import frappe

MERGES = {
    'Webshop Dynamic Pages Settings': {
        'enabled': 'dynamic_pages_enabled',
        'about_enabled': 'dynamic_about_enabled',
        'about_show_in_nav': 'dynamic_about_show_in_nav',
        'about_label_en': 'dynamic_about_label_en',
        'about_label_ar': 'dynamic_about_label_ar',
        'policy_enabled': 'dynamic_policy_enabled',
        'policy_show_in_nav': 'dynamic_policy_show_in_nav',
        'policy_label_en': 'dynamic_policy_label_en',
        'policy_label_ar': 'dynamic_policy_label_ar',
        'articles_enabled': 'dynamic_articles_enabled',
        'articles_show_in_nav': 'dynamic_articles_show_in_nav',
        'articles_label_en': 'dynamic_articles_label_en',
        'articles_label_ar': 'dynamic_articles_label_ar',
        'qa_enabled': 'dynamic_qa_enabled',
        'qa_show_in_nav': 'dynamic_qa_show_in_nav',
        'qa_label_en': 'dynamic_qa_label_en',
        'qa_label_ar': 'dynamic_qa_label_ar',
        'seo_description_en': 'dynamic_seo_description_en',
        'seo_description_ar': 'dynamic_seo_description_ar',
    },
    'Webshop Landing Page Builder': {
        'enabled': 'landing_builder_enabled',
        'hero_heading_en': 'landing_hero_heading_en',
        'hero_heading_ar': 'landing_hero_heading_ar',
        'featured_grid_title_en': 'landing_featured_grid_title_en',
        'featured_grid_title_ar': 'landing_featured_grid_title_ar',
    },
    'Webshop Help Guide': {'help_content': 'help_content'},
}


def _raw(doctype, field):
    return frappe.db.sql('SELECT value FROM `tabSingles` WHERE doctype=%s AND field=%s LIMIT 1', (doctype, field))


def _copy(source, target, mapping):
    copied = 0
    sm = frappe.get_meta(source)
    tm = frappe.get_meta(target)
    for source_field, target_field in mapping.items():
        if not sm.has_field(source_field) or not tm.has_field(target_field):
            continue
        value = _raw(source, source_field)
        if value and not _raw(target, target_field):
            frappe.db.set_single_value(target, target_field, value[0][0], update_modified=False)
            copied += 1
    return copied


def execute():
    copied = 0
    deleted = 0
    for source, mapping in MERGES.items():
        if frappe.db.exists('DocType', source) and frappe.db.exists('DocType', 'Webshop Content Settings'):
            copied += _copy(source, 'Webshop Content Settings', mapping)
    for source in MERGES:
        if frappe.db.exists('DocType', source):
            frappe.delete_doc('DocType', source, force=True, ignore_permissions=True)
            deleted += 1
    frappe.db.commit()
    frappe.clear_cache()
    return {'copied_fields': copied, 'deleted_doctypes': deleted}
