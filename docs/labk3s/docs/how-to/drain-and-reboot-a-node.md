# Drain and reboot a node

Use this when one labk3s node needs a reboot now: a hung kubelet, a kernel that's installed but not running, hardware work.

**Before you start:** [kubectl access](get-kubectl-access.md) and the Buckle UI (<https://buckle.sphinx-map.ts.net>, sign in through tsidp). Rebooting `clusterpi-leader` takes the API down for the duration; the workers keep running their pods but nothing can change.

## Let Buckle do it (no hurry)

You often don't need to do anything. Two schedules reboot nodes through a normal rollout, which drains each node first and does one k3s node at a time:

- `schedules/nightly-upgrades.yaml`, 03:00 Europe/Berlin: `base: upgrade`, rebooting only where the upgrade needs it.
- `schedules/nightly-kernel-reboots.yaml`, 05:30: `base: reboot-if-required` for a kernel installed earlier.

A rollout that disrupts a node (a reboot, or a change to `k3s-server`/`k3s-agent`) cordons and drains it, gives the pods 10 minutes to move, applies, and uncordons it once the host is healthy.

## Reboot it now

A host-page action in Buckle runs straight away on that host, outside a rollout, and doesn't drain. So drain first.

1. Cordon and drain the node:

   ```sh
   export KUBECONFIG=~/.kube/configs/labk3s
   kubectl --context labk3s drain clusterpi-worker2 --ignore-daemonsets --delete-emptydir-data --timeout=10m
   ```

   You should see `node/clusterpi-worker2 drained`. The `tailnet-ingress` PodDisruptionBudget keeps one of its two proxies up, so a drain can wait on it until the other replica is ready.
2. In the Buckle UI, open the host and run its reboot action: `k3s-agent: reboot` on a worker, `base: reboot` on any host. Both ask for a note (they're `confirm: true`) and wait up to 10 minutes for the host to come back.
3. Wait for the node to rejoin:

   ```sh
   kubectl --context labk3s get node clusterpi-worker2 -w
   ```

   `Ready,SchedulingDisabled` means it's back.
4. Hand it back:

   ```sh
   kubectl --context labk3s uncordon clusterpi-worker2
   ```

## Check it worked

```sh
kubectl --context labk3s get nodes
kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide
```

All nodes `Ready` without `SchedulingDisabled`, and the node's ceph-csi node plugin `3/3 Running` again.

## If it didn't

- **The node doesn't come back `Ready`:** SSH in (`ssh pi@clusterpi-worker2`, fish shell) and check `systemctl status k3s-agent`. Its start waits up to 2 minutes for `tailscale0` to have a `100.x` address, so a tailscaled problem shows up as k3s never starting.
- **A drain hangs past 10 minutes:** look for pods with a PDB that can't be satisfied, or local data. Buckle 2.22's own drain evicts once and doesn't wait for the pods (fix proposed upstream as SierraSoftworks/buckle#908), so don't assume a rollout's drain finished either.
