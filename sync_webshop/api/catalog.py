import json

import frappe

from sync_webshop.api.utils import (
    full_url,
    get_json_cache,
    require_catalog_access,
    set_cors_headers,
    set_json_cache,
)


def _get_price_list():
    settings = frappe.get_single("Webshop API Settings")
    return settings.default_price_list or "Standard Selling"


def _get_prices(item_codes, price_list):
    if not item_codes:
        return {}
    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", item_codes], "price_list": price_list, "selling": 1, "price_list_rate": [">", 0]},
        fields=["item_code", "price_list_rate", "currency"],
    )
    return {row.item_code: {"rate": row.price_list_rate, "currency": row.currency} for row in rows}


def _positive_price_codes(price_list, item_codes=None):
    filters = {"price_list": price_list, "selling": 1, "price_list_rate": [">", 0]}
    if item_codes is not None:
        filters["item_code"] = ["in", item_codes]
    return frappe.get_all("Item Price", filters=filters, pluck="item_code")


def _get_item_group_scope(item_group):
    """Return the selected item group plus descendants for parent-category browsing."""
    if not item_group:
        return None
    groups = [item_group]
    try:
        descendants = frappe.db.get_descendants("Item Group", item_group) or []
        groups.extend(descendants)
    except Exception:
        # Preserve exact-group behavior if a legacy Frappe version lacks get_descendants.
        pass
    return list(dict.fromkeys(groups))


def _get_price_range(price_list, item_group=None):
    filters = {"price_list": price_list, "selling": 1}
    group_scope = _get_item_group_scope(item_group)
    if group_scope:
        codes = frappe.get_all("Item", filters={"item_group": ["in", group_scope], "disabled": 0}, pluck="item_code")
        if not codes:
            return {"min_price": 0, "max_price": 0}
        filters["item_code"] = ["in", codes]
    rows = frappe.get_all("Item Price", filters=filters, fields=["price_list_rate"])
    rates = [float(row.price_list_rate or 0) for row in rows]
    return {
        "min_price": min(rates) if rates else 0,
        "max_price": max(rates) if rates else 0,
    }


def _get_stock(item_codes):
    """Aggregate ERPNext Bin availability without exposing warehouse-level data publicly."""
    if not item_codes:
        return {}
    try:
        rows = frappe.db.sql(
            """
            SELECT item_code,
                   SUM(actual_qty) AS actual_qty,
                   SUM(projected_qty) AS projected_qty,
                   SUM(reserved_qty) AS reserved_qty
            FROM `tabBin`
            WHERE item_code IN %(item_codes)s
            GROUP BY item_code
            """,
            {"item_codes": tuple(item_codes)},
            as_dict=True,
        )
    except Exception:
        return {}
    return {
        row.item_code: {
            "actual_qty": float(row.actual_qty or 0),
            "projected_qty": float(row.projected_qty or 0),
            "reserved_qty": float(row.reserved_qty or 0),
            "available_qty": max(float(row.actual_qty or 0) - float(row.reserved_qty or 0), 0),
            "in_stock": float(row.actual_qty or 0) - float(row.reserved_qty or 0) > 0,
        }
        for row in rows
    }


def _get_variant_attributes(item_codes):
    if not item_codes:
        return {}
    try:
        rows = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": ["in", item_codes]},
            fields=["parent", "attribute", "attribute_value"],
        )
    except Exception:
        return {}
    result = {}
    for row in rows:
        result.setdefault(row.parent, []).append({
            "attribute": row.attribute,
            "value": row.attribute_value,
        })
    return result


def _get_available_attributes(item_codes):
    by_item = _get_variant_attributes(item_codes)
    facets = {}
    for rows in by_item.values():
        for row in rows:
            facets.setdefault(row["attribute"], set()).add(row["value"])
    return {key: sorted(values) for key, values in facets.items()}


