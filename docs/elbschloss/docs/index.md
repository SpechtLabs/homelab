# Elbschloss

Elbschloss is the house and the infrastructure in it that other Systems lean on: the home LAN,
the UPS and the NUT chain that shuts the fleet down on a power cut, the Synology NAS, Home
Assistant, and the two x86 boxes, isa and the NUC. The Backstage System is `elbschloss`
([catalog/systems.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/systems.yaml)).

## Parts

| Part | What it is | Configured in |
|---|---|---|
| Home LAN | `192.168.0.0/24`. Carries what mustn't wait for Tailscale: NTP and PTP from timepi, the UPS's NUT server | [catalog/hardware.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml) (`home-lan`) |
| UPS Tower | Ubiquiti UPS Tower 1000 VA at `192.168.0.156`, runs its own NUT server | the UPS itself; [catalog/hardware.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml) (`ups`) |
| NUT | isa re-exports the UPS as `svc:nut` and is the primary that sets FSD on low battery; upsmon on every Pi and the NUC powers them off; UPS metrics and alerts | [modules/nut-server](https://github.com/SpechtLabs/homelab/tree/main/modules/nut-server), [modules/nut-client](https://github.com/SpechtLabs/homelab/tree/main/modules/nut-client) |
| Synology NAS | DS923+ on DSM 7.4.1: DSM, Drive, NFS, Jellyfin, exporters, CouchDB for Obsidian, GitHub backup; reached as `svc:nas`, `svc:stream`, `svc:nfs`, `svc:node-exporter` | DSM by hand; compose projects in [nas/](https://github.com/SpechtLabs/homelab/tree/main/nas) |
| Home Assistant | `hass-elbschloss`, reached as `svc:hass`; backs up to the NAS | Home Assistant itself; [catalog/home-assistant.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/home-assistant.yaml) |
| isa | HP EliteDesk 800 G6 Mini: Buckle server, tsidp, the NUT proxy, the o11y collector | Buckle: [vars/host-isa.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/host-isa.yaml), groups in [buckle.yaml](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml) |
| nuc | The old GIGABYTE Celeron box on Ubuntu 24.10 (end of life). A plain host since isa took over | Buckle: [vars/host-nuc.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/host-nuc.yaml) |

## Where to start

- An alert fired for the NAS, Jellyfin or Home Assistant:
  [Respond to an availability alert](how-to/respond-to-an-availability-alert.md).
- A `UPS — ...` alert fired: [Respond to a UPS alert](how-to/respond-to-a-ups-alert.md).
- The power is out, or just came back: [Respond to a power cut](how-to/respond-to-a-power-cut.md).
- You need an address, a port or a tag: [Hosts](reference/hosts.md) and
  [Services and ports](reference/services-and-ports.md).
- You want to know why isa matters this much: [isa, and why so much runs on it](explanation/isa.md).

The sections: [How-to guides](how-to/index.md) for tasks, [Reference](reference/index.md) for
facts, [Explanation](explanation/index.md) for the reasons behind the setup.

## Related Systems

These have their own docs. This site links to them instead of repeating them.

- [Fleet management (Buckle)](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/):
  the Buckle server on isa, enrolling hosts, rollouts.
- [Tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/): the policy,
  grants, Tailscale Services, tsidp.
- [Observability](https://backstage.k8s.specht-labs.de/docs/default/system/observability/):
  Alloy, Mimir and Loki, Grafana, alerting.
- [Timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/),
  [Ceph](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/),
  [labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/),
  [Compute blades](https://backstage.k8s.specht-labs.de/docs/default/system/compute-blades/),
  [Schiltach](https://backstage.k8s.specht-labs.de/docs/default/system/schiltach/).
