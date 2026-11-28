# Hosts

Machines in the Elbschloss System. Values checked live on 2026-11-26.

Sources of truth: tailnet addresses and tags in `tailscale status` and the admin console; LAN
addresses come from DHCP on the router (fixed leases where noted); hardware in
[catalog/hardware.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml)
and [catalog/home-assistant.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/home-assistant.yaml).

| Host | Role | Hardware / OS | LAN | Tailnet name | Tailnet IPv4 | Tags | Log in |
|---|---|---|---|---|---|---|---|
| isa | Buckle server, tsidp, NUT proxy (`svc:nut`), o11y collector | HP EliteDesk 800 G6 Mini, i5-10500; Ubuntu 26.04.1 LTS | 192.168.0.118 (DHCP) | `isa` | 100.70.89.41 | `tag:buckle-agent`, `tag:buckle-server`, `tag:nut-server`, `tag:o11y-collector`, `tag:tsidp-client` | `ssh cedi@isa` |
| idp | tsidp's own tailnet node; the process runs on isa | (on isa) | none | `idp` | 100.77.112.23 | `tag:tsidp` | none (it's a tsnet node) |
| nuc | Plain host; still runs Incus and Docker, unmanaged | GIGABYTE mini PC, Celeron; Ubuntu 24.10 (end of life) | 192.168.0.72 (static) | `nuc` | 100.122.149.90 | `tag:buckle-agent` | `ssh cedi@nuc` |
| NAS | DSM, Drive, NFS, Jellyfin, exporters | Synology DS923+; DSM 7.4.1; Tailscale 1.98.4 (DSM package) | 192.168.0.64 | `nas-elbschloss` | 100.71.201.45 | `tag:nas`, `tag:tsidp-client` | `ssh -J cedi@nyx king@nas.local` (sudo works) |
| hass | Home Assistant at home | not recorded in the repo | 192.168.0.62 | `hass-elbschloss` | 100.75.135.70 | `tag:smarthome`, `tag:o11y-agent` | see [Home Assistant](home-assistant.md) |
| UPS Tower | The UPS; serves NUT itself (UPS name `ups`) | Ubiquiti `TOWER_1000VA_230V`, line-interactive | 192.168.0.154, `UPSTower.local` (keep the DHCP lease fixed) | not on the tailnet | | | its own web UI |
| Router | Default gateway and DNS for the LAN (seen on isa) | not recorded in the repo | 192.168.0.1 | | | | |

On isa and the NUC the login shell is fish; wrap remote commands in `bash -c '...'`. The NAS's
SSH is reached on the LAN, through nyx as the jump host.

## Other Systems' hosts that matter here

| Host | Why it shows up here | LAN | System |
|---|---|---|---|
| jumphost | Late NUT host: shuts down only when the UPS runs low | 192.168.0.31 | [Tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) |
| timepi | Late NUT host; LAN address fixed in `vars/defaults.yaml` (`ntp_server`) | 192.168.0.109 | [Timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/) |
| clusterpi-*, storagepi-ceph*, blade-pi* | Early NUT hosts: off 60 s into a power cut | DHCP | labk3s, Ceph, Compute blades |
| hass-schiltach | The other Home Assistant, in Schiltach; tailnet 100.89.41.43, `tag:smarthome` | not at home | [Schiltach](https://backstage.k8s.specht-labs.de/docs/default/system/schiltach/) |

## Buckle groups that pick these hosts

From [buckle.yaml](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml). All of isa's
roles are chosen by host id, not by tag.

| Group | Selector | Hosts |
|---|---|---|
| `buckle-server`, `tsidp`, `o11y-collector`, `nut-server` | `host.id == "isa"` | isa |
| `nut-client` | any Raspberry Pi, or `host.id == "nuc"` | 14 Pis, nuc |
| `nut-late` | `host.id in ["jumphost", "timepi"]` | jumphost, timepi |
| rollout phase `core` | `host.id in ["nuc", "isa", "timepi", "jumphost"]` | two at a time |

The NAS, Home Assistant and the UPS aren't Buckle hosts.
