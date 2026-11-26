# Alerts, SLOs and dashboards

Everything here lives in SpechtLabs/k8s-deployment and reaches Grafana Cloud (`https://spechtlabs.grafana.net`) through the grafana-operator on the specht-labs cluster, synced by Argo CD. Change it there, not in the UI. Every alert goes to Grafana IRM: critical ones fast and every 4 h while firing, warnings batched and daily ([`grafananotificationpolicy.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafananotificationpolicy.yaml)).

## Alert rules

Rule group `time-sync`, folder Infrastructure, evaluated every minute on `mimir-homelab`: [`grafanaalertrules-time-sync.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-time-sync.yaml). Labels on all: `service=time-sync`, `category=health`. What to do for each: [Respond to a time-sync alert](../how-to/respond-to-a-time-sync-alert.md).

| Title | UID | Severity | Query | Fires when | For | No data |
|-------|-----|----------|-------|-----------|-----|---------|
| timepi — GPS PPS lost | `time-timepi-pps-lost` | warning | `max(ntpsec_peer_selection{instance="timepi:9100",peer="PPS"})` | < 5.5 | 30m | OK |
| timepi — not synchronised | `time-timepi-unsynced` | critical | `max(ntpsec_stratum{instance="timepi:9100"})` | > 15 | 5m | OK |
| timepi — time metrics missing | `time-timepi-metrics-missing` | warning | `count(ntpsec_stratum{instance="timepi:9100"})` | < 1 | 15m | **Alerting** |
| Host clock off by more than 1 ms | `time-host-offset` | warning | `max by (instance) (abs(chrony_tracking_system_offset_seconds))` | > 0.001 | 15m | OK |
| Host clock unsynchronised | `time-host-unsynced` | warning | `min by (instance) (chrony_tracking_leap_normal)` | < 0.5 | 10m | OK |
| PTP client lost the grandmaster | `time-ptp-no-master` | warning | `min by (instance) (ptp4l_port_slave)` | < 0.5 | 10m | OK |

GPS reception is alerted on here instead of gating Buckle rollouts: `ptp-server`'s `gps-pps-selected` health check has been informational since 2026-11-24.

## SLOs

Files in [`slos/`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/grafana-operator/cluster/specht-labs/slos), applied by the `slo-sync` job. Labels `service_name=time-sync`, `team_name=homelab`; burn alerts carry `service=time-sync`.

| SLO | File | Good event | Objective | Fast / slow burn |
|-----|------|-----------|-----------|------------------|
| Homelab — clock accuracy (PTP clients) | `homelab-clock-accuracy-ptp.yaml` | a host-minute with \|offset\| < 10 µs, hosts with `ptp4l_port_slave` | 99.5% / 28d | critical / warning |
| Homelab — clock accuracy (NTP clients) | `homelab-clock-accuracy-ntp.yaml` | same, < 100 µs, hosts without `ptp4l_port_slave` | 99.5% / 28d | critical / warning |
| Homelab — timepi on GPS time (stratum 1) | `homelab-timepi-stratum1.yaml` | a minute with `ntpsec_peer_selection{peer="PPS"} >= 6` | 80% / 28d (antenna-bound) | warning / warning; never pages |

The 80% reflects 84.5% measured over the 7 days before 2026-11-24; raise it once the antenna sees open sky.

## Dashboards

| Dashboard | Folder | Link | Source |
|-----------|--------|------|--------|
| Time Server (uid `stratum1`) | Infrastructure | [open](https://spechtlabs.grafana.net/d/stratum1) | [`components/grafana-dashboards/infrastructure/stratum1.json`](https://github.com/SpechtLabs/k8s-deployment/blob/main/components/grafana-dashboards/infrastructure/stratum1.json) |

Rows: **Now** (disciplined by, stratum, PPS offset and jitter, GPS fix, satellites, PTP port and clock class, NTP clients), **Timing accuracy**, **GPS receiver** (sky plot, SNR per satellite, DOP), **NTP service**, **Fleet clients** (worst offset, via PTP / via NTP, source per host), **PTP grandmaster** (phc2sys, messages, announced quality), **Hardware the clock depends on** (SoC temperature against frequency), **Logs** (time daemons, last 24 h, from Loki).

The operator only picks up a changed dashboard on its periodic resync, about 10 minutes after Argo CD syncs.
