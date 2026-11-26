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

k3s ships CoreDNS, metrics-server, local-path-provisioner (the default StorageClass `local-path`) and its manifests under `/var/lib/rancher/k3s/server/manifests`; Traefik is off.

## Nobody (yet)

These namespaces exist on labk3s but no Application in `argo-apps/labk3s/` deploys them: `capi-system`, `chaos-mesh`, `gossip`, `observability`, `opentelemetry-operator-system`, `tka-dev` (seen 2026-11-26). Leftovers from before; check before relying on or deleting anything there.
