# Mute or unmute a health check

Use this when a Ceph health warning is a deliberate, lasting decision and shouldn't page anyone, or when such a decision is reversed.

**Before you start:** a mute lives in three places, and they have to agree. The mgr exports muted checks as active, so Grafana can't tell a muted check from a live one unless the rule and the dashboard name it.

| Where | What | Repo |
|---|---|---|
| `ceph_health_mutes` | `ceph health mute <code> --sticky`, run by Buckle | SpechtLabs/homelab [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml) |
| Alert rule *Ceph — HEALTH_WARN* | `name!~"..."` in its query | SpechtLabs/k8s-deployment [`apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ceph.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ceph.yaml) |
| *Ceph - Status* dashboard | `MUTED` (shows them as "muted") | k8s-deployment [`hack/gen-ceph-status-dashboard.py`](https://github.com/SpechtLabs/k8s-deployment/blob/main/hack/gen-ceph-status-dashboard.py) |

Today all three list `AUTH_INSECURE_CLIENT_KEY_TYPE`, `AUTH_INSECURE_KEYS_ALLOWED` and `AUTH_INSECURE_KEYS_CREATABLE`.

## Mute a check

1. Add the code to `ceph_health_mutes` in `vars/group-ceph.yaml`, with a comment saying why. Push to `main`; Buckle's `resources` step on `storagepi-ceph1` mutes it with `--sticky` (the mute survives the check clearing and coming back).
2. In k8s-deployment, add the code to the `name!~` regex of rule `ceph-health-warn` in `grafanaalertrules-ceph.yaml`, and to `MUTED` in `hack/gen-ceph-status-dashboard.py`. Regenerate the dashboard:

   ```sh
   cd ~/src/gh/SpechtLabs/k8s-deployment
   python3 hack/gen-ceph-status-dashboard.py > components/grafana-dashboards/ceph/ceph-status.json
   ```

   Push.
3. grafana-operator doesn't resync a GrafanaDashboard when only its ConfigMap changes. If the dashboard still shows the check as active after the sync, annotate the GrafanaDashboard `ceph-status` on the specht-labs cluster (any annotation change makes the operator resync it).

!!! note
    A HEALTH_ERR check isn't excluded by name anywhere: *Ceph — HEALTH_ERR* fires for muted checks too. Don't mute errors.

## Unmute a check

Removing the code from `ceph_health_mutes` doesn't unmute it: the script only ever adds. Do both:

1. Remove it from the three places above and push both repos.
2. Lift the mute by hand, on any storage Pi:

   ```sh
   sudo cephadm shell -- ceph health unmute <code>
   ```

## Check it worked

```sh
sudo cephadm shell -- ceph health detail
```

Muted checks show as `(MUTED, STICKY)`; `ceph -s` lists them under `muted:`. After an unmute the check counts again and `ceph -s` reports HEALTH_WARN while it's active.
