# How-to guides

Task recipes for the Ceph cluster and its labk3s client. Each says what you need first, the commands, and how to tell it worked.

- [Respond to a Ceph alert](respond-to-a-ceph-alert.md): one section per alert rule in the `ceph-health` group.
- [Check cluster health](check-cluster-health.md): `ceph -s` and friends, what healthy looks like.
- [Restart a daemon](restart-a-daemon.md): one daemon, or every daemon on a host after Docker restarted.
- [Take a host down for maintenance](take-a-host-down-for-maintenance.md): `noout`, reboot or power off, and how Buckle's limits fit in.
- [Add a Ceph host](add-a-ceph-host.md): disk split, `ceph_hosts`, the spec.
- [Replace a failed OSD or host](replace-a-failed-osd-or-host.md): a dead NVMe means a rebuilt host.
- [Add a pool and a client key](add-a-pool-and-a-client-key.md): `ceph_rbd_pools`, `ceph_clients`, which key type.
- [Rotate a client key](rotate-a-client-key.md): when Buckle reports a key of the wrong type.
- [Add an S3 user](add-an-s3-user.md): `ceph_rgw_users` and reading the keys.
- [Mute or unmute a health check](mute-or-unmute-a-health-check.md): the vars, the alert rule and the dashboard together.
- [Upgrade Ceph](upgrade-ceph.md): `ceph orch upgrade`, then the versions in the repo.
- [Give a Kubernetes cluster RBD access](give-a-kubernetes-cluster-rbd-access.md): pool, `tag:ceph-client`, ceph-csi config.
- [Recover a ceph-csi node plugin](recover-a-ceph-csi-node-plugin.md): the plugin that stopped reporting after a node address change.
- [Open the Ceph dashboard](open-the-ceph-dashboard.md): find the active mgr, reset the admin password.
