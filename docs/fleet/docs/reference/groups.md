# Groups

Groups are declared under `fleet.groups` in
[`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml) as selectors over a
host's facts and id. Nothing lists hosts by hand except where no fact can tell. Membership below is
what `mise run validate` computes from `fixtures/facts/` on 2026-11-26; a host's live groups are on
its page (`GET /api/v1/hosts/<id>`, field `groups`).

## What the machine is

| Group | Selector | Members |
|---|---|---|
| `debian` | `host.facts.os.family == "debian"` | all 17 |
| `pi` | `host.facts.hardware.raspberry_pi.version != null` | blades, clusterpi-*, storagepi-*, jumphost, timepi |
| `pi5` | `host.facts.hardware.raspberry_pi.version == 5` | clusterpi-leader, storagepi-ceph1..3, jumphost, timepi |
| `blades` | `host.facts.hardware.raspberry_pi.compute_module == true` | blade-pi1..4 |

## What it does, from facts

| Group | Selector | Members |
|---|---|---|
| `ptp-grandmaster` | `host.facts.script.rpi.pps_gpio == true` (`pi-facts`) | timepi |
| `ntp-client` | `host.facts.script.ptp.lan == true` (`ptp-facts`) | every home-LAN host except timepi |
| `ptp-client` | `ntp-client` and `host.facts.script.ptp.hardware == true` | blades, clusterpi-leader, storagepi-ceph1..3, jumphost, isa |
| `nut-client` | a Pi, or `host.id == "nuc"` | all Pis, nuc |

## Roles by host id

No fact tells which host is the Buckle server or the k3s leader, and a Tailscale tag reaches
Buckle only when the agent next reports facts (after a restart), so a tag-derived role can't move in
one rollout. These stay by id.

| Group | Selector | Members |
|---|---|---|
| `k3s-server` | `host.id == "clusterpi-leader"` | clusterpi-leader |
| `k3s-agent` | `host.id like "clusterpi-worker*"` | clusterpi-worker1..4 |
| `ceph` | `host.id like "storagepi-ceph*"` | storagepi-ceph1..3 |
| `buckle-server` | `host.id == "isa"` | isa |
| `o11y-collector` | `host.id == "isa"` | isa |
| `tsidp` | `host.id == "isa"` | isa |
| `nut-server` | `host.id == "isa"` | isa |
| `nut-late` | `host.id in ["jumphost", "timepi"]` | jumphost, timepi (shut down last on power loss) |
| `spechtlabs` | `host.id == "meet"` | meet (spechtlabs o11y endpoints, `admin_user: root`) |
| `jitsi` | `host.id == "meet"` | meet |

Why the split, and how to move a group from ids to a fact:
[Facts over hostnames](../explanation/facts-over-hostnames.md).

## The cluster

`fleet.clusters.labk3s` (kind `kubernetes`, `identity: local`, label `site: home`):

| Key | Value |
|---|---|
| `nodes` | hosts in `k3s-server` or `k3s-agent` |
| `executors` | hosts in `k3s-server` (applies with `/etc/rancher/k3s/k3s.yaml`) |
| `maintenance` | `{ drain: disruptive, deadline: 10m }`: cordon and drain a node before a run that reboots it or changes a `disrupts: node` module, uncordon once healthy |
