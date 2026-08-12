# Automated ERPNext Backups

The included systemd unit and timer run a daily `bench --site <site> backup --with-files` job. The script is configured through `BENCH_PATH`, `SITE_NAME`, and `RETENTION_DAYS` environment variables; defaults are `/home/frappe/frappe-bench`, `erpnext.localhost`, and 14 days.

Install the files as root:

```bash
install -m 0750 sync-webshop-backup.sh /usr/local/sbin/sync-webshop-backup
install -m 0644 sync-webshop-backup.service sync-webshop-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sync-webshop-backup.timer
systemctl start sync-webshop-backup.service
```

Backups are written to the site’s private backups directory. Verify the latest SQL archive, files archive, and service status after installation. For disaster recovery, copy the backup directory to storage outside the application server; the timer provides local recovery, not protection against total server loss.
