# Nginx deployment template

The `sync_webshop.conf.example` file contains the reference dual-port reverse-proxy layout used by the live deployment. It keeps the React storefront on port 80, the Frappe Desk on the ERP port, and Socket.IO on its dedicated realtime service.

Before installing it, replace the following placeholders for the target server:

| Placeholder | Meaning |
|---|---|
| `YOUR_SYNC_WEBSHOP_FRONTEND` | Absolute path to the built React storefront directory. |
| `YOUR_FRAPPE_SITE_NAME` | Frappe site name used in `X-Frappe-Site-Name` and the public files path. |
| `YOUR_FRAPPE_BACKEND_PORT` | Local Gunicorn/Frappe backend port. |
| `YOUR_SOCKETIO_PORT` | Local Frappe Socket.IO port. |
| `YOUR_ERP_DESK_PORT` | Public ERP Desk port used in redirect rewriting. |

The `location ^~ /files/` block is intentional. Product and content images uploaded through Frappe Desk are stored under the site’s `public/files` directory, and the storefront must serve those files directly rather than routing them through the SPA fallback or an unavailable upstream. The `/assets` route remains separate for compiled frontend and Frappe assets.

After substituting the values, validate and reload Nginx:

```bash
nginx -t
systemctl reload nginx
```

Then verify the storefront shell, the ERP Desk shell, the catalog and content APIs, Socket.IO polling, and at least one uploaded image. All content and presentation values remain configurable from the Webshop Single DocTypes in Frappe Desk; this file only controls transport and static-file routing.
