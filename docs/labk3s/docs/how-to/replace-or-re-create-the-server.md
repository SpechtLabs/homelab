# Replace or re-create the server

Use this when `clusterpi-leader` is dead or has to move to new hardware. Read all of it first: the repo covers bringing k3s and Argo CD up on a server, not carrying the old cluster's state over.

**Before you start:** labk3s has a single server with the SQLite (kine) datastore under `/var/lib/rancher/k3s` on `clusterpi-leader`. Nothing in this repo or k8s-deployment backs that up. If the old disk is readable, everything below is easier with it; if it isn't, you're building a new cluster that happens to have the same name.

## What the repo does for you

The `k3s-server` group is `host.id == "clusterpi-leader"`, so a Pi enrolled under that tailnet name gets, on its first rollout:

- k3s at `k3s_version`, with `/etc/rancher/k3s/config.yaml` from [`config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-server/files/config.yaml.j2): the same `K3S_TOKEN`, `node-ip` = its own tailnet IPv4, `advertise-address` = `k3s_service_ip`, `tls-san` = `labk3s.sphinx-map.ts.net`;
- `tailscale serve --service=svc:labk3s --tcp=6443 tcp://localhost:6443`, which takes over `svc:labk3s` once the device carries `tag:k3s-server` (the Service's only autoApprover). The VIP belongs to the Service and stays `100.67.145.122`; the `svc-ip` check confirms it;
- on an API with no `argocd-server` Deployment, `argocd-seed` renders k8s-deployment's `apps/argocd/cluster/labk3s` with ksops and `ARGOCD_AGE_KEY` and applies it, once;
- the root Application `1-meta-labk3s` from `workloads/argocd-root`, after which Argo CD deploys every app in `argo-apps/labk3s/`.

## Steps

1. Give the new Pi the tailnet name `clusterpi-leader` and the tags `tag:buckle-agent`, `tag:k3s-node`, `tag:ceph-client` and `tag:k3s-server` (admin console). The old device has to be gone first: two devices can't hold the same name.
2. Enrol it in Buckle ([fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/)) and let the rollout run. The `k3s-server` checks `unit`, `kubelet`, `apiserver`, then `svc-api` and `svc-ip`, should pass; `argocd-server` reports when Argo CD serves.
3. Refresh your admin kubeconfig ([Get kubectl access](get-kubectl-access.md)): a new datastore means a new CA and new client certificates.

!!! warning "Unverified: everything after a fresh datastore"
    None of this has been done on labk3s. From the config, expect at least these to break and need fixing by hand:

    - **The workers.** They hold the old cluster's CA and node credentials under `/var/lib/rancher/k3s/agent`. Whether they rejoin with the same `K3S_TOKEN` or need a [reset](reset-k3s.md) first isn't known.
    - **In-cluster `*.ts.net` lookups.** [`coredns-custom.cm.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/coredns/cluster/labk3s/coredns-custom.cm.yaml) forwards `ts.net` to the Tailscale nameserver's ClusterIP, pinned as `10.43.37.229`. A new cluster allocates a new one; update the ConfigMap.
    - **TKA.** `caData` and `apiEndpoint` in [`tka-config.patch.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/tka/cluster/labk3s/tka-config.patch.yaml) are the old cluster's CA and `https://clusterpi-leader:6443`.
    - **Backstage's Argo CD cards.** The labk3s `backstage` account's token (`ARGOCD_LABK3S_TOKEN`, `apps/backstage/cluster/specht-labs/argocd.secret.yaml` in k8s-deployment) belongs to the old Argo CD.
    - **The Tailscale operator's devices.** Its proxies' state lived in Secrets in the old cluster. New proxies join as new devices; whether `svc:lab-argocd` and `svc:labk3s-argocd-api` keep their VIPs isn't known.
    - **Volumes.** The RBD images stay in Ceph's `k3s` pool, but the PV objects that pointed at them are gone, and `ceph-rbd` has `reclaimPolicy: Delete`.

## Check it worked

```sh
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s get nodes
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s -n argocd get applications
```

All nodes `Ready`, every Application `Synced` and `Healthy`, and the SLO probe (`labk3s-api`) green again.

## If it didn't

Look at the server's checks in Buckle first, then `journalctl -u k3s` on it. [Respond to a labk3s alert](respond-to-a-labk3s-alert.md) walks the API path layer by layer.
