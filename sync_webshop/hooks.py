app_name = "sync_webshop"
app_title = "Sync Webshop"
app_publisher = "Dpono"
app_description = "Headless webshop backend for ERPNext"
app_email = "dev@dpono.com"
app_license = "mit"

doc_events = {
	"Webshop Content Settings": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	},
	"Webshop API Settings": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	},
	"Webshop Theme Settings": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	},
	"Webshop Announcement Bar": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	},
	"Webshop Footer Settings": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	},
	"Item": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	},
	"Item Group": {
		"on_update": "sync_webshop.api.utils.clear_webshop_cache"
	}
}
