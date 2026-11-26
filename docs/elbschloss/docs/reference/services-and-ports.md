# Services and ports

## Tailscale Services hosted here

Serve config read live on the NAS and isa (`tailscale serve get-config --all`) on 2026-11-26.
Grants come from [tailscale/policy.hujson](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy.hujson),
which Backstage renders from the catalog. The Service definitions (name and ports) exist only
in the Tailscale admin console.

| Service | Address | Host | Port: backend | Who may reach it |
|---|---|---|---|---|
| `svc:nas` | `https://nas.sphinx-map.ts.net` | nas-elbschloss | tcp:443: `https+insecure://localhost:5001` (DSM)<br>tcp:5001: `tcp://localhost:5001` (DSM HTTPS, the mobile apps)<br>tcp:6690: `tcp://localhost:6690` (Drive sync) | `group:synology-users` (443, 5001, 6690); `tag:o11y-collector` (443) |
| `svc:stream` | `https://stream.sphinx-map.ts.net` | nas-elbschloss | tcp:443: `http://localhost:8096` (Jellyfin) | `group:synology-users`, `tag:o11y-collector` (443) |
| `svc:node-exporter` | `http://node-exporter.sphinx-map.ts.net:9100` | nas-elbschloss | tcp:9100: `tcp://localhost:9100` | `tag:o11y-collector` |
| `svc:nfs` | `nfs.sphinx-map.ts.net:/volume1/...` | nas-elbschloss | tcp:2049: `tcp://127.0.0.1:2049` (NFS v4.1) | `tag:buckle-server` |
| `svc:nut` | `nut.sphinx-map.ts.net:3493` | isa | tcp:3493: `tcp://localhost:3493` (upsd) | `tag:buckle-agent` |
| `svc:hass` | `https://hass.sphinx-map.ts.net`, `http://hass.sphinx-map.ts.net:8123` | hass-elbschloss (Home Assistant's Tailscale add-on, `services:` option) | tcp:443 and tcp:8123: `127.0.0.1:8123` | `group:hass-users`, `tag:o11y-collector` (443, 8123) |

`group:admins` has a `*` grant and reaches all of them. Each Service has one admin-owned host
tag as its auto-approver: `tag:nas` for the four NAS Services, `tag:nut-server` for `svc:nut`,
`tag:smarthome` for `svc:hass`.

isa also hosts `svc:buckle` (tcp:443, tcp:7700) and runs the `idp` node; those belong to the
[Fleet](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/) and
[Tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) Systems.

`svc:nas` has no port 80: `http://nas.sphinx-map.ts.net` gets nothing.

## Device addresses

Nothing here is meant to be reached on its device address over the tailnet. The policy's tests
check, among others, that `nas-elbschloss:443`, `:5001`, `:6690`, `:8096`, `:2049`,
`hass-elbschloss:8123` and `tag:nut-server:3493` are closed to the groups and tags that use the
Services. The NAS passes unserved ports of its Service addresses through to the device, so its
grants list ports (see [The NAS and Tailscale](../explanation/nas-and-tailscale.md)).

## LAN ports

Traffic that stays on `192.168.0.0/24` and needs no grant.

| Address | What | Used by |
|---|---|---|
| 192.168.0.156:3493 | UPS Tower's NUT server (UPS `ups`, SSL) | isa's `dummy-ups` proxy and isa's upsmon; DSM's UPS client |
| 192.168.0.118:3493 | upsd on isa (`LISTEN 0.0.0.0 3493`) | Home Assistant (UPS status over the LAN) |
| 192.168.0.64:5000, :5001 | DSM (HTTP, HTTPS) | Home Assistant's Synology DSM integration (backups); which port isn't recorded |
| 192.168.0.64:8096 | Jellyfin (host network); 1900 and 7359 for discovery | LAN clients |
| 192.168.0.64:9100 | node-exporter | `svc:node-exporter` forwards here (localhost) |
| 192.168.0.64:9116 | snmp-exporter (`/snmp`, module `synology`) | the collector on isa |
| 192.168.0.64:8123 | cAdvisor | the collector on isa |
| 192.168.0.62:8123 | Home Assistant, plain HTTP | LAN clients |
| isa :4317, :4318 | Alloy's OTLP receiver (gRPC, HTTP) | the labk3s cluster (see Observability) |
| isa :12345 | Alloy's HTTP server (`--server.http.listen-addr=0.0.0.0:12345`) | health check `/-/ready` |

The repo's `nas/media` compose project also puts Nginx Proxy Manager on 80, 81 and 443 of the
NAS, but that container isn't deployed (see [Synology NAS](nas.md#compose-projects)).