def _get_item_experience(item_codes):
    """Serialize optional Desk-managed media and curation fields without exposing private ERP data."""
    if not item_codes:
        return {}
    try:
        available_columns = set(frappe.db.get_table_columns("Item"))
    except Exception:
        return {}
    wanted = [field for field in ["video_url", "webshop_stage_image", "webshop_stage_image_2", "webshop_stage_label_en", "webshop_stage_label_ar", "webshop_curated_tags", "webshop_search_keywords", "webshop_style_tags", "webshop_quote_enabled", "webshop_quote_min_qty", "webshop_quote_note_en", "webshop_quote_note_ar", "webshop_material_variants"] if field in available_columns]
    if not wanted:
        return {}
    try:
        rows = frappe.get_all("Item", filters={"item_code": ["in", item_codes]}, fields=["item_code"] + wanted)
    except Exception:
        return {}
    material_by_item = {}
    if frappe.db.exists("DocType", "Webshop Material Variant"):
        try:
            material_rows = frappe.get_all("Webshop Material Variant", filters={"parent": ["in", item_codes], "parenttype": "Item", "parentfield": "webshop_material_variants", "enabled": 1}, fields=["parent", "material_name", "material_name_ar", "swatch_color", "texture_url", "image_url", "model_url"], order_by="sort_order asc")
            for variant in material_rows:
                material_by_item.setdefault(variant.parent, []).append({"name": variant.material_name, "name_ar": variant.material_name_ar, "swatch_color": variant.swatch_color, "texture_url": full_url(variant.texture_url) if variant.texture_url else None, "image_url": full_url(variant.image_url) if variant.image_url else None, "model_url": full_url(variant.model_url) if variant.model_url else None})
        except Exception:
            material_by_item = {}
    result = {}
    for row in rows:
        stage_images = [full_url(value) for value in [row.get("webshop_stage_image"), row.get("webshop_stage_image_2")] if value]
        tags = [value.strip().lower() for value in str(row.get("webshop_curated_tags") or "").split(",") if value.strip()]
        result[row.item_code] = {
            "video_url": full_url(row.get("video_url")) if row.get("video_url") else None,
            "stage_images": stage_images,
            "stage_labels": {"en": row.get("webshop_stage_label_en"), "ar": row.get("webshop_stage_label_ar")},
            "curated_tags": tags,
            "search_keywords": [value.strip().lower() for value in str(row.get("webshop_search_keywords") or "").split(",") if value.strip()],
            "style_tags": [value.strip().lower() for value in str(row.get("webshop_style_tags") or "").split(",") if value.strip()],
            "quote_enabled": bool(row.get("webshop_quote_enabled")),
            "quote_min_qty": float(row.get("webshop_quote_min_qty") or 10),
            "quote_note_en": row.get("webshop_quote_note_en"),
            "quote_note_ar": row.get("webshop_quote_note_ar"),
            "material_variants": material_by_item.get(row.item_code, []),
        }
    return result


def _empty_catalog(page, page_size, price_list, item_group=None):
    return {
        "items": [],
        "page": page,
        "page_size": page_size,
        "total_count": 0,
        "price_list": price_list,
        "price_range": _get_price_range(price_list, item_group),
        "available_attributes": {},
    }


