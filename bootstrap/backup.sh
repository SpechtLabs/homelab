#!/bin/sh
# Nightly copy of the Buckle server's state to the NAS. Restore = stop the
# server, put buckle.db back, start it; secrets come from your password manager.
set -eu
dest=/mnt/nas/backups/buckle
mkdir -p "$dest"
sqlite3 /var/lib/buckle-server/buckle.db ".backup '$dest/buckle-$(date +%F).db'"
find "$dest" -name 'buckle-*.db' -mtime +14 -delete
