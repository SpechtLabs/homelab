# Reboot a k3s or Ceph host

Use this when a `clusterpi-*` or `storagepi-ceph*` host needs a reboot or a patch now and you want
the same safety the nightly runs get: the k3s node cordoned and drained first and uncordoned once
healthy, Ceph back to clean before the next Ceph host goes.

A direct action from the host page skips all of that. An **action rollout** doesn't: it runs the
action through the phases in `buckle.yaml`, and `labk3s`'s `maintenance` drains a node around any
run that reboots it.

**Before you start:** the API with `bpost` ([Call the Buckle API](call-the-buckle-api.md)), or
the UI. No other rollout running (check **Rollouts**); an action rollout queues behind it.

1. Start an action rollout limited to the host. The selector sees hosts as the phase selectors do:

    ```sh
    bpost rollouts '{"module":"base","action":"reboot","selector":"host.id == \"clusterpi-worker2\"","note":"reboot worker2"}'
    ```

    For a patch with a reboot only if needed, use `"action":"upgrade"`. Several hosts:
    `"selector":"host.groups contains \"k3s-agent\""` (one at a time, `k3s-agent`'s
    `parallel: 1`) or `"host.groups contains \"ceph\""` (one at a time, `ceph`'s `parallel: 1`).

    In the UI: **Hosts**, **Run action…**, pick `base` / Reboot, enter the same selector and a
    note.

2. The response names the rollout. Watch it as in [Watch a rollout](watch-a-rollout.md). For a
   k3s node you'll see it drain, apply, show `rebooting`, then wait for `k3s-agent/kubelet` (or
   the k3s server's checks) before the node is uncordoned. For a Ceph host, `ceph/cluster` holds
   the host until every OSD and mon is back and no data is degraded.

## Check it worked

The rollout is `completed`. For a k3s node:

```sh
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s get node clusterpi-worker2
```

shows `Ready` without `SchedulingDisabled`. For a Ceph host:

```sh
ssh pi@storagepi-ceph1 "bash -c 'sudo cephadm shell -- ceph -s'"
```

shows `HEALTH_OK` (or only the muted warnings).

## If it didn't

- The rollout paused on `ceph/cluster`: recovery took longer than `settle`. Wait for Ceph, then
  **Retry** ([Fix a paused rollout](fix-a-paused-rollout.md)).
- The row failed in its drain: pods didn't leave the node within the 10-minute `deadline` (a
  PodDisruptionBudget, a pod stuck terminating). `kubectl --context labk3s get pods -A -o wide
  --field-selector spec.nodeName=<node>` shows what's left; nothing was applied, and Buckle hands
  the node back. Drains wait for the pods since Buckle 2.22.1.
- A node stays cordoned after a failed run: a row that fails after its apply leaves the node
  drained until a retry is healthy or the host is rolled back. Retry, or
  `kubectl --context labk3s uncordon <node>` once you've fixed it by hand.
