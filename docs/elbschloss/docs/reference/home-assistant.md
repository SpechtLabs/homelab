# Home Assistant

Neither instance is managed by Buckle, and their configuration isn't in this repo. They're in
the catalog ([catalog/home-assistant.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/home-assistant.yaml))
because the homelab serves them and watches them.

## At home: hass-elbschloss

| | |
|---|---|
| LAN | 192.168.0.62, plain HTTP on 8123 |
| Tailnet | `hass-elbschloss`, 100.75.135.70, `tag:smarthome`, `tag:o11y-agent` |
| Tailscale Service | `svc:hass`, hosted by Home Assistant's Tailscale add-on (its `services:` option); both ports go to `127.0.0.1:8123` |
| URLs | `https://hass.sphinx-map.ts.net` (tcp:443), `http://hass.sphinx-map.ts.net:8123` (tcp:8123) |
| Who | `group:hass-users` and `tag:o11y-collector` (443, 8123); admins through their `*` grant. Group members live in SpechtLabs/backstage_resources (private) |
| SSH | the policy lets admins and the jumphost in as root on `tag:smarthome` |
| Backups | nightly at 01:00 through Home Assistant's Synology DSM integration, as DSM user `hass`, over the LAN, into `/volume1/backup/hass` |
| UPS status | from isa's upsd over the LAN (192.168.0.118:3493): there's no tailnet grant from `tag:smarthome` to `svc:nut` |
| Metrics and logs | its Prometheus integration and log shipping to the `hass` tenants of Mimir and Loki on specht-labs (`hass-mimir` / `hass-loki.k8s.specht-labs.de`), through `svc:lgtm` (tcp:80) |
| SLO | `hlhassavail`, probe `http://hass.sphinx-map.ts.net:8123/` from isa |

API paths, from the catalog's `api:home-assistant-api`:

| Path | What |
|---|---|
| `/` | web UI; the collector probes it |
| `/api/` | REST API, bearer token (a long-lived access token) |
| `/api/websocket` | WebSocket API |
| `/api/prometheus` | metrics from the Prometheus integration (`hass_*`) |

`hass.elbschloss.xyz` resolves to the NAS (192.168.0.64), where a Nginx Proxy Manager proxy
host for it points at 192.168.0.62:8123. That container isn't running, so the name doesn't
answer (checked 2026-11-26).

Home Assistant has nothing on the NAS over the tailnet. The policy comment that `svc:nas`
carries SMB (tcp:445) for its backups is out of date: the NAS serves no port 445 on `svc:nas`.

## In Schiltach: hass-schiltach

| | |
|---|---|
| Tailnet | `hass-schiltach`, 100.89.41.43, `tag:smarthome`; reached only over the tailnet |
| URL | `http://hass-schiltach.sphinx-map.ts.net:8123` |
| System | [Schiltach](https://backstage.k8s.specht-labs.de/docs/default/system/schiltach/) |
| Metrics and logs | the `hass-schiltach` tenants of Mimir and Loki on specht-labs |
| NAS | doesn't use it |

Both instances share the Grafana dashboard `Home Assistant — Diagnostics` (folder
Applications), which picks the tenant from its `site` variable.
