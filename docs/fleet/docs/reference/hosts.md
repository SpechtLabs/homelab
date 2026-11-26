# Hosts and phases

The 17 hosts Buckle manages, as of 2026-11-26, and the `labk3s` cluster target. The source of
truth is the server's Hosts page (`GET /api/v1/hosts`); hardware and OS here come from
`fixtures/facts/`. `hole` is on the tailnet but not enrolled.

The host id is the tailnet node name. Every host carries `tag:buckle-agent`.

| Host | Hardware, OS | Phase | Log in as | What it's for |
|---|---|---|---|---|
| blade-pi1..4 | Pi CM4 compute blades, Debian 12 | `canary` | `pi` | Compute blades; prove each revision first |
| isa | HP EliteDesk 800 G6 Mini (i5-10500), Ubuntu 26.04 | `core` | `cedi` | Buckle server, tsidp, NUT proxy, o11y collector |
| nuc | Intel NUC (Celeron 2955U), Ubuntu 24.10 (EOL) | `core` | `cedi` | Plain host since 2026-11-23 |
| timepi | Pi 5, Debian 12 | `core` | `cedi` | GPS/PPS time server, PTP grandmaster |
| jumphost | Pi 5, Debian 12 | `core` | `pi` | The way in |
| clusterpi-leader | Pi 5, Debian 12 | `fleet` | `pi` | k3s server (`labk3s`), Argo CD seed |
| clusterpi-worker1..4 | Pi 4, Debian 12 | `fleet` | `pi` | k3s agents |
| storagepi-ceph1..3 | Pi 5, Debian 12 | `fleet` | `pi` | Ceph (cephadm) |
| meet | vServer, Ubuntu 24.04 | `fleet` | `root` | Jitsi Meet; ships to the spechtlabs o11y stack |
| labk3s | Kubernetes cluster (executor: clusterpi-leader) | `fleet` | - | Target for `workloads/argocd-root` |

Phases are assigned by the first `select` in `rollout.phases` that matches
([Rollout policy](rollout-policy.md)): `canary` is the `blades` group, `core` is
`host.id in ["nuc", "isa", "timepi", "jumphost"]`, `fleet` is everything else.

## SSH

Tailscale SSH: admins log in as any non-root user on `tag:buckle-agent` hosts directly, as `root`
in check mode (a browser re-auth every 8 h). `ssh root@meet` therefore waits for that re-auth.
The `dotfiles` module makes fish the login shell of each host's login account
(`login_shell` in `vars/defaults.yaml`), so wrap POSIX commands in `bash -c '...'`. Host-to-host SSH
over the tailnet is refused; use LAN addresses (isa: 192.168.0.118).

## Where each host's settings are

| Host | Vars |
|---|---|
| isa | [`vars/host-isa.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-isa.yaml) |
| nuc | [`vars/host-nuc.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-nuc.yaml) |
| timepi | [`vars/host-timepi.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-timepi.yaml) |
| meet | [`vars/host-meet.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-meet.yaml) |
| jumphost | inline in `buckle.yaml` (`dotfiles_preset: core`) |
| the others | group files only ([Vars](vars.md)) |
