#!/bin/sh
# Managed by Buckle (modules/nas-backup). Nightly backups to the NAS, one line
# of /etc/nas-backup/backups per backup (vars/backups.yaml):
#
#   name kind source folder keep_local keep_nas
#
# kind sqlite: a consistent copy of a live SQLite database (VACUUM INTO, one
#              read transaction, so a database written to every second, as
#              k3s's kine is, still copies in one go), checked, as
#              <name>-nightly-<date>.db;
# kind dir:    a tarball of the directory, <name>-nightly-<date>.tar.gz.
#
# Each copy is kept in /var/backups/<name> for keep_local days and in the NAS
# folder /volume1/homelab/<folder> (NFS v4.1 through svc:nfs, mounted for the
# run only) for keep_nas days. Every success is a timestamp per backup and
# target in TEXTFILE_DIR/nas_backup.prom; the alerts in k8s-deployment
# (grafanaalertrules-homelab.yaml) read it. One backup failing doesn't stop
# the others; the run exits non-zero if any failed.
#
#   nas-backup run TEXTFILE_DIR     back everything up
#   nas-backup check TEXTFILE_DIR   exit 1 unless every backup reached the NAS within 26 h
set -eu
# What these hold (fleet state and per-host tokens, every secret Buckle hands
# out, tsidp's signing key, the cluster's CA) is root's alone, here and on the
# NAS, whose folders are world-writable.
umask 077

conf=/etc/nas-backup/backups
nfs_root=$(cat /etc/nas-backup/nfs-root)    # nfs.<tailnet>:/volume1/homelab
cmd=${1:?usage: nas-backup run|check TEXTFILE_DIR}
metrics=${2:?usage: nas-backup run|check TEXTFILE_DIR}/nas_backup.prom
date=$(date +%F)
failed=0

stamp() {  # backup target bytes -> record a success, keeping every other series
    tmp=$(mktemp "$metrics.XXXXXX")
    { echo "# HELP nas_backup_last_success_timestamp_seconds When a backup last reached a target (local, nas)."
      echo "# TYPE nas_backup_last_success_timestamp_seconds gauge"
      grep '^nas_backup_last_success_timestamp_seconds{' "$metrics" 2>/dev/null |
          grep -v "^nas_backup_last_success_timestamp_seconds{backup=\"$1\",target=\"$2\"}" || true
      echo "nas_backup_last_success_timestamp_seconds{backup=\"$1\",target=\"$2\"} $(date +%s)"
      echo "# HELP nas_backup_size_bytes Size of a backup's latest copy."
      echo "# TYPE nas_backup_size_bytes gauge"
      grep '^nas_backup_size_bytes{' "$metrics" 2>/dev/null | grep -v "^nas_backup_size_bytes{backup=\"$1\"}" || true
      echo "nas_backup_size_bytes{backup=\"$1\"} $3"
    } > "$tmp"
    chmod 0644 "$tmp"; mv "$tmp" "$metrics"
}

backup() {  # name kind source folder keep_local keep_nas
    # Called as `backup ... || failed=1`, where `set -e` doesn't apply: every
    # step that can fail says so itself.
    name=$1 kind=$2 src=$3 folder=$4 keep_local=$5 keep_nas=$6
    local_dir=/var/backups/$name
    case $kind in
        sqlite) file="$name-nightly-$date.db" ;;
        dir)    file="$name-nightly-$date.tar.gz" ;;
        *)      echo "$name: unknown kind $kind" >&2; return 1 ;;
    esac
    install -d -m 0700 "$local_dir" || return 1
    rm -f "$local_dir/$file.tmp"
    case $kind in
        sqlite)
            sqlite3 "$src" "VACUUM INTO '$local_dir/$file.tmp'" </dev/null || {
                echo "$name: VACUUM INTO failed" >&2; return 1; }
            check=$(sqlite3 "$local_dir/$file.tmp" 'PRAGMA quick_check;' </dev/null) || return 1
            [ "$check" = ok ] || { echo "$name: the copy fails quick_check: $check" >&2; return 1; } ;;
        dir)
            tar -C "$(dirname "$src")" -czf "$local_dir/$file.tmp" "$(basename "$src")" </dev/null || {
                echo "$name: tar failed" >&2; return 1; } ;;
    esac
    mv "$local_dir/$file.tmp" "$local_dir/$file" || return 1
    find "$local_dir" -maxdepth 1 -name "$name-nightly-*" -mtime +"$keep_local" -delete
    size=$(stat -c %s "$local_dir/$file")
    stamp "$name" local "$size"

    mnt=/run/nas-backup/$folder
    install -d -m 0700 "$mnt" || return 1
    if ! mountpoint -q "$mnt"; then
        mount -t nfs -o nfsvers=4.1,soft,timeo=150,retrans=3 "$nfs_root/$folder" "$mnt" </dev/null || {
            echo "$name: can't mount $nfs_root/$folder: kept the local copy only" >&2; return 1; }
    fi
    rc=0
    # The NAS's ACLs can hand new files to everyone: chmod after the copy.
    { cp "$local_dir/$file" "$mnt/$file.tmp" &&
      chmod 0600 "$mnt/$file.tmp" &&
      mv "$mnt/$file.tmp" "$mnt/$file" &&
      find "$mnt" -maxdepth 1 -name "$name-nightly-*" -mtime +"$keep_nas" -delete; } || rc=1
    umount "$mnt" || true
    [ "$rc" -eq 0 ] || { echo "$name: copying to the NAS failed" >&2; return 1; }
    stamp "$name" nas "$size"
    echo "$name: backed up to $local_dir/$file and $nfs_root/$folder/$file"
}

case $cmd in
    run)
        while read -r name kind src folder keep_local keep_nas <&3; do
            case $name in ''|'#'*) continue ;; esac
            backup "$name" "$kind" "$src" "$folder" "$keep_local" "$keep_nas" || failed=1
        done 3< "$conf"
        ;;
    check)
        now=$(date +%s)
        while read -r name _ <&3; do
            case $name in ''|'#'*) continue ;; esac
            t=$(sed -n "s/^nas_backup_last_success_timestamp_seconds{backup=\"$name\",target=\"nas\"} //p" "$metrics" 2>/dev/null)
            if [ -z "$t" ] || [ $((now - ${t%.*})) -gt 93600 ]; then
                echo "$name: no NAS copy in the last 26 h"; failed=1
            fi
        done 3< "$conf"
        [ "$failed" -eq 1 ] || echo "ok: every backup reached the NAS in the last 26 h"
        ;;
    *) echo "usage: nas-backup run|check TEXTFILE_DIR" >&2; exit 2 ;;
esac
exit "$failed"
