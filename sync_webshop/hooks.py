app_title = "Sync Webshop"
app_publisher = "Dpono"
app_description = "Headless webshop backend for ERPNext"
app_email = "dev@dpono.com"
app_license = "mit"

doc_events = {
    "Webshop Editorial Collection": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Content Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop API Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Theme Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Announcement Bar": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Footer Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Item": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Item Group": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Item Price": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Bin": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Pricing Rule": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Shipping Rule": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Payment Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Paymob Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop AI Chat Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Dashboard Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Product Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Review": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop SEO Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop AI Vision Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Marketplace Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Regional Payment Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop PWA Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Landing Page Builder": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Subscription Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Courier Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Return Policy": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Currency Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Social Feed": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Enterprise AI Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop B2B Wholesale Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Live Shopping Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Flash Sale Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Recovery Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Fraud Shield Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Infrastructure Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Volume Pricing Rule": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Flash Sale Item": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Fraud Rule": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Ecosystem AI Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Marketplace Vendor Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Fintech Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Omnichannel Settings": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
    "Webshop Gift Card": {"on_update": "sync_webshop.api.utils.clear_webshop_cache"},
}


scheduler_events = {
    "hourly": [
        "sync_webshop.api.elite.run_scheduled_marketplace_sync",
        "sync_webshop.api.master_class.process_due_subscriptions",
        "sync_webshop.api.enterprise.process_abandoned_cart_recovery",
        "sync_webshop.api.enterprise.run_enterprise_maintenance",
    ],
}