@frappe.whitelist(allow_guest=True)
def get_catalog(item_group=None, search=None, page=1, page_size=20, min_price=None, max_price=None, attributes=None, style_profile=None):
    set_cors_headers()
    require_catalog_access()
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    min_price = float(min_price) if min_price not in (None, "") else None
    max_price = float(max_price) if max_price not in (None, "") else None
    if style_profile and isinstance(style_profile, str):
        try:
            style_profile = json.loads(style_profile)
        except Exception:
            style_profile = None
    if attributes and isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except Exception:
            attributes = None

    cache_payload = {
        "item_group": item_group,
        "search": search,
        "page": page,
        "page_size": page_size,
        "min_price": min_price,
        "max_price": max_price,
        "attributes": attributes or {},
        "style_profile": style_profile or {},
    }
    cached = get_json_cache("catalog", cache_payload)
    if cached is not None:
        return cached

    filters = {"disabled": 0}
    group_scope = _get_item_group_scope(item_group)
    if group_scope:
        filters["item_group"] = ["in", group_scope]
    or_filters = None
    if search:
        or_filters = [
            ["item_name", "like", f"%{search}%"],
            ["item_code", "like", f"%{search}%"],
        ]

    price_list = _get_price_list()
    priced_codes = _positive_price_codes(price_list)
    if not priced_codes:
        return _empty_catalog(page, page_size, price_list, item_group)
    filters["item_code"] = ["in", priced_codes]
    if min_price is not None or max_price is not None:
        price_filters = [["price_list", "=", price_list], ["selling", "=", 1]]
        if min_price is not None:
            price_filters.append(["price_list_rate", ">=", min_price])
        if max_price is not None:
            price_filters.append(["price_list_rate", "<=", max_price])
        codes = frappe.get_all("Item Price", filters=price_filters, pluck="item_code")
        if not codes:
            return _empty_catalog(page, page_size, price_list, item_group)
        filters["item_code"] = ["in", list(set(filters["item_code"][1]).intersection(codes))]
        if not filters["item_code"][1]:
            return _empty_catalog(page, page_size, price_list, item_group)

    if attributes:
        matching_codes = None
        for attribute, values in attributes.items():
            values = values if isinstance(values, list) else [values]
            if not values:
                continue
            current = set(frappe.get_all(
                "Item Variant Attribute",
                filters={"attribute": attribute, "attribute_value": ["in", values]},
                pluck="parent",
            ))
            matching_codes = current if matching_codes is None else matching_codes.intersection(current)
        if matching_codes is not None:
            if not matching_codes:
                return _empty_catalog(page, page_size, price_list, item_group)
            if "item_code" in filters:
                matching_codes = matching_codes.intersection(set(filters["item_code"][1]))
            filters["item_code"] = ["in", list(matching_codes)]

    items = frappe.get_all(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=["item_code", "item_name", "description", "image", "item_group", "webshop_rating"],
        limit_start=(page - 1) * page_size,
        limit_page_length=page_size,
        order_by="item_name asc",
    )
    if or_filters:
        # frappe.db.count does not accept or_filters on all supported Frappe versions.
        # Use the same Frappe query builder as the item fetch to keep search contracts compatible.
        total_count = len(frappe.get_all("Item", filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    else:
        total_count = frappe.db.count("Item", filters=filters)
    codes = [row.item_code for row in items]
    prices = _get_prices(codes, price_list)
    stocks = _get_stock(codes)
    variants = _get_variant_attributes(codes)
    experiences = _get_item_experience(codes)
    results = []
    for item in items:
        price = prices.get(item.item_code) or {}
        exp = experiences.get(item.item_code, {})
        results.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "image": full_url(item.image),
            "item_group": item.item_group,
            "price": price.get("rate"),
            "currency": price.get("currency"),
            "rating": item.webshop_rating,
            "stock": stocks.get(item.item_code, {"available_qty": 0, "in_stock": False}),
            "attributes": variants.get(item.item_code, []),
            "video_url": exp.get("video_url"),
            "stage_images": exp.get("stage_images", []),
            "stage_labels": exp.get("stage_labels", {}),
            "curated_tags": exp.get("curated_tags", []),
            "search_keywords": exp.get("search_keywords", []),
            "style_tags": exp.get("style_tags", []),
            "quote_enabled": exp.get("quote_enabled", False),
            "quote_min_qty": exp.get("quote_min_qty", 10),
            "quote_note_en": exp.get("quote_note_en"),
            "quote_note_ar": exp.get("quote_note_ar"),
            "material_variants": exp.get("material_variants", []),
        })

    if style_profile and results:
        wanted_tags = {str(value).strip().lower() for value in (style_profile.get("tags") or []) if str(value).strip()}
        if wanted_tags:
            results.sort(key=lambda row: len(wanted_tags.intersection(set(row.get("style_tags") or []) | set(row.get("curated_tags") or []))), reverse=True)
    response = {
        "items": results,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "price_list": price_list,
        "price_range": _get_price_range(price_list, item_group),
        "available_attributes": _get_available_attributes(codes),
    }
    return set_json_cache("catalog", cache_payload, response, expires_in_sec=45)


