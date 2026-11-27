# Tour the cluster

Every command here only reads, so you can run them at any time. By the end you'll have seen the nodes, the path the API takes over the tailnet, what Argo CD deploys and where the alerts live. Allow about 15 minutes.

You need a Mac on the tailnet as a member of `group:admins` and the admin kubeconfig at `~/.kube/configs/labk3s` (see [Get kubectl access](../how-to/get-kubectl-access.md) if you don't have it yet).

## 1. Point kubectl at labk3s

Open a terminal **outside** `~/src/gh/SpechtLabs/k8s-deployment` (that repo's mise config points `KUBECONFIG` at the specht-labs cluster) and run:

```sh
export KUBECONFIG=~/.kube/configs/labk3s
kubectl --context labk3s config view --minify -o jsonpath='{.clusters[0].cluster.server}{"\n"}'
```

You should see `https://labk3s.sphinx-map.ts.net:6443`. That name is the Tailscale Service `svc:labk3s`, not a machine.

## 2. Look at the nodes

```sh
kubectl --context labk3s get nodes -o wide
```

Five nodes, all `Ready`. The `INTERNAL-IP` column shows `100.x` addresses: each node registered with its tailnet IPv4, which is what puts the cluster on the tailnet. `clusterpi-leader` has the roles `control-plane,master`; the four workers have none.

## 3. Follow the API through the Service

```sh
dig +short labk3s.sphinx-map.ts.net
kubectl --context labk3s get endpointslices -n default -l kubernetes.io/service-name=kubernetes
```

Both show `100.67.145.122`. The first is MagicDNS answering for the Service; the second is the address the cluster itself advertises for the `kubernetes` Service. They match because the server's `advertise-address` is set to the Service's VIP, so pods and the workers' agents also reach the API through `svc:labk3s`. [k3s over the tailnet](../explanation/k3s-over-the-tailnet.md) explains why.

## 4. See what Argo CD runs

```sh
kubectl --context labk3s -n argocd get applications
```

You'll see `1-meta-labk3s` (the root, owned by Buckle) and one Application per file in k8s-deployment's [`argo-apps/labk3s/`](https://github.com/SpechtLabs/k8s-deployment/tree/main/argo-apps/labk3s): `argocd`, `ceph-csi-rbd`, `cert-manager`, `coredns`, `grafana-k8s-monitoring`, `tailscale`, `tka`. Now open the same list in a browser at <https://lab-argocd.sphinx-map.ts.net> and sign in with **Tailscale** (tsidp).

## 5. Find the tailnet ingress

```sh
kubectl --context labk3s get proxygroup
kubectl --context labk3s -n tailscale get pods -o wide
```

`tailnet-ingress` should be `ProxyGroupReady`, with pods `tailnet-ingress-0` and `-1` on different workers. Those two pods serve `svc:lab-argocd`, the UI you just opened.

## 6. Check storage

```sh
kubectl --context labk3s get storageclass
kubectl --context labk3s -n ceph-csi-rbd get pods -o wide
```

`ceph-rbd` is the Ceph-backed class and the default, so a PVC that names no class lands on Ceph. `local-path` (a directory on one node's disk) is still there for TKA's state. The node plugin runs one pod per node in the host network, which is why its pod IPs are the nodes' tailnet addresses.

## 7. Find the alerts

In Grafana (<https://spechtlabs.grafana.net>), open **Alerting > Alert rules** and search for `labk3s`. You'll find the cluster's own group `labk3s-platform` (nodes, pods, volumes, Argo CD apps, telemetry) under *Infrastructure > Kubernetes Platform*, the burn-rate alerts of the SLO *Homelab — labk3s API availability*, and the four `Ceph CSI —` rules under *Infrastructure > Ceph*. [Alerts and dashboards](../reference/alerts-and-dashboards.md) lists them all.

## Where next

You've now touched every layer: the Pis and k3s (Buckle), the API Service (tailnet), the apps (Argo CD) and storage (Ceph). When you need to change one of them, start from [How-to guides](../how-to/index.md).
