# Backups

Nightly backups to the NAS by the `nas-backup` module
([`modules/nas-backup`](https://github.com/SpechtLabs/homelab/tree/main/modules/nas-backup)). The
list is [`vars/backups.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/backups.yaml);
a host runs the entries whose `group` it's in.

| Backup | Host (group) | Kind | Source | NAS folder | Kept |
|---|---|---|---|---|---|
| `buckle` | isa (`buckle-server`) | sqlite | `/var/lib/buckle-server/buckle.db` | `/volume1/homelab/buckle` | 3 days local, 14 on the NAS |
| `buckle-secrets` | isa (`buckle-server`) | dir | `/etc/buckle/secrets` | `/volume1/homelab/buckle-secrets` | 3 / 14 |
| `tsidp` | isa (`tsidp`) | dir | `/data` (tsidp's state) | `/volume1/homelab/tsidp` | 3 / 14 |
| `k3s` | clusterpi-leader (`k3s-server`) | sqlite | `/var/lib/rancher/k3s/server/db/state.db` | `/volume1/homelab/k3s` | 3 / 14 |

**All four are sensitive.** The Buckle database holds every host's token, `buckle-secrets` every
secret Buckle hands out (the K3S token, NUT passwords, the Argo CD age key, Jitsi's secrets),
`tsidp` the OIDC signing key, `k3s` the cluster's CA keys (encrypted with `K3S_TOKEN`, which is in
`buckle-secrets`). Every copy is root's, mode 0600, on the host and on the NAS; the NAS folders
need their DSM permissions kept to the admin account, because DSM's ACLs can override the mode.

## How a run works

| | |
|---|---|
| Timer | `nas-backup.timer`: 02:00 Europe/Berlin (whatever the host's zone), up to 5 min random delay, `Persistent=true`; before the 03:00 nightly upgrades |
| Script | `/usr/local/sbin/nas-backup run <textfile dir>` ([`nas-backup.sh`](https://github.com/SpechtLabs/homelab/blob/main/modules/nas-backup/files/nas-backup.sh)) |
| Config | `/etc/nas-backup/backups` (one line per backup), `/etc/nas-backup/nfs-root` (`nfs.sphinx-map.ts.net:/volume1/homelab`), rendered by Buckle |
| `sqlite` | `VACUUM INTO` a new file (one read transaction, consistent while the database is written to), then `PRAGMA quick_check`; `<backup>-nightly-YYYY-MM-DD.db` |
| `dir` | `tar -czf` of the directory; `<backup>-nightly-YYYY-MM-DD.tar.gz` |
| Local | `/var/backups/<backup>/`, 0700 |
| NAS | NFS v4.1 through `svc:nfs`, mounted at `/run/nas-backup/<folder>` for the copy and unmounted after |
| Failure | One backup failing doesn't stop the others; the unit fails if any did |

A host's tag needs a grant to `svc:nfs` on `tcp:2049`: `tag:buckle-server` and `tag:k3s-server`,
rendered from the `nas-backup` Component's `tailnet-src` in
[`modules/nas-backup/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/nas-backup/catalog-info.yaml).

## Metrics

In the host's textfile directory (`/var/lib/prometheus/node-exporter/`), exported by Alloy with
`job="node_exporter"`, `instance="<host>:9100"`:

| Metric | Labels | Written by |
|---|---|---|
| `nas_backup_configured` | `backup` | Buckle (`nas_backup_configured.prom`), at apply time: what the host should back up |
| `nas_backup_last_success_timestamp_seconds` | `backup`, `target` (`local`, `nas`) | the script (`nas_backup.prom`), after each copy |
| `nas_backup_size_bytes` | `backup` | the script, size of the latest copy |

Alerts on them: [Alerts and SLO](alerts.md). The informational health check `nas-backup/recent`
runs `nas-backup check`, which fails when a configured backup has no NAS copy younger than 26 h.

## Restore

[Buckle database](../how-to/restore-the-server-database.md) ·
[Buckle secrets](../how-to/restore-the-buckle-secrets.md) ·
[tsidp](../how-to/restore-tsidp.md) ·
[k3s datastore](../how-to/restore-the-k3s-datastore.md)
