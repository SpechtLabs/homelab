# Nodes

| Node | Hardware | Role | Buckle group | Tailnet tags | Tailnet IPv4 |
|---|---|---|---|---|---|
| `clusterpi-leader` | Raspberry Pi 5 (8 GB) | server (`control-plane,master`) | `k3s-server` | `tag:buckle-agent`, `tag:ceph-client`, `tag:k3s-node`, `tag:k3s-server` | 100.92.89.43 |
| `clusterpi-worker1` | Raspberry Pi 4 Model B (8 GB) | agent | `k3s-agent` | `tag:buckle-agent`, `tag:ceph-client`, `tag:k3s-node` | 100.94.152.81 |
| `clusterpi-worker2` | Raspberry Pi 4 Model B | agent | `k3s-agent` | same as worker1 | 100.123.236.103 |
| `clusterpi-worker3` | Raspberry Pi 4 Model B | agent | `k3s-agent` | same as worker1 | 100.126.248.78 |
| `clusterpi-worker4` | Raspberry Pi 4 Model B | agent | `k3s-agent` | same as worker1 | 100.103.254.83 |

Hardware from [`catalog/hardware.yaml`](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml); groups from [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml) (`host.id == "clusterpi-leader"`, `host.id like "clusterpi-worker*"`); tags and addresses as `tailscale status` showed them on 2026-11-26. Addresses are the nodes' `INTERNAL-IP`; the source of truth is `kubectl --context labk3s get nodes -o wide` or the admin console.

As of 2026-11-26 every node ran k3s `v1.37.2+k3s1` on Debian 12 (bookworm), kernel `6.12.115`, containerd `2.3.7-k3s1`. The k3s version comes from `k3s_version`; the kernel from the nightly upgrades.

## Login

SSH as `pi@<node>` over Tailscale SSH; the login shell is fish, so wrap POSIX commands in `bash -c '...'`. `group:admins` and the jumphost may log in as any user including root; `group:sre` as non-root, and as root in check mode (re-authenticate every 8 h).

## Buckle actions on the nodes

| Action | Where | What |
|---|---|---|
| `k3s-agent: reboot` | workers | Reboot, `delay: 5s`, `timeout: 10m`, asks for a note |
| `base: reboot` | every host | Same, for any host |
| `base: upgrade` | every host | `apt upgrade` with autoremove, reboots if required |
| `base: reboot-if-required` | every host | Reboots only when a newer kernel is installed but not running |

Run from the host's page in the Buckle UI, they don't drain the node (see [Drain and reboot a node](../how-to/drain-and-reboot-a-node.md)).
