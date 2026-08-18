# Archived Sync Webshop Maintenance Scripts

These scripts were previously stored inside the importable Frappe application package but were not referenced by `hooks.py`, `patches.txt`, runtime modules, or the deployed storefront. They have been retained here for historical reference and recovery; they are not loaded during normal Frappe operation.

For a repeatable data migration, a reviewed idempotent patch should be added to `sync_webshop/patches.txt` instead of executing an archived script manually.
