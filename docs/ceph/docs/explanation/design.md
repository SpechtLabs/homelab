# Design

The cluster was built on 2026-11-18/19 with three goals from the operator: managed by Buckle like every other host, reachable only over Tailscale, and fully in git. Most of what looks odd follows from one of those.

## cephadm, with Buckle around it

Ceph ships its own orchestrator, and it's good at the part Buckle would do badly: placing daemons, pulling container images, restarting and upgrading them in the right order. So the split mirrors k3s and Argo CD elsewhere in the homelab. Buckle owns the hosts (packages, the disk, SSH access for cephadm, a route) and the cluster's *desired state*: the orchestrator specs in `cluster.yaml` and a resources script for pools, keys, config, mutes and S3 users. cephadm owns what runs.

Buckle applies each file when its rendered content changes and keeps a copy of what it last applied. Both steps only create or set. That's deliberate: removing a line from `vars/group-ceph.yaml` should never delete a pool full of labk3s volumes. The price is that removals are manual (`ceph orch rm`, `ceph osd pool rm`, `ceph health unmute`), and the vars can drift from the cluster if you forget one.

Upgrades follow the same split. `ceph orch upgrade` moves the running cluster; the `ceph_version` in the repo only picks the `cephadm` binary and the bootstrap image. Driving the upgrade from Buckle would mean re-implementing cephadm's ordering.

Buckle also gates itself on Ceph. Module `ceph` has `parallel: 1`, and Buckle counts that limit across every module on the host, so a kernel reboot from `base` waits its turn like a Ceph change would. The `cluster` health check holds each host until the cluster has every mon and OSD back and no degraded PGs. One host at a time keeps two copies of every PG online; two at once would drop PGs below `min_size` and stop writes.

## Everything on the tailnet

`public_network` is `100.64.0.0/10`, Tailscale's whole CGNAT range, so mons, OSDs and RGW bind to the hosts' 100.x addresses. Clients (the labk3s nodes) and the hosts themselves talk over WireGuard. The measured cost was 878 vs 933 Mbit/s against the LAN; for a cluster of Pi 5s that's noise.

What it buys: Ceph's traffic is covered by the tailnet policy like everything else. Only `tag:ceph` hosts reach each other, only `tag:ceph-client` nodes reach the mons and OSDs, nothing on the LAN reaches Ceph at all, and the rules have tests.

What it costs:

- **Mon addresses are tailnet addresses.** The monmap stores them, and a mon whose address changes won't start. A Tailscale node keeps its address for as long as it exists, which is good enough, but re-enrolling a host as a new node means re-adding its mon.
- **cephadm can't see them.** `cephadm list-networks` reads the main routing table; Tailscale keeps its routes in table 52. Without help, cephadm says no host is in `public_network` and won't place mons. `ceph-tailnet-route.service` adds a main-table route for each host's own address. It never carries a packet, because the local table answers for the host's own address first; it only exists for cephadm to read.
- **Tailscale SSH owns port 22** on the tailnet address and authenticates by tailnet identity, which cephadm can't do. A second sshd port, 2222, takes root logins with cephadm's key only, from tailnet addresses only.
- **Names don't resolve everywhere.** labk3s's CoreDNS forwards `*.ts.net` to the Tailscale operator's nameserver, which knows only the operator's proxies. ceph-csi lists the mons by IP; pods reach 100.x through the node.

## Why there's no Tailscale Service for Ceph

Most homelab services sit behind a Tailscale Service (`svc:<name>`), so grants name the Service and the host behind it can move. Ceph can't work that way. A client asks a mon for the cluster map, then talks to *every* OSD at the OSD's own address; there's no single endpoint to put behind a VIP, and the addresses in the maps have to be the real ones.

```mermaid
flowchart LR
  subgraph labk3s["labk3s node (tag:ceph-client)"]
    csi["ceph-csi node plugin + kernel rbd"]
  end
  subgraph ceph["storage Pis (tag:ceph), 100.x addresses"]
    mon["mons :3300 / :6789<br/>(3, one per host)"]
    osd["OSDs :6800-7568, not 7480<br/>(3, one per host)"]
  end
  csi -- "1. cluster map, auth (client.k3s)" --> mon
  csi -- "2. reads and writes, to each OSD directly" --> osd
  osd <-- "replication between hosts" --> osd
``` So the Ceph grants are among the few left that name tags as destinations: `tag:ceph` for the hosts, with `tag:ceph-client` as the client attribute.

The ports have one wrinkle. OSDs and the mgr bind anywhere in 6800-7568 (`ms_bind_port_max`), and RGW's 7480 sits inside that range. RGW has no tailnet consumer, so the grants split the range (6800-7479, 7481-7568) and the policy tests deny 7480, 8443 and 9283 to clients explicitly.

## Restarts: always

cephadm writes its unit template with `Restart=on-failure`. A Docker restart stops every container with SIGTERM, the daemons exit 0, and systemd treats that as a clean stop: they stay down. Buckle's drop-in sets `Restart=always` for the template, so it covers every daemon cephadm adds later, and cephadm never writes that directory. `systemctl stop`, which `ceph orch daemon stop` and redeploys use, still stops a daemon for good. [Failure modes](failure-modes.md) has the incident that caused it.

## Monitoring without cephadm's stack

Bootstrap skipped cephadm's Prometheus, Grafana and Alertmanager (`--skip-monitoring-stack`). The homelab already has one place for metrics, so each storage Pi's Alloy scrapes its local mgr and ceph-exporter into Mimir, the ceph-mixin dashboards sit in Grafana Cloud, and the alerts are a short curated set rather than the mixin's hundred or so. Every mgr runs the prometheus module; standbys answer with an empty body instead of redirecting, so the active mgr's metrics arrive once.
