# Catalog annotations

The annotations Backstage's tailnet plugin reads
([`graph.ts`](https://github.com/SpechtLabs/backstage-plugin-tailscale/blob/main/plugins/tailscale-backend/src/graph.ts),
[`model.ts`](https://github.com/SpechtLabs/backstage-plugin-tailscale/blob/main/plugins/tailscale-common/src/model.ts)).

## On an API

| Annotation | Value | Says | Rules |
|---|---|---|---|
| `specht-labs.de/tailnet-dst` | comma-separated `svc:<name>` or `tag:<name>` | where tailnet consumers reach the API | required once any of the four is set; nothing but `svc:` and `tag:` |
| `specht-labs.de/tailnet-ports` | comma-separated ports: `tcp:443`, `udp:8472`, `tcp:6800-7479` | on which ports | required next to `tailnet-dst`; concrete ports, no `*` |
| `specht-labs.de/tailnet-allow` | comma-separated `group:`, `user:`, `autogroup:`, `tag:` entries, or a login | who else may use it: people, and devices that aren't Components | optional |
| `specht-labs.de/tailnet-client-tag` | one `tag:` | the tag every consumer reaches it as, replacing the consumers' own `tailnet-src` | optional; used once: `tag:tsidp-client` on `api:tsidp-oidc` |

## On a Component

| Annotation | Value | Says |
|---|---|---|
| `specht-labs.de/tailnet-src` | comma-separated `tag:` entries | the tags its traffic comes from: its host's, or its egress proxy's |

## On a Group or User (SpechtLabs/backstage_resources)

| Annotation | On | Value |
|---|---|---|
| `specht-labs.de/tailnet-group` | Group | the policy group it is, `group:admins` |
| `specht-labs.de/tailnet-login` | User | the Tailscale login, `cedi@github` |

## On a Tailscale tag entity

| Annotation | Says |
|---|---|
| `specht-labs.de/tailnet-device-reason` | why grants reach devices with this tag rather than a Service. Silences the "reached as a device" warning. No tag uses it today: the device destinations are all peer meshes, capability targets or autogroups. |

## Where they're set today

| API | `tailnet-dst` | Ports | `tailnet-allow` | File |
|---|---|---|---|---|
| `buckle-api` | `svc:buckle` | tcp:443 | group:admins, group:sre | homelab `modules/buckle-server/catalog-info.yaml` |
| `buckle-agent-api` | `svc:buckle` | tcp:7700 | | same |
| `nut` | `svc:nut` | tcp:3493 | | homelab `modules/nut-server/catalog-info.yaml` |
| `synology-dsm-web` | `svc:nas` | tcp:443 | group:synology-users | homelab `nas/catalog-info.yaml` |
| `synology-dsm-https` | `svc:nas` | tcp:5001 | group:synology-users | same |
| `synology-drive` | `svc:nas` | tcp:6690 | group:synology-users | same |
| `jellyfin-web` | `svc:stream` | tcp:443 | group:synology-users | same |
| `nas-nfs` | `svc:nfs` | tcp:2049 | | same |
| `nas-node-exporter` | `svc:node-exporter` | tcp:9100 | | same |
| `home-assistant-api` | `svc:hass` | tcp:443, tcp:8123 | group:hass-users | homelab `catalog/home-assistant.yaml` |
| `labk3s-kubernetes-api` | `svc:labk3s` | tcp:6443 | group:admins | homelab `modules/k3s-server/catalog-info.yaml` |
| `labk3s-node-mesh` | `tag:k3s-node` | udp:8472, tcp:10250, tcp:8681 | | same |
| `ceph-rbd` | `tag:ceph` | tcp:3300, 6789, 6800-7479, 7481-7568 | | homelab `modules/ceph/catalog-info.yaml` |
| `ceph-cluster` | `tag:ceph` | tcp:2222 plus the `ceph-rbd` ports | | same |
| `tsidp-oidc` | `tag:tsidp` | tcp:443 | autogroup:member (client tag `tag:tsidp-client`) | homelab `modules/tsidp/catalog-info.yaml` |
| `loki-push`, `mimir-remote-write`, `tempo-otlp` | `svc:lgtm` | tcp:80 | | k8s-deployment `apps/{loki,mimir,tempo}/cluster/specht-labs/catalog-info.yaml` |
| `argocd-api` | `svc:argocd` | tcp:443 | group:admins | k8s-deployment `apps/argocd/cluster/specht-labs/catalog-info.yaml` |
| `backstage-web` | `svc:backstage` | tcp:443 | group:admins | k8s-deployment `apps/backstage/cluster/specht-labs/catalog-info.yaml` |
| `argocd-labk3s-api` | `svc:labk3s-argocd-api` | tcp:443 | | k8s-deployment `apps/argocd/cluster/labk3s/catalog-info.yaml` |
| `argocd-labk3s-web` | `svc:lab-argocd` | tcp:443 | group:admins, group:sre | same |

Components with `tailnet-src`: in homelab `alloy`, `buckle-agent` and
`nut-client` (`tag:buckle-agent`), `o11y-collector` (`tag:o11y-collector`),
`buckle-server` (`tag:buckle-server`), `ceph` (`tag:ceph`), `k3s-server`
and `k3s-agent` (`tag:k3s-node`), `home-assistant` and
`home-assistant-schiltach` (`tag:smarthome`); in
k8s-deployment `backstage` (`tag:backstage`), `ceph-csi-rbd`
(`tag:ceph-client`), `grafana-k8s-monitoring-labk3s` (`tag:o11y-agent`).
Find them all with `git grep -n 'specht-labs.de/tailnet'` in both repos.
