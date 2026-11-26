# Dashboards and metrics

## Dashboards

Grafana Cloud (<https://spechtlabs.grafana.net>), folder Infrastructure > Ceph. Deployed by grafana-operator from SpechtLabs/k8s-deployment [`components/grafana-dashboards/ceph`](https://github.com/SpechtLabs/k8s-deployment/tree/main/components/grafana-dashboards/ceph) (CRs in [`grafanadashboards-ceph.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanadashboards-ceph.yaml)).

| Dashboard | uid | Source | Use it for |
|---|---|---|---|
| Ceph - Status | `ceph-status` | `hack/gen-ceph-status-dashboard.py` | start here: per host, daemons running, OSD up, mon in quorum, exporters scraped; active health checks; every daemon, OSD, mon; timelines |
| Ceph CSI (RBD) | `ceph-csi-rbd` | `hack/gen-ceph-csi-dashboard.py` | labk3s side: node plugins and provisioners live, CSI operations and errors, volumes, pool and image I/O |
| Ceph - Cluster | `edtb0oxdq` | ceph-mixin | capacity, IOPS, throughput |
| Ceph Cluster - Advanced | `dn13KBeTv` | ceph-mixin | |
| Host Overview, Host Details | `y0KGL0iZz`, `rtOg0AiWz` | ceph-mixin | |
| OSD Overview, OSD device details | `lo02I1Aiz`, `CrAHE0iZz` | ceph-mixin | |
| Ceph Pools Overview, Ceph Pool Details | `z99hzWtmk`, `-xyV8KCiz` | ceph-mixin | |
| RBD Overview, RBD Details | `41FrpeUiz`, `YhCYGcuZz` | ceph-mixin | per-image stats for pool `k3s` |
| RGW Overview, RGW Instance Detail | `WAkugZpiz`, `x5ARzZtmk` | ceph-mixin | |

The mixin dashboards are from `monitoring/ceph-mixin/dashboards_out` at Ceph v20.2.5, changed only to default the datasource to Mimir (homelab). The two generated ones: edit the script and regenerate, don't edit the JSON. The alert rules link to *Ceph - Status* panels by id, and ids follow the order in the script, so moving a panel means updating the rules' `__panelId__`.

*Ceph - Status* panel ids: 2 Health, 3 Daemons not running, 4 OSDs down, 5 Mons out of quorum, 6 PGs not active+clean, 7 Objects degraded, 8 Hosts, 9 Active health checks, 10 Daemons, 11 OSDs, 12 Monitors, 14 Daemon status, 15 OSD up, 16 Mon quorum, 17 Health checks, 18 Exporters scraped.

grafana-operator doesn't resync a GrafanaDashboard when only its ConfigMap changes; annotate the CR to nudge it.

## Metrics

All in the homelab Mimir tenant.

| Job | Scraped by | Target | Labels |
|---|---|---|---|
| `ceph_mgr` | Alloy on each storage Pi, locally | mgr prometheus module, :9283 | `cluster="homelab-ceph"`, `honor_labels` (keeps the mgr's per-daemon `instance`) |
| `ceph_exporter` | Alloy on each storage Pi, locally | ceph-exporter, :9926 | `cluster="homelab-ceph"` |
| `rpi_exporter` | Alloy on each storage Pi | :9243 | |
| `ceph-csi-rbd/nodeplugin` | k8s-monitoring on labk3s (pod annotations) | node plugin, :8681 | `cluster="labk3s"` |
| `ceph-csi-rbd/provisioner` | k8s-monitoring on labk3s | provisioner sidecars :8090 (provisioner), :8091 (resizer), :8093 (attacher), plus liveness | `cluster="labk3s"` |

Only the active mgr returns metrics; standbys answer `/metrics` with an empty body (`mgr/prometheus/standby_behaviour: error`), so Alloy doesn't record the active mgr's metrics twice. Kubelet volume stats for PVCs come from k8s-monitoring too.

Useful series: `ceph_health_status`, `ceph_health_detail{name,severity}`, `ceph_osd_up`, `ceph_osd_in`, `ceph_osd_metadata{hostname}`, `ceph_mon_quorum_status`, `ceph_mon_metadata{hostname}`, `ceph_cephadm_daemon_status{hostname,daemon_name,service_type}`, `ceph_pg_total`, `ceph_pg_active`, `ceph_osd_stat_bytes(_used)`, `csi_liveness`, `csi_sidecar_operations_seconds_count`.
