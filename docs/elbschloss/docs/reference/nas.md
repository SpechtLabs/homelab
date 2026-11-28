# Synology NAS

Sources: [nas/](https://github.com/SpechtLabs/homelab/tree/main/nas) and
[nas/catalog-info.yaml](https://github.com/SpechtLabs/homelab/blob/main/nas/catalog-info.yaml);
everything else is DSM's own configuration and isn't in git. Live values read on 2026-11-26.

## Device

| | |
|---|---|
| Model | Synology DS923+ |
| DSM | 7.4.1 (build 90080) |
| LAN | 192.168.0.64 (`bond0`), `nas.local` |
| Tailnet | `nas-elbschloss`, 100.71.201.45, tags `tag:nas`, `tag:tsidp-client` |
| Tailscale | DSM package, 1.98.4. Binary `/var/packages/Tailscale/target/bin/tailscale`, LocalAPI socket `/var/packages/Tailscale/var/tailscaled.sock` |
| SSH | `ssh -J cedi@nyx king@nas.local`; `sudo` works for `king` |
| Docker | `/usr/local/bin/docker` (not on `sudo`'s PATH), Compose v2.20.1 |

## Serve config

As `sudo /var/packages/Tailscale/target/bin/tailscale serve get-config --all` prints it:

```json
{
  "version": "0.0.1",
  "services": {
    "svc:nas": {
      "endpoints": {
        "tcp:443": "https+insecure://localhost:5001",
        "tcp:5001": "tcp://localhost:5001",
        "tcp:6690": "tcp://localhost:6690"
      }
    },
    "svc:nfs": {
      "endpoints": {
        "tcp:2049": "tcp://127.0.0.1:2049"
      }
    },
    "svc:node-exporter": {
      "endpoints": {
        "tcp:9100": "tcp://localhost:9100"
      }
    },
    "svc:stream": {
      "endpoints": {
        "tcp:443": "http://localhost:8096"
      }
    }
  }
}
```

The node itself serves nothing (`tailscale serve status`: "No serve config"). tailscaled keeps
this in its state file: it survives reboots and package updates, not an uninstall.

The Service definitions in the admin console: `svc:nas` tcp:443, tcp:5001, tcp:6690;
`svc:stream` tcp:443; `svc:node-exporter` tcp:9100; `svc:nfs` tcp:2049.

## Shared folders that matter here

| Path | Holds | Written by |
|---|---|---|
| `/volume1/homelab` | NFS-exported folder | |
| `/volume1/homelab/<name>` | the nightly NAS backups, 14 days each: `buckle` (`buckle-nightly-<date>.db`), `buckle-secrets` and `tsidp` (`.tar.gz`) from isa, `k3s` from clusterpi-leader | `modules/nas-backup` at 02:00 Europe/Berlin, through `svc:nfs` ([vars/backups.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/backups.yaml)) |
| `/volume1/backup/github-backup` | GitHub repositories and stars | `github-backup`, hourly |
| `/volume1/backup/hass` | Home Assistant's `Automatic_backup_<HA version>_<date>_01.00_<n>.tar` and `_meta.json` | Home Assistant at 01:00, DSM user `hass`, over the LAN |
| `/volume1/docker/<project>` | compose projects | you, by hand |
| `/volume1/Media` | Jellyfin's library (`/data/media` in the container) | |

## NFS

| | |
|---|---|
| Versions on | 2, 3, 4, 4.1 (`/proc/fs/nfsd/versions`: `+2 +3 +4 +4.1 -4.2`) |
| Used | 4.1 only, through `svc:nfs` (tcp:2049) |
| Export rule | per shared folder, DSM: Control Panel > Shared Folder > Edit > NFS Permissions |

`/etc/exports` (DSM writes it):

```text
/volume1/homelab  127.0.0.1(rw,async,no_wdelay,insecure,no_root_squash,insecure_locks,sec=sys,anonuid=1025,anongid=100)
                  ::1(rw,async,no_wdelay,insecure,no_root_squash,insecure_locks,sec=sys,anonuid=1025,anongid=100)
```

`insecure` is DSM's "Allow connections from non-privileged ports". Only the `127.0.0.1` rule
does anything: the serve forward names `127.0.0.1`, because `localhost` is `::1` on the NAS.

Clients:

| Client | Mount | Options |
|---|---|---|
| isa and clusterpi-leader (`nas-backup` module) | `nfs.sphinx-map.ts.net:/volume1/homelab/<folder>`, mounted only while the backup runs | `nfsvers=4.1,soft,timeo=150,retrans=3` |

## Compose projects

Deployed through DSM's Container Manager, one Project per directory. Containers seen with
`docker ps` on 2026-11-26:

| Project | Repo | NAS directory | Containers running | Ports |
|---|---|---|---|---|
| `media` | [nas/media](https://github.com/SpechtLabs/homelab/tree/main/nas/media) | `/volume1/docker/media` | `jellyfin` (`jellyfin/jellyfin:latest`, host network) | 8096; 1900, 7359 discovery |
| `o11y` | [nas/o11y](https://github.com/SpechtLabs/homelab/tree/main/nas/o11y) | `/volume1/docker/o11y` | `NodeExporter` (`prom/node-exporter:latest`), `SNMPExporter` (`prom/snmp-exporter:latest`), `cAdvisor` (`gcr.io/cadvisor/cadvisor:latest`), all host network | 9100, 9116, 8123 |
| `obsidian` | [nas/obsidian](https://github.com/SpechtLabs/homelab/tree/main/nas/obsidian) | `/volume1/docker/obsidian` | `obsidian-livesync` (`couchdb:3.3.3`, host network) | 5984 |
| `backup` | [nas/backup](https://github.com/SpechtLabs/homelab/tree/main/nas/backup) | `/volume1/docker/backup` | `github-backup` (`ghcr.io/sierrasoftworks/github-backup:v3.3.5`, host network), hourly into `/volume1/backup/github-backup` | |

Nginx Proxy Manager (80, 81, 443) used to be part of `media`. It's gone from the NAS and, since
2026-11, from the repo; its old data is still in `/volume1/docker/media/nginx-proxy/`. The repo's
`o11y` has a commented-out `alloy` service that the NAS's copy doesn't; it does nothing.

### Secrets that stay on the NAS

Not in git (`.gitignore`), only next to the compose file on the NAS. The `*.example` files in the
repo show their shape.

| File on the NAS | Holds | Example in the repo |
|---|---|---|
| `/volume1/docker/obsidian/.env` | `COUCHDB_PASSWORD`, the `obsidian_admin` password CouchDB creates on first start | [nas/obsidian/.env.example](https://github.com/SpechtLabs/homelab/blob/main/nas/obsidian/.env.example) |
| `/volume1/docker/obsidian/data/etc/local.d/docker.ini` | CouchDB's accounts (`obsidian_admin`, `obsidian_user`) and cookie secret, written by CouchDB | none: CouchDB's data |
| `/volume1/docker/backup/github-backup/config.yaml` | github-backup's entries, each with a GitHub username and token (`!UsernamePassword`) | [nas/backup/github-backup/config.example.yaml](https://github.com/SpechtLabs/homelab/blob/main/nas/backup/github-backup/config.example.yaml) |

node-exporter runs with `--collector.disable-defaults` plus `stat`, `time`, `cpu`, `loadavg`,
`hwmon`, `meminfo` and `diskstats`. snmp-exporter reads
`/volume1/docker/o11y/snmp-exporter/snmp.yaml` (identical to the repo's), which comes from
[wozniakpawel/synology-grafana-prometheus-overly-comprehensive-dashboard](https://github.com/wozniakpawel/synology-grafana-prometheus-overly-comprehensive-dashboard).

## DSM settings outside the repo

| Setting | Where in DSM | Value |
|---|---|---|
| SSO through tsidp | Control Panel > Domain/LDAP > SSO Client | redirect URI `https://nas.sphinx-map.ts.net`, no trailing slash; tsidp client `synology` |
| NFS permissions | Control Panel > Shared Folder > Edit > NFS Permissions | `127.0.0.1`, non-privileged ports allowed |
| UPS | `/usr/syno/etc/ups/synoups.conf` | `ups_mode="slave"`, `upsslave_server="192.168.0.154"`: a network UPS client of the UPS Tower, not of isa |

The UPS file also has `ups_acl="192.168.0.72|192.168.0.62"` (the NUC and Home Assistant). That's
an ACL for a NUT server, which the NAS doesn't run any more.

## Catalog entities

`resource:nas`, `component:synology-dsm` (APIs `nas-nfs`, `synology-dsm-web`,
`synology-dsm-https`, `synology-drive`), `component:jellyfin` (`jellyfin-web`),
`component:obsidian-livesync`, `component:github-backup`, and in the observability System `component:nas-exporters`
(`nas-node-exporter`). All in [nas/catalog-info.yaml](https://github.com/SpechtLabs/homelab/blob/main/nas/catalog-info.yaml).
