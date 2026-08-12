# WSGI asset compatibility template

`sync_webshop_wsgi.py.example` wraps Frappe’s WSGI application with two safeguards required by this deployment pattern. It preloads `sites/assets/assets.json` so Frappe’s asset helpers always receive a mapping, and it redirects legacy bare bundle URLs such as `/file_uploader.bundle.js` to the current hashed path under `/assets/frappe/dist/js/`.

The wrapper reads these optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `FRAPPE_BENCH_PATH` | `/home/frappe/frappe-bench` | Absolute bench path. |
| `FRAPPE_SITE_NAME` | `erpnext.localhost` | Frappe site name injected into requests. |

Copy the template to the bench entrypoint used by Gunicorn, set the variables in the service environment when the server differs from the defaults, and restart the API service after an asset build. This prevents the Desk from requesting unhashed bundle names that return SPA/404 responses while keeping asset filenames fully dynamic.