@frappe.whitelist(allow_guest=True)
def get_item(item_code):
    set_cors_headers()
    require_catalog_access()
    cache_payload = {"item_code": item_code}
    cached = get_json_cache("item", cache_payload)
    if cached is not None:
        return cached
    if not frappe.db.exists("Item", {"item_code": item_code, "disabled": 0}):
        frappe.throw("Item not found", frappe.DoesNotExistError)
    item = frappe.get_doc("Item", item_code)
    price_list = _get_price_list()
    price = (_get_prices([item_code], price_list).get(item_code) or {})
    if not price or float(price.get("rate") or 0) <= 0:
        frappe.throw("This item is not currently available for purchase.", frappe.ValidationError)
    stock = _get_stock([item_code]).get(item_code, {"available_qty": 0, "in_stock": False})
    attributes = _get_variant_attributes([item_code]).get(item_code, [])
    item_experience = _get_item_experience([item_code]).get(item_code, {})
    recommendations = frappe.get_all(
        "Item",
        filters={"item_group": item.item_group, "disabled": 0, "item_code": ["!=", item_code]},
        fields=["item_code", "item_name", "image", "item_group", "webshop_rating"],
        limit_page_length=6,
        order_by="modified desc",
    )
    rec_prices = _get_prices([row.item_code for row in recommendations], price_list)
    response = {
        "item_code": item.item_code,
        "item_name": item.item_name,
        "description": item.description,
        "item_group": item.item_group,
        "image": full_url(item.image),
        "stock_uom": item.stock_uom,
        "price": price.get("rate"),
        "currency": price.get("currency"),
        "rating": item.webshop_rating,
        "price_list": price_list,
        "images": [full_url(value) for value in [item.image, item.get("image_2"), item.get("image_3"), item.get("image_4")] if value],
        "video_url": item_experience.get("video_url") or (full_url(item.get("video_url")) if item.get("video_url") else None),
        "stage_images": item_experience.get("stage_images", []),
        "stage_labels": item_experience.get("stage_labels", {}),
        "curated_tags": item_experience.get("curated_tags", []),
        "search_keywords": item_experience.get("search_keywords", []),
        "ar_ios_model_url": full_url(item.get("ar_ios_model_url")) if item.get("ar_ios_model_url") else None,
        "ar_android_model_url": full_url(item.get("ar_android_model_url")) if item.get("ar_android_model_url") else None,
        "three_d_model_url": full_url(item.get("three_d_model_url")) if item.get("three_d_model_url") else None,
        "palette_key": item.get("palette_key") or None,
        "palette_color": item.get("palette_color") or None,
        "exploded_layers": item.get("exploded_layers") or [],
        "stock": stock,
        "attributes": attributes,
        "recommendations": [
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "image": full_url(row.image),
                "item_group": row.item_group,
                "rating": row.webshop_rating,
                "price": (rec_prices.get(row.item_code) or {}).get("rate"),
                "currency": (rec_prices.get(row.item_code) or {}).get("currency"),
            }
            for row in recommendations
        ],
    }
    return set_json_cache("item", cache_payload, response, expires_in_sec=90)


@frappe.whitelist(allow_guest=True)
def get_stock(item_code=None):
    set_cors_headers()
    require_catalog_access()
    if item_code:
        cache_payload = {"item_code": item_code}
        cached = get_json_cache("stock", cache_payload)
        if cached is not None:
            return cached
        response = _get_stock([item_code]).get(item_code, {"available_qty": 0, "in_stock": False})
        return set_json_cache("stock", cache_payload, response, expires_in_sec=20)
    return _get_stock([])


@frappe.whitelist(allow_guest=True)
def get_categories():
    set_cors_headers()
    require_catalog_access()
    cached = get_json_cache("categories", {})
    if cached is not None:
        return cached
    group_columns = set(frappe.db.get_table_columns("Item Group"))
    optional_fields = [field for field in ["webshop_label_en", "webshop_label_ar", "webshop_description_en", "webshop_description_ar"] if field in group_columns]
    groups = frappe.get_all(
        "Item Group",
        filters={"show_in_website": 1},
        fields=["name", "item_group_name", "image", "parent_item_group"] + optional_fields,
        order_by="name asc",
    )
    nodes = {
        group.name: {
            "name": group.name,
            "label": group.get("webshop_label_en") or group.item_group_name,
            "label_en": group.get("webshop_label_en") or group.item_group_name,
            "label_ar": group.get("webshop_label_ar") or group.get("webshop_label_en") or group.item_group_name,
            "description_en": group.get("webshop_description_en") or "",
            "description_ar": group.get("webshop_description_ar") or group.get("webshop_description_en") or "",
            "image": full_url(group.image),
            "parent": group.parent_item_group,
            "children": [],
        }
        for group in groups
    }
    roots = []
    for node in nodes.values():
        parent = nodes.get(node["parent"])
        if parent and parent["name"] != node["name"]:
            parent["children"].append(node)
        else:
            roots.append(node)
    response = roots
    return set_json_cache("categories", {}, response, expires_in_sec=300)


