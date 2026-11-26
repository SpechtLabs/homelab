# Tags

The 24 tags in the policy (`tagOwners`), from
[`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml).
"Carried by" is from `tailscale status --json` on 2026-11-26; check it again
with `tailscale status --json | jq -r '.Peer[] | select(.Tags) | [.HostName, (.Tags|join(","))] | @tsv'`.

## Attribute tags: what a device is or does

| Tag | Owners | Carried by | Used as |
|---|---|---|---|
| `tag:buckle-agent` | admins | all 17 Buckle hosts: blade-pi1..4, clusterpi-leader, clusterpi-worker1..4, storagepi-ceph1..3, isa, jumphost, meet, nuc, timepi | source for `svc:buckle` 7700, `svc:nut`, `svc:lgtm`; SSH destination |
| `tag:ceph` | admins | storagepi-ceph1..3 | Ceph mesh (source and destination) |
| `tag:ceph-client` | admins | clusterpi-leader, clusterpi-worker1..4 | source to `tag:ceph` (ceph-csi) |
| `tag:k3s-node` | admins | clusterpi-leader, clusterpi-worker1..4 | labk3s node mesh, source for `svc:labk3s`; SSH destination |
| `tag:compute-blade` | admins | blade-pi1..4 | SSH destination |
| `tag:smarthome` | admins | hass-elbschloss, hass-schiltach | source for `svc:lgtm`; SSH destination; web UI (5252) destination; approver of `svc:hass` |
| `tag:o11y-collector` | admins | isa | source: scrapes and probes through Services |
| `tag:o11y-agent` | admins | meet, monitoring-lab-lgtm-egress, hass-elbschloss | source for `svc:lgtm` |
| `tag:tsidp-client` | admins, `tag:k8s-operator`, `tag:k3s-operator` | isa, nas-elbschloss, tailscale-k3s-idp-egress | source to `tag:tsidp` (relying parties) |
| `tag:backstage` | admins, `tag:k8s-operator` | backstage-lab-argocd (Backstage's egress proxy) | source for `svc:labk3s-argocd-api` |
| `tag:jumphost` | admins | jumphost | SSH source |
| `tag:tsidp` | admins | idp | capability target; Funnel |
| `tag:tka` | `tag:k8s-operator`, admins | tka, lab-tka | capability target (tcp:8123) |
| `tag:opencode` | admins | no device today | in no rule |

## Service host tags: who may serve a Service

Each is the only auto approver of its Services. Owned by admins only, so
neither Kubernetes operator can hand it to a proxy; the two ingress tags are
the exception, because their operator mints the proxies' keys.

| Tag | Owners | Carried by | Serves |
|---|---|---|---|
| `tag:buckle-server` | admins | isa | `svc:buckle` (also a source: `svc:nfs`) |
| `tag:nut-server` | admins | isa | `svc:nut` |
| `tag:nas` | admins | nas-elbschloss | `svc:nas`, `svc:stream`, `svc:node-exporter`, `svc:nfs` |
| `tag:k3s-server` | admins | clusterpi-leader | `svc:labk3s` |
| `tag:specht-labs-ingress` | admins, `tag:k8s-operator` | specht-labs-ingress-0, -1 | `svc:lgtm`, `svc:argocd`, `svc:backstage` |
| `tag:labk3s-ingress` | admins, `tag:k3s-operator` | labk3s-ingress-0, -1 | `svc:labk3s-argocd-api`, `svc:lab-argocd` |

`svc:hass` is approved for `tag:smarthome`, which both Home Assistant boxes
carry, not a host tag of its own.

## Operator tags

| Tag | Owners | Carried by | What |
|---|---|---|---|
| `tag:k8s-operator` | admins | tailscale-operator (specht-labs) | the operator itself; may enable Funnel |
| `tag:k3s-operator` | admins | lab-tailscale-operator (labk3s) | the operator itself; may enable Funnel |
| `tag:k8s` | `tag:k8s-operator` | the specht-labs operator's default proxy tag; on the Tailscale Services `svc:lgtm`, `svc:argocd`, `svc:backstage` | in no grant |
| `tag:k3s` | `tag:k3s-operator` | the labk3s operator's default (`PROXY_TAGS`); on `svc:labk3s-argocd-api`, `svc:lab-argocd` | in no grant |

## Retired

`tag:core-services`, `tag:core-infra`, `tag:homelab`, `tag:o11y-endpoint` and
`tag:lab-argocd` are gone from the policy and from every device
([History](../explanation/history.md)).
