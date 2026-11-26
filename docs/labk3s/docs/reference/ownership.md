# Who owns what

No object has two managers. If you change something in the wrong place, the owner writes it back.

## Buckle (this repo)

| What | Where |
|---|---|
| k3s binary, config, units, sysctls on all five nodes | `modules/k3s-server`, `modules/k3s-agent` |
| `svc:labk3s` served from the leader | `modules/k3s-server`, task `svc-k3s` |
| Argo CD's first install, only on a cluster without `argocd-server` | `modules/argocd-seed` |
| The root Application `argocd/1-meta-labk3s` | [`workloads/argocd-root/files/1-meta-labk3s.yaml`](https://github.com/SpechtLabs/homelab/blob/main/workloads/argocd-root/files/1-meta-labk3s.yaml) |

`1-meta-labk3s` syncs `argo-apps/labk3s` from k8s-deployment `main` with `prune` and `selfHeal`. It carries `argocd.argoproj.io/sync-options: Prune=false`, so Argo CD never prunes it, and the workload has `removal: keep`, so dropping it from Buckle never deletes it.

## Argo CD (SpechtLabs/k8s-deployment)

Every Application below lives in `argo-apps/labk3s/<name>.yaml`, renders `apps/<name>/cluster/labk3s`, tracks `main` and has `automated: { prune: true, selfHeal: true }`.

| Application | Namespace | What |
|---|---|---|
| `argocd` | `argocd` | Argo CD itself (chart `argo-cd` 10.20.0), Dex to tsidp, the `lab-argocd` Ingress and `argocd-server-tailnet-svc` |
| `ceph-csi-rbd` | `ceph-csi-rbd` | ceph-csi 3.18.2, StorageClass `ceph-rbd` (pool `k3s`, `client.k3s`) |
| `cert-manager` | `cert-manager` | cert-manager |
| `coredns` | `kube-system` | only `coredns-custom`: the `ts.net` forward. CoreDNS itself is k3s's bundled one |
| `grafana-k8s-monitoring` | `monitoring` | Alloy, kube-state-metrics, node-exporter, shipping to `svc:lgtm` (tenant `homelab`, `cluster="labk3s"`) |
| `tailscale` | `tailscale` | Tailscale operator 1.104.7 (`lab-tailscale-operator`), ProxyGroup `tailnet-ingress`, egress `k3s-idp-egress`, nameserver |
| `tka` | `tka-system` | TKA (`lab-tka`) |

Chart versions as of 2026-11-26; they're pinned in each `kustomization.yaml` and Renovate bumps them.

## k3s itself

k3s ships CoreDNS, metrics-server and local-path-provisioner, with manifests under `/var/lib/rancher/k3s/server/manifests`; Traefik is off. The bundled StorageClass `local-path` is the cluster's **default**, so a PVC without `storageClassName` lands in a directory on one node's root filesystem. `ceph-rbd` must be named explicitly. As of 2026-11-27 the only PVCs are TKA's two `tsnet-state` volumes, both `local-path`.

## Nobody (yet)

No Application in `argo-apps/labk3s/` deploys these, and nothing else in either repo does. Contents as of 2026-11-27:

| Namespace | What's in it | Cluster-wide leftovers |
|---|---|---|
| `capi-system` | Deployment `capi-controller-manager` (cluster-api v1.13.2), its webhook Service and cert (cert-manager `Certificate capi-serving-cert`); no `Cluster` objects anywhere | cluster-api, CAPH and kubeadm CRDs; validating and mutating webhooks for `capi`, `capi-kubeadm-bootstrap`, `capi-kubeadm-control-plane` and `caph`, whose `caph-system` and `capi-kubeadm-*-system` Services no longer exist (`failurePolicy: Fail`, scoped to those CRDs) |
| `chaos-mesh` | Chaos Mesh v2.7.0: controller-manager (3), dashboard, DNS server, `chaos-daemon` DaemonSet on all nodes | Chaos Mesh CRDs and webhooks; a `NetworkChaos` `gossip/test1` (partition, 2024-11-03, stopped) |
| `gossip` | DaemonSet `gossip-testing` (`ghcr.io/cedi/gossip-experiment:main`) on all five nodes, Service `gossip` | |
| `observability` | nothing but `kube-root-ca.crt` | |
| `opentelemetry-operator-system` | only the operator's webhook cert Secret | OpenTelemetry operator CRDs |
| `tka-dev` | nothing but `kube-root-ca.crt` | |

None has a PVC or a secret beyond webhook certificates. They're experiments from before the cluster was GitOps-managed; nothing on labk3s depends on them.
