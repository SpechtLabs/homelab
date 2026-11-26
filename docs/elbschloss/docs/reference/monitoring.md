# Monitoring

The pipeline itself (Alloy, Mimir, Loki, Grafana Cloud alerting, IRM paging) belongs to the
[Observability](https://backstage.k8s.specht-labs.de/docs/default/system/observability/) System.
This page lists what watches Elbschloss.

## SLOs

Files in SpechtLabs/k8s-deployment, `apps/grafana-operator/cluster/specht-labs/slos/`.

| SLO (uid) | Name | Objective | SLI | Fast-burn alert |
|---|---|---|---|---|
| `hlnasavail` | `Homelab — NAS (DSM) availability` | 99.5 % over 28 d | `probe_success{job="blackbox", service="nas"}` | severity `critical` (pages) |
| `hljellyfinavail` | `Homelab — Jellyfin availability` | 99.5 % over 28 d | `probe_success{job="blackbox", service="jellyfin"}` | `critical` |
| `hlhassavail` | `Homelab — Home Assistant availability` | 99.5 % over 28 d | `probe_success{job="blackbox", service="home-assistant"}` | `critical` |

## Probes

From [vars/group-o11y-collector.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/group-o11y-collector.yaml)
(`o11y_probes`), run by Alloy's blackbox exporter on isa every 30 s. Each URL is the path users
take.

| Probe | `service` | Module | URL |
|---|---|---|---|
| `nas-dsm` | `nas` | `http_2xx` | `https://nas.sphinx-map.ts.net/` |
| `jellyfin` | `jellyfin` | `http_2xx` | `https://stream.sphinx-map.ts.net/health` |
| `home-assistant` | `home-assistant` | `http_2xx` | `http://hass.sphinx-map.ts.net:8123/` |

The same file probes Buckle, tsidp and the labk3s API for their Systems. Every probe runs on
isa, so if isa or its Alloy is down, all six go dark together.

## Scrapes of the NAS

Also from `vars/group-o11y-collector.yaml` (`o11y_remote_scrapes`), by the collector on isa:

| Name | Job | Target | Notes |
|---|---|---|---|
| `nas_node_exporter` | `node_exporter` | `node-exporter.sphinx-map.ts.net:9100` | through `svc:node-exporter`; series keep `instance="nas-elbschloss:9100"` |
| `snmp_exporter` | `snmp` | `192.168.0.64:9116`, path `/snmp` | params `module=synology`, `auth=snmpv3`, `target=nas`; over the LAN |
| `cadvisor` | `cadvisor` | `192.168.0.64:8123` | over the LAN |

isa and the NUC run their own Alloy like every Buckle host (`job="node_exporter"`,
`instance="<host>:9100"`).

## Alerts

In `apps/grafana-operator/cluster/specht-labs/grafanaalertrules-homelab.yaml` (group
`homelab-platform`, folder Infrastructure):

| uid | Title | Severity | Elbschloss side |
|---|---|---|---|
| `buckle-backup-stale` | `Buckle — database backup on the NAS is stale` | warning | the NFS path to the NAS (`svc:nfs`) |
| `buckle-backup-missing` | `Buckle — no database backup on the NAS recorded` | warning | same |

The backup itself belongs to the [Fleet](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/)
System. There's no alert on the UPS, on NUT or on Home Assistant's backups.

## Dashboards

| Grafana folder | Dashboard | For |
|---|---|---|
| Applications | `Synology Dashboard` | the NAS (SNMP, node-exporter, cAdvisor) |
| Applications | `Home Assistant — Diagnostics` | both Home Assistants |
| Infrastructure | `Node Exporter for Prometheus Dashboard` | isa, the NUC |

The SLOs show in Grafana's SLO app under the names above.
