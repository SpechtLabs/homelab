# Addresses, ports and Services

The tailnet is `sphinx-map.ts.net`. Grants live in [`tailscale/policy.hujson`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy.hujson), rendered by Backstage from the catalog.

## Tailscale Services

| Service | Name | VIP (2026-11-26) | Ports | Served by | Who may reach it |
|---|---|---|---|---|---|
| `svc:labk3s` | `labk3s.sphinx-map.ts.net` | 100.67.145.122 | tcp:6443 (passed through, k3s terminates TLS) | `clusterpi-leader` (`tailscale serve`, task `svc-k3s` in `modules/k3s-server`) | `group:admins`, `tag:o11y-collector` (isa's probe), `tag:k3s-node` |
| `svc:lab-argocd` | `lab-argocd.sphinx-map.ts.net` | 100.112.213.104 | tcp:443 (Tailscale terminates TLS) | ProxyGroup `tailnet-ingress` (Ingress `argocd/argocd-server`) | `group:admins`, `group:sre` |
| `svc:labk3s-argocd-api` | `labk3s-argocd-api.sphinx-map.ts.net` | 100.126.137.0 | tcp:443 (argocd-server terminates TLS) | ProxyGroup `tailnet-ingress` (Service `argocd/argocd-server-tailnet-svc`) | `tag:backstage` |

Admins also have a grant to `*` on every port, so they reach all of these and the nodes directly.

`svc:labk3s`'s VIP is also the API's `advertise-address` (`k3s_service_ip`), so the in-cluster `kubernetes` endpoint is `100.67.145.122:6443`. Each Service has one autoApprover: `tag:k3s-server` for `svc:labk3s`, `tag:labk3s-ingress` for the other two.

## Between the nodes

Every node is a peer on its own tailnet address (`tag:k3s-node` to `tag:k3s-node`):

| Port | What |
|---|---|
| udp 8472 | flannel VXLAN, the pod network (`flannel.1` on `tailscale0`, MTU 1230) |
| tcp 10250 | kubelet API: `exec`, `logs`, metrics-server, Alloy's scrapes |
| tcp 8681 | ceph-csi-rbd node plugin metrics (hostNetwork) |

`tag:k3s-node` reaches the API only through `svc:labk3s`: a policy test denies `tag:k3s-node` to `tag:k3s-server:6443`.

## Other devices from the cluster

| Device | Tag | What for |
|---|---|---|
| `labk3s-ingress-0`, `labk3s-ingress-1` | `tag:labk3s-ingress` | the ProxyGroup replicas |
| `lab-tailscale-operator` | `tag:k3s-operator` | the Tailscale operator |
| `lab-tka` | `tag:tka` | TKA on tcp:8123; admins get `cluster-admin` for 1 h through the capability grant `specht-labs.de/cap/tka` |
| `tailscale-k3s-idp-egress` | `tag:tsidp-client` | egress to tsidp (`idp.sphinx-map.ts.net`) for Argo CD's Dex |
| `monitoring-lab-lgtm-egress` | `tag:o11y-agent` | egress to `svc:lgtm`, where Alloy ships metrics, logs and traces |

Tags on operator proxies are set only when the proxy is first created. To retag one, change the annotation, then delete the k8s Service and let Argo CD re-create it.

## Ceph

The nodes are Ceph clients (`tag:ceph-client` to `tag:ceph`, tcp 3300, 6789, 6800-7479, 7481-7568). ceph-csi lists the mons by tailnet address: 100.105.212.35, 100.107.71.68, 100.118.224.54 (`storagepi-ceph1..3`), port 6789, in [`helm-values.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/ceph-csi-rbd/cluster/labk3s/helm-values.yaml).

## Inside the cluster

| What | Value |
|---|---|
| Pod CIDR | 10.42.0.0/16 (k3s default), a /24 per node: leader 10.42.0.0, worker1 10.42.6.0, worker2 10.42.3.0, worker3 10.42.4.0, worker4 10.42.1.0 |
| Service CIDR | 10.43.0.0/16 (k3s default; `kubernetes` is 10.43.0.1) |
| CoreDNS `ts.net` forward | to `10.43.37.229`, the ClusterIP of Service `tailscale/nameserver`: in [`coredns-custom.cm.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/coredns/cluster/labk3s/coredns-custom.cm.yaml), and pinned on the Service by the DNSConfig's `nameserver.service.clusterIP` ([`dns-config.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/tailscale/cluster/labk3s/dns-config.yaml)); change both together |

In-cluster lookups of `*.ts.net` resolve to the operator's egress proxies, not to raw `100.x` addresses. Pods still reach `100.x` addresses directly through their node.
