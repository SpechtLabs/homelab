#!/bin/sh
# Managed by Buckle (modules/buckle-server). The Buckle server's database,
# nightly: a consistent `sqlite3 .backup` kept on this host and copied to the
# NAS. Restore: stop buckle-server, put the copy back as
# /var/lib/buckle-server/buckle.db, start it. The secrets in /etc/buckle/secrets
# are not in it: they live in your password manager.
set -eu
# The database holds fleet state and per-host tokens, and the NAS folder is
# world-writable: every copy is root's alone.
umask 077
db=/var/lib/buckle-server/buckle.db
local_dir=/var/backups/buckle
nas_mount=/mnt/nas/backups
nas_dir=$nas_mount              # the export is the Buckle backups' own folder
metrics=${1:?usage: buckle-backup TEXTFILE_DIR}/buckle_backup.prom
name="buckle-nightly-$(date +%F).db"

stamp() {  # target -> record a success time for it, keeping the other's
    tmp=$(mktemp "$metrics.XXXXXX")
    { echo "# HELP buckle_backup_last_success_timestamp_seconds When the Buckle database was last backed up, per target."
      echo "# TYPE buckle_backup_last_success_timestamp_seconds gauge"
      grep '^buckle_backup_last_success_timestamp_seconds{' "$metrics" 2>/dev/null | grep -v "target=\"$1\"" || true
      echo "buckle_backup_last_success_timestamp_seconds{target=\"$1\"} $(date +%s)"
    } > "$tmp"
    chmod 0644 "$tmp"; mv "$tmp" "$metrics"
}

install -d -m 0700 "$local_dir"
sqlite3 "$db" ".backup '$local_dir/$name.tmp'"
mv "$local_dir/$name.tmp" "$local_dir/$name"
find "$local_dir" -maxdepth 1 -name 'buckle-nightly-*.db' -mtime +3 -delete
stamp local

if ! mountpoint -q "$nas_mount"; then
    echo "the NAS isn't mounted at $nas_mount: kept the local copy only" >&2
    exit 1
fi
cp "$local_dir/$name" "$nas_dir/$name.tmp"
mv "$nas_dir/$name.tmp" "$nas_dir/$name"
find "$nas_dir" -maxdepth 1 -name 'buckle-nightly-*.db' -mtime +14 -delete
stamp nas
echo "backed up to $local_dir/$name and $nas_dir/$name"
