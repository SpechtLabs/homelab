# Alerts and dashboards

Grafana is Grafana Cloud at <https://spechtlabs.grafana.net>. It evaluates rules against the self-hosted Mimir tenant `mimir-homelab`, where labk3s's Alloy writes with `cluster="labk3s"`. All rules, the SLO and the dashboards are code in SpechtLabs/k8s-deployment under [`apps/grafana-operator/cluster/specht-labs/`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/grafana-operator/cluster/specht-labs); edits made in the UI get overwritten. A rule with `severity: critical` pages, anything else notifies.

## SLO

| SLO | Objective | Measures | File |
|---|---|---|---|
| *Homelab — labk3s API availability* (`hlk3sapiavail`) | 99.5 % over 28 d | `probe_success{job="blackbox", service="labk3s-api"}`: isa's blackbox probe of `https://labk3s.sphinx-map.ts.net:6443/readyz` every 30 s, module `http_401_insecure` (a `401` counts as up) | [`slos/homelab-labk3s-api-availability.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/slos/homelab-labk3s-api-availability.yaml) |

Its generated alerts, in the folder *Grafana SLO*:

| Alert | Severity |
|---|---|
| Homelab — labk3s API availability - Error Budget Burn Rate is Very High | critical (fast burn) |
| Homelab — labk3s API availability - Error Budget Burn Rate is High | warning (slow burn) |

The probe itself is defined in this repo: `o11y_probes` in [`vars/group-o11y-collector.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-o11y-collector.yaml).

## Alert rules

Group `ceph-health`, folder *Infrastructure > Ceph*, label `service: ceph-csi`, in [`grafanaalertrules-ceph.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ceph.yaml):

| Rule | For | Severity | Fires when |
|---|---|---|---|
| Ceph CSI — no provisioner | 5m | critical | `sum(csi_liveness{cluster="labk3s", job="ceph-csi-rbd/provisioner"})` is below 1 |
| Ceph CSI — node plugin missing | 10m | warning | fewer live node plugins than `kube_node_info{cluster="labk3s"}` nodes |
| Ceph CSI — volume operations failing | 15m | warning | CSI sidecar operations return a non-OK gRPC status |
| Ceph CSI — PVC over 85% full | 15m | warning | a `ceph-rbd` PVC uses more than 85 % of its capacity |

What to do: [Respond to a labk3s alert](../how-to/respond-to-a-labk3s-alert.md).

Not covered on labk3s: the rules in `grafanaalertrules-platform.yaml` (*Node NotReady*, *Pod restarting repeatedly*, *Volume almost full*, *ArgoCD app unhealthy*, ...) query `mimir-spechtlabs` and the specht-labs cluster only.

## Dashboards

| Dashboard | Folder | UID | Shows |
|---|---|---|---|
| [Ceph CSI (RBD)](https://spechtlabs.grafana.net/d/ceph-csi-rbd) | Infrastructure > Ceph | `ceph-csi-rbd` | driver health, CSI operations, PVC usage, the `k3s` pool |
| Raspberry Pi Fleet | Infrastructure > Providers | `be3ouz53blwqoc` | the Pis' hardware, including the five cluster nodes |

Logs from pods and nodes are in Loki (tenant `homelab`), filtered by `cluster="labk3s"`.

## In Buckle

Each node's page in the Buckle UI (<https://buckle.sphinx-map.ts.net>) shows its health checks live; the list is in [k3s configuration](k3s-configuration.md#health-checks).
