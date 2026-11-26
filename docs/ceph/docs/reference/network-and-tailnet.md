# Network and tailnet

Everything Ceph speaks binds to the hosts' tailnet addresses (`public_network = 100.64.0.0/10`, Tailscale's CGNAT range). There's no cluster network and no LAN path.

## Ports

| Port | Daemon | Bound to | Who reaches it |
|---|---|---|---|
| tcp 22 | sshd (and Tailscale SSH on the tailnet address) | all | admins, jumphost, `group:sre` (SSH policy) |
| tcp 2222 | sshd for cephadm, root only, cephadm's key only, `from=100.64.0.0/10` | all | `tag:ceph` |
| tcp 3300 | mon, msgr v2 | tailnet IP | `tag:ceph`, `tag:ceph-client` |
| tcp 6789 | mon, msgr v1 | tailnet IP | `tag:ceph`, `tag:ceph-client` |
| tcp 6800-7568 | OSDs and mgr (`ms_bind_port_max` 7568) | tailnet IP | `tag:ceph`, `tag:ceph-client`, both except 7480 |
| tcp 7480 | RGW (S3), storagepi-ceph2 only | all | admins only |
| tcp 8443 | mgr dashboard (active mgr) | all | admins only |
| tcp 9283 | mgr prometheus module | all | the host's own Alloy (local scrape) |
| tcp 9926 | ceph-exporter | all | the host's own Alloy (local scrape) |
| tcp 8765 | mgr (cephadm's service discovery endpoint) | | admins only |

An OSD on storagepi-ceph1 used 6800-6807 on 2026-11-26 (`ss -ltnp`). RGW's 7480 sits inside the OSD range, which is why every grant splits the range into 6800-7479 and 7481-7568; the policy test caught it.

## Tailnet grants

The policy is rendered by Backstage from the catalog; don't edit [`tailscale/policy.hujson`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy.hujson) by hand ([Tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)). The Ceph grants come from the APIs' annotations in [`modules/ceph/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/catalog-info.yaml):

| Grant | Ports | From |
|---|---|---|
| `tag:ceph` to `tag:ceph` | tcp:2222, 3300, 6789, 6800-7479, 7481-7568 | API `ceph-cluster` (consumed by component `ceph`, `tailnet-src: tag:ceph`) |
| `tag:ceph-client` to `tag:ceph` | tcp:3300, 6789, 6800-7479, 7481-7568 | API `ceph-rbd` (consumed by `ceph-csi-rbd` in k8s-deployment, `tailnet-src: tag:ceph-client`) |
| `group:admins` to `*` | everything | the general admin grant |

The policy test `test-ceph` ([`tailscale/policy/tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tests.yaml)) checks: `tag:ceph` reaches `tag:ceph` on 2222, 3300, 6789, 6800 and 7568; `tag:ceph-client` reaches 3300, 6789, 6800 and 7568 and is denied 2222, 8443, 7480 and 9283. Another test denies `tag:compute-blade` the mons on 6789.

SSH: admins and the jumphost reach `tag:ceph` as any user including root; `group:sre` as non-root, and as root in check mode (8 h).

## Tags

| Tag | Owner | Carried by |
|---|---|---|
| `tag:ceph` | `group:admins` | storagepi-ceph1, -ceph2, -ceph3 |
| `tag:ceph-client` | `group:admins` | clusterpi-leader, clusterpi-worker1..4 (labk3s) |

Defined in [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml); the devices get them in the Tailscale admin console.

## Names and routing

- cephadm reaches the hosts as `<host>.sphinx-map.ts.net` on port 2222 (host specs in [`cluster.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/files/cluster.yaml.j2), SSH config in [`files/ssh_config`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/files/ssh_config)).
- ceph-csi on labk3s lists the mons by IP (`100.105.212.35:6789`, `100.107.71.68:6789`, `100.118.224.54:6789`) in [`helm-values.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/ceph-csi-rbd/cluster/labk3s/helm-values.yaml), and follows the monmap after that.
- Each host has a main-table route `<own tailnet IP>/32 dev tailscale0 scope link src <own tailnet IP>` from `ceph-tailnet-route.service`, so cephadm sees the address in `public_network`. Buckle's health check `tailnet-route` checks it.
- S3: `http://storagepi-ceph2.sphinx-map.ts.net:7480`.
