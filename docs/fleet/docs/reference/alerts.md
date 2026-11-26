# Alerts and SLO

Defined in SpechtLabs/k8s-deployment, evaluated by Grafana Cloud on the `mimir-homelab` data
source.

## Alert rules

Group `homelab-platform`, folder Infrastructure,
[`apps/grafana-operator/cluster/specht-labs/grafanaalertrules-homelab.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-homelab.yaml).
Both evaluate every 5 min.

One pair of rules covers every backup in `vars/backups.yaml`; each fires once per `backup` and
`instance` ([Backups](backups.md)).

| Title | uid | Fires when | For | Severity | Runbook |
|---|---|---|---|---|---|
| NAS backup is stale | `nas-backup-stale` | `time() - max by (backup, instance) (nas_backup_last_success_timestamp_seconds{target="nas"}) > 93600` (26 h) | 10m | warning | [stale](../how-to/respond-to-a-backup-alert.md#nas-backup-stale) |
| NAS backup never recorded | `nas-backup-missing` | `nas_backup_configured` without any `target="nas"` timestamp for the same `backup` and `instance` | 26h | warning | [missing](../how-to/respond-to-a-backup-alert.md#nas-backup-missing) |

Labels: `service: nas-backup`, `category: backup`. They replaced the Buckle-only
`buckle-backup-stale` and `buckle-backup-missing` (2026-11-27).

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
