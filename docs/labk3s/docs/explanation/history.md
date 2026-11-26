# History

The cluster is older than everything managing it: its nodes report an age of a little over two years.

## k3s-ansible on the LAN

Until November 2026 a fork of k3s-ansible in `homelab-ansible` installed k3s, about 600 lines mostly of branches for distributions and install modes the homelab never used. Upgrades went through `k3s-upgrade.yml`, reboots through `k3s-reboot.yml` with `serial: 1`, and `k3s-reset.yml` ran the uninstall scripts. Node addresses and flannel were on the home LAN (`192.168.0.x`). k3s was on v1.31.1, past end of life.

## Buckle, 2026-11-17/18

The migration to Buckle ([`docs/buckle-migration.md`](https://github.com/SpechtLabs/homelab/blob/26d76a6/docs/buckle-migration.md)) replaced the fork with two small modules. Flags moved from `ExecStart` into `/etc/rancher/k3s/config.yaml`, the token juggling in `.service.env` went away, and an upgrade became a one-line bump of `k3s_version`. It migrated on the same k3s version first, then Renovate walked it one minor at a time: v1.31.14 and v1.32.13 on 2026-11-20, then v1.33.13, v1.34.13, v1.35.10, v1.36.6 and v1.37.2 by 2026-11-21. Minors now automerge only on Monday mornings, a week apart. The SQLite datastore stayed (one server, no etcd). Reset wasn't ported, on purpose.

On 2026-11-24 Buckle 2.22.0 shipped node maintenance (SierraSoftworks/buckle#907, cedi's PR upstream): rollouts drain a node before a run that disrupts it. labk3s turned it on with `drain: disruptive` and the `canary`/`core`/`fleet` phases.

## Onto the tailnet, 2026-11-26

All in one night and the following afternoon, in this order:

| Time (CET) | Commit | Change |
|---|---|---|
| 00:52 | `6f7de17` | Additive grants for `tag:k3s-node`, ahead of the switch |
| 00:59 | `760a24a` | `node-ip` = tailnet IPv4, flannel on `tailscale0`, agents join through `svc:labk3s`; units wait for `tailscale0` |
| 01:00 | `a0fac78` | Temporarily: no `disrupts: node`, `k3s-agent` at `parallel: 4`, so the cluster isn't split between LAN and tailnet for half an hour |
| 01:12 | `28faf75` | Drains and one worker at a time again; all five nodes on tailnet addresses, DNS and the API working from a pod on every node |
| 01:54-02:11 | `164bf03`, `bb2c00b`, `0261e92` | The labk3s Argo CD's API and UI become `svc:labk3s-argocd-api` and `svc:lab-argocd` on the new `tailnet-ingress` ProxyGroup |
| 15:16 | `d62877d` | Lesson recorded: restart ceph-csi's node plugin after the nodes change address |
| 15:21 | `3ad28d7` | `advertise-address` = `svc:labk3s`'s VIP; all API traffic through the Service |
| 15:24 | `cb3b742` | The grant to `tag:k3s-server` goes; a test denies the nodes the server's port 6443 |

The one surprise came after the switch: "Ceph CSI — node plugin missing" fired because the node plugin, a hostNetwork pod, had read its node's LAN address at start and kept serving metrics there. Deleting the plugin pods one node at a time fixed it; RBD mappings survived. Buckle, even with no drains and `parallel: 4`, still moved about one node every 2 minutes, so the cluster ran mixed for roughly 10 minutes without visible harm.

Why the design ended up this way: [k3s over the tailnet](k3s-over-the-tailnet.md).
