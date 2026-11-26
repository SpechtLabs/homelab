# Tailscale Services

Every Tailscale Service on `sphinx-map.ts.net`, reached as
`<name>.sphinx-map.ts.net`. VIPs as of 2026-11-26; the source of truth is
`dig +short <name>.sphinx-map.ts.net`. A VIP lasts as long as the Service
exists, whichever host serves it.

| Service | VIP | Served by | Ports | Who (besides `group:admins`, who reach everything) |
|---|---|---|---|---|
| `svc:buckle` | 100.120.125.116 | isa | tcp:443 (UI, API), tcp:7700 (agents' gRPC, PROXY v2) | 443: `group:sre`; 7700: `tag:buckle-agent` |
| `svc:nut` | 100.65.115.181 | isa | tcp:3493 | `tag:buckle-agent` |
| `svc:nas` | 100.87.152.84 | nas-elbschloss | tcp:443 (DSM), tcp:5001 (DSM HTTPS, mobile apps), tcp:6690 (Drive) | `group:synology-users` (all three); `tag:o11y-collector` (443) |
| `svc:stream` | 100.115.192.64 | nas-elbschloss | tcp:443 (Jellyfin) | `group:synology-users`, `tag:o11y-collector` |
| `svc:node-exporter` | 100.118.146.244 | nas-elbschloss | tcp:9100 | `tag:o11y-collector` |
| `svc:nfs` | 100.123.239.59 | nas-elbschloss | tcp:2049 (NFS v4.1) | `tag:buckle-server`, `tag:k3s-server` (nightly backups, [`modules/nas-backup`](https://github.com/SpechtLabs/homelab/blob/main/modules/nas-backup/module.yaml)) |
| `svc:hass` | 100.81.129.181 | hass-elbschloss (Home Assistant add-on's `services:`) | tcp:443 (HTTPS), tcp:8123 (plain HTTP) | `group:hass-users`, `tag:o11y-collector` |
| `svc:labk3s` | 100.67.145.122 | clusterpi-leader | tcp:6443 (k3s API, passed through) | `tag:k3s-node`, `tag:o11y-collector` |
| `svc:lgtm` | 100.102.186.94 | specht-labs `tailnet-ingress` (specht-labs-ingress-0/1) | tcp:80 | `tag:buckle-agent`, `tag:o11y-agent`, `tag:o11y-collector`, `tag:smarthome` |
| `svc:argocd` | 100.93.249.30 | specht-labs `tailnet-ingress` | tcp:443 (TLS passthrough) | admins only |
| `svc:backstage` | 100.93.117.9 | specht-labs `tailnet-ingress` | tcp:443 | admins only |
| `svc:labk3s-argocd-api` | 100.126.137.0 | labk3s `tailnet-ingress` (labk3s-ingress-0/1) | tcp:443 | `tag:backstage` |
| `svc:lab-argocd` | 100.112.213.104 | labk3s `tailnet-ingress` (an Ingress, Tailscale terminates TLS) | tcp:443 | `group:sre` |

## Where each one is defined

| Service | Definition (ports) | Auto approver | Serve config | Grants from |
|---|---|---|---|---|
| `svc:buckle` | admin console | `approve-buckle`: `tag:buckle-server` | by hand on isa ([`bootstrap/README.md`](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/README.md)) | `api:buckle-api`, `api:buckle-agent-api` ([`modules/buckle-server/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/buckle-server/catalog-info.yaml)) |
| `svc:nut` | admin console | `approve-nut`: `tag:nut-server` | [`modules/nut-server`](https://github.com/SpechtLabs/homelab/blob/main/modules/nut-server/module.yaml) | `api:nut` |
| `svc:nas`, `svc:stream`, `svc:node-exporter`, `svc:nfs` | admin console | `approve-nas`: `tag:nas` | by hand on the NAS ([`nas/README.md`](https://github.com/SpechtLabs/homelab/blob/main/nas/README.md)) | [`nas/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/nas/catalog-info.yaml) |
| `svc:hass` | admin console | `approve-hass`: `tag:hass-server` (plus `tag:smarthome` during the change-over) | the Home Assistant Tailscale add-on | `api:home-assistant-api` ([`catalog/home-assistant.yaml`](https://github.com/SpechtLabs/homelab/blob/main/catalog/home-assistant.yaml)) |
| `svc:labk3s` | admin console | `approve-labk3s`: `tag:k3s-server` | [`modules/k3s-server`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-server/module.yaml) | `api:labk3s-kubernetes-api` |
| `svc:lgtm`, `svc:argocd`, `svc:backstage` | the operator, from the Kubernetes Service | `approve-specht-labs-ingress`: `tag:specht-labs-ingress` | [`tailnet-services.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/envoy-gateway/cluster/specht-labs/tailnet-services.yaml) | `api:loki-push`, `mimir-remote-write`, `tempo-otlp`, `argocd-api`, `backstage-web` |
| `svc:labk3s-argocd-api`, `svc:lab-argocd` | the operator | `approve-labk3s-ingress`: `tag:labk3s-ingress` | [`argocd-api-tailnet.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/argocd/cluster/labk3s/argocd-api-tailnet.yaml), the `argocd-server` Ingress | `api:argocd-labk3s-api`, `api:argocd-labk3s-web` |

Auto approvers are in [`tailscale/policy/auto-approvers.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/auto-approvers.yaml).

## Behaviour per host

- isa, clusterpi-leader and hass-elbschloss (Tailscale 1.104.x) keep a
  Service's unserved ports closed.
- The NAS (Tailscale 1.98.4, DSM's package) passes every port of a Service
  address through to the device: `nas.<tailnet>:8096` reaches Jellyfin.
  Grants to its Services list ports. On the NAS, `tailscale serve status`
  prints "No serve config"; `serve get-config --all` shows the Services.
- `svc:nas` has no port 80.
- The specht-labs Services map only the VIP's IPv4 address (the cluster is
  IPv4-only), so their DNS records are A records only.
