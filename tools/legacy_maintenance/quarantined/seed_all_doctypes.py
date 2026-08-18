import frappe
import json
import random
import datetime

def execute():
    frappe.init("erpnext.localhost")
    frappe.connect()

    doctypes = frappe.get_all("DocType", filters={"module": "Sync Webshop"}, pluck="name")
    print(f"Found {len(doctypes)} DocTypes in Sync Webshop module.")

    report = {}

    for dt in doctypes:
        meta = frappe.get_meta(dt)
        if meta.istable or meta.issingle:
            # Handle Single or Table separately if needed, but let's focus on main doctypes
            continue

        print(f"Seeding/Checking DocType: {dt}")

        # Check if records already exist
        existing = frappe.get_all(dt, limit=1)
        if existing:
            print(f"  -> Record already exists for {dt}, updating fields to ensure no empty fields.")
            doc = frappe.get_doc(dt, existing[0].name)
        else:
            print(f"  -> Creating new record for {dt}")
            doc = frappe.new_doc(dt)

        # Fill fields
        for f in meta.fields:
            if f.fieldtype in ["Section Break", "Column Break", "HTML", "Button", "Read Only", "Heading"]:
                continue
            if f.fieldname in ["name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"]:
                continue

            current_val = doc.get(f.fieldname)
            if not current_val:
                # Generate sample data based on fieldtype
                sample_val = get_sample_value(f)
                if sample_val is not None:
                    try:
                        doc.set(f.fieldname, sample_val)
                    except Exception as e:
                        print(f"     Could not set {f.fieldname} ({f.fieldtype}): {e}")

        try:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            report[dt] = "Success"
            print(f"  -> Successfully saved {dt}")
        except Exception as e:
            frappe.db.rollback()
            report[dt] = f"Error: {str(e)}"
            print(f"  -> Error saving {dt}: {e}")

    print("Seeding complete.")
    print(json.dumps(report, indent=2))

def get_sample_value(f):
    ft = f.fieldtype
    opts = f.options

    if ft in ["Data", "Small Text", "Text", "Long Text", "Text Editor", "Code"]:
        if "email" in f.fieldname:
            return "sample_user@syncwebshop.com"
        elif "phone" in f.fieldname:
            return "+966500000000"
        elif "url" in f.fieldname or "image" in f.fieldname or "attachment" in f.fieldname:
            return "/files/kit2a65be.webp"
        elif "color" in f.fieldname:
            return "#173F3A"
        else:
            return f"Sample {f.label or f.fieldname} Value"

    elif ft in ["Int", "Long"]:
        return random.randint(1, 100)

    elif ft in ["Float", "Currency", "Percent"]:
        return round(random.uniform(10.0, 500.0), 2)

    elif ft == "Check":
        return 1

    elif ft == "Select":
        if opts:
            lines = [l.strip() for l in opts.split("\n") if l.strip()]
            if lines:
                return lines[0]
        return "Default"

    elif ft == "Date":
        return str(datetime.date.today())

    elif ft == "Datetime":
        return str(datetime.datetime.now())

    elif ft == "Link":
        # Try to find a valid link
        if opts and frappe.db.exists("DocType", opts):
            existing_links = frappe.get_all(opts, limit=5, pluck="name")
            if existing_links:
                return existing_links[0]
        return None

    return None

if __name__ == "__main__":
    execute()
