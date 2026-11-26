# Alerts

Group `ceph-health` in Grafana folder Infrastructure > Ceph, evaluated every minute against the homelab Mimir tenant (datasource `mimir-homelab`). Source: SpechtLabs/k8s-deployment [`apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ceph.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ceph.yaml). Notifications route by labels `service` (`ceph`, `ceph-csi`) and `severity` to Grafana IRM.

The Ceph rules fire once per daemon, OSD, mon or health check and carry its `hostname`. They link to the *Ceph - Status* dashboard (uid `ceph-status`) at the panel listed; the ceph-csi rules link to *Ceph CSI (RBD)* (uid `ceph-csi-rbd`).

| Rule (uid) | Fires when | For | Severity | No data | Panel |
|---|---|---|---|---|---|
| Ceph — HEALTH_ERR (`ceph-health-error`) | `ceph_health_detail{severity="HEALTH_ERR"}` for any check | 5m | critical | OK | 9 Active health checks |
| Ceph — HEALTH_WARN (`ceph-health-warn`) | a HEALTH_WARN check, except the three muted `AUTH_INSECURE_*` | 30m | warning | OK | 9 |
| Ceph — no cluster metrics (`ceph-metrics-absent`) | `count(ceph_health_status)` < 1 | 10m | critical | **Alerting** | 18 Exporters scraped |
| Ceph — OSD down (`ceph-osd-down`) | `ceph_osd_up` < 1 | 5m | warning | OK | 11 OSDs |
| Ceph — placement groups inactive (`ceph-pgs-inactive`) | `ceph_pg_total - ceph_pg_active` > 0 | 10m | critical | OK | 8 Hosts |
| Ceph — monitor out of quorum (`ceph-mon-quorum`) | `ceph_mon_quorum_status` < 1 | 5m | warning | OK | 12 Monitors |
| Ceph — OSD over 75% full (`ceph-osd-nearfull`) | `ceph_osd_stat_bytes_used / ceph_osd_stat_bytes` > 0.75 | 15m | warning | OK | 11 |
| Ceph — daemon not running (`ceph-daemon-down`) | `ceph_cephadm_daemon_status` != 1 | 10m | warning | OK | 10 Daemons |
| Ceph CSI — no provisioner (`csi-provisioner-down`) | `sum(csi_liveness{job="ceph-csi-rbd/provisioner"})` < 1 | 5m | critical | **Alerting** | CSI 3 Provisioners live |
| Ceph CSI — node plugin missing (`csi-nodeplugin-missing`) | nodes minus live node plugins > 0 | 10m | warning | OK | CSI 2 Node plugins live |
| Ceph CSI — volume operations failing (`csi-operation-errors`) | rate of non-OK `csi_sidecar_operations_seconds_count` > 0 (10m window) | 15m | warning | OK | CSI 10 Errors |
| Ceph CSI — PVC over 85% full (`csi-pvc-nearfull`) | `kubelet_volume_stats_used_bytes / capacity` > 0.85 for `ceph-rbd` PVCs | 15m | warning | OK | CSI 15 Mounted volumes |

Ceph rules select `cluster="homelab-ceph"`, ceph-csi rules `cluster="labk3s"`.

`ceph_cephadm_daemon_status` values: 1 running, 0 stopped, -1 error, 2 starting, -2 unknown. It comes from cephadm's inventory (`ceph orch ps`), refreshed every few minutes; `ceph_osd_up` and `ceph_mon_quorum_status` are the cluster's own view and change at once.

What to do for each: [Respond to a Ceph alert](../how-to/respond-to-a-ceph-alert.md).

!!! note "runbook_url"
    Every rule's `runbook_url` points at its own section of [Respond to a Ceph alert](../how-to/respond-to-a-ceph-alert.md) in Backstage (`https://backstage.k8s.specht-labs.de/docs/default/system/ceph/how-to/respond-to-a-ceph-alert/#<id>`). The ids are fixed in the headings (`{#ceph-osd-down}`), so renaming a heading doesn't break the links; a new rule needs a new section and id.
