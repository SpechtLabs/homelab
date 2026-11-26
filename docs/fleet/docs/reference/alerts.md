# Alerts and SLO

Defined in SpechtLabs/k8s-deployment, evaluated by Grafana Cloud on the `mimir-homelab` data
source.

## Alert rules

Group `homelab-platform`, folder Infrastructure,
[`apps/grafana-operator/cluster/specht-labs/grafanaalertrules-homelab.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-homelab.yaml).
Both evaluate every 5 min.

| Title | uid | Fires when | For | Severity | Runbook |
|---|---|---|---|---|---|
| Buckle — database backup on the NAS is stale | `buckle-backup-stale` | `time() - max(buckle_backup_last_success_timestamp_seconds{target="nas"}) > 93600` (26 h) | 10m | warning | [Respond to a backup alert](../how-to/respond-to-a-backup-alert.md) |
| Buckle — no database backup on the NAS recorded | `buckle-backup-missing` | `absent(buckle_backup_last_success_timestamp_seconds{target="nas"})` | 26h | warning | same |

Labels: `service: buckle`, `category: backup`.

## SLO

`Homelab — Buckle availability` (`hlbuckleavail`),
[`slos/homelab-buckle-availability.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/slos/homelab-buckle-availability.yaml),
applied by the `slo-sync` job.

| | |
|---|---|
| SLI | `avg_over_time(probe_success{job="blackbox", service="buckle"}[$__rate_interval])`: isa's Alloy probes `https://buckle.sphinx-map.ts.net/readyz` every 30 s |
| Objective | 99.5% over 28 days |
| Fast burn | `severity: critical` |
| Slow burn | `severity: warning` |

99.5% because agents keep running without the server; it's the control plane (rollouts, actions,
sign-in) that's out. When it fires: `curl -s https://buckle.sphinx-map.ts.net/readyz` (503 names
what's broken), then `journalctl -u buckle-server` on isa and `tailscale serve status` there.

No Grafana dashboard covers Buckle itself.
