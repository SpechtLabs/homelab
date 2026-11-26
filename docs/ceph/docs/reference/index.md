# Reference

Facts to look up. Where a value drifts, each page names its source of truth.

- [Hosts and daemons](hosts-and-daemons.md): the three storage Pis, their addresses and OSDs, daemons, units, disk layout, cluster settings.
- [Network and tailnet](network-and-tailnet.md): ports, the OSD range split around 7480, tailnet grants and tags.
- [Pools, clients and S3 users](pools-and-clients.md): pools, cephx clients and key types, the `ceph-rbd` StorageClass, RGW.
- [Variables](variables.md): `vars/group-ceph.yaml`, versions, module defaults.
- [Buckle module](buckle-module.md): what `modules/ceph` and `modules/ceph-disk` install, their actions and health checks.
- [Alerts](alerts.md): the `ceph-health` rules, conditions and severities.
- [Dashboards and metrics](dashboards-and-metrics.md): Grafana dashboards, uids, scrape jobs.