@frappe.whitelist(allow_guest=True)
def get_search_suggestions(search):
    set_cors_headers()
    require_catalog_access()
    if not search or len(search) < 2:
        return []
    cache_payload = {"search": search.strip().lower()}
    cached = get_json_cache("suggestions", cache_payload)
    if cached is not None:
        return cached
    categories = frappe.get_all(
        "Item Group",
        filters={"show_in_website": 1, "item_group_name": ["like", f"%{search}%"]},
        fields=["name", "item_group_name", "image"],
        limit_page_length=3,
    )
    items = frappe.get_all(
        "Item",
        filters={"disabled": 0, "item_name": ["like", f"%{search}%"]},
        fields=["item_code", "item_name", "image", "item_group"],
        limit_page_length=5,
    )
    results = [
        {"type": "category", "id": row.name, "name": row.item_group_name, "image": full_url(row.image)}
        for row in categories
    ]
    price_list = _get_price_list()
    prices = _get_prices([row.item_code for row in items], price_list)
    items = [row for row in items if float((prices.get(row.item_code) or {}).get("rate") or 0) > 0]
    results.extend([
        {
            "type": "item",
            "id": row.item_code,
            "name": row.item_name,
            "image": full_url(row.image),
            "category": row.item_group,
            "price": (prices.get(row.item_code) or {}).get("rate"),
            "currency": (prices.get(row.item_code) or {}).get("currency"),
        }
        for row in items
    ])
    return set_json_cache("suggestions", cache_payload, results, expires_in_sec=30)


@frappe.whitelist(allow_guest=True)
def get_recommendations(item_code=None, item_group=None, limit=8):
    """Return lightweight, cacheable recommendations for landing pages and product cards."""
    set_cors_headers()
    require_catalog_access()
    try:
        limit = min(max(int(limit or 8), 1), 24)
    except (TypeError, ValueError):
        limit = 8
    source_group = item_group
    if item_code and not source_group:
        source_group = frappe.db.get_value("Item", item_code, "item_group")
    cache_payload = {"item_code": item_code, "item_group": source_group, "limit": limit}
    cached = get_json_cache("recommendations", cache_payload)
    if cached is not None:
        return cached
    filters = {"disabled": 0}
    if source_group:
        filters["item_group"] = source_group
    if item_code:
        filters["item_code"] = ["!=", item_code]
    priced_codes = _positive_price_codes(_get_price_list())
    filters["item_code"] = ["in", priced_codes]
    if item_code:
        filters["item_code"] = ["in", [code for code in priced_codes if code != item_code]]
    items = frappe.get_all(
        "Item",
        filters=filters,
        fields=["item_code", "item_name", "image", "item_group", "webshop_rating", "modified"],
        order_by="webshop_rating desc, modified desc",
        limit_page_length=limit,
    )
    codes = [row.item_code for row in items]
    prices = _get_prices(codes, _get_price_list())
    stocks = _get_stock(codes)
    recommendation_experience = _get_item_experience(codes)
    response = [
        {
            "item_code": row.item_code,
            "item_name": row.item_name,
            "image": full_url(row.image),
            "item_group": row.item_group,
            "rating": row.webshop_rating or 0,
            "price": (prices.get(row.item_code) or {}).get("rate"),
            "currency": (prices.get(row.item_code) or {}).get("currency"),
            "stock": stocks.get(row.item_code, {"available_qty": 0, "in_stock": False}),
            "in_stock": stocks.get(row.item_code, {}).get("in_stock", False),
            "video_url": recommendation_experience.get(row.item_code, {}).get("video_url"),
            "stage_images": recommendation_experience.get(row.item_code, {}).get("stage_images", []),
            "curated_tags": recommendation_experience.get(row.item_code, {}).get("curated_tags", []),
            "search_keywords": recommendation_experience.get(row.item_code, {}).get("search_keywords", []),
        }
        for row in items
    ]
    return set_json_cache("recommendations", cache_payload, response, expires_in_sec=90)
