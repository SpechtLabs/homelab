# Recover a ceph-csi node plugin

Use this when *Ceph CSI — node plugin missing* fires, or a labk3s node's node plugin pod runs but doesn't report `csi_liveness`.

**Before you start:** you need `kubectl` for labk3s (`KUBECONFIG=~/.kube/configs/labk3s`, and always `--context labk3s`: the default context isn't labk3s). Deleting a node plugin pod doesn't unmap volumes: kernel rbd mappings survive, and running pods keep their mounts. New mounts on that node wait until the replacement pod is up.

The node plugin runs in the host network and serves its metrics on port 8681, bound to `POD_IP` once, when the container starts. When the node's address changes, it keeps listening on the old one and the scrape fails. That happened on 2026-11-26, when labk3s moved from the LAN to the tailnet: every node got a new node IP.

1. Find the node without a live plugin:

   ```sh
   kubectl --context labk3s get nodes -o wide
   kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide
   ```

   Every node should have one pod, `3/3 Running`, with the node's current `INTERNAL-IP` as pod IP. A pod missing or not ready is the obvious case; a pod that runs fine but started before the node's address changed is the subtle one.
2. Delete that node's pod, one node at a time:

   ```sh
   kubectl --context labk3s -n ceph-csi-rbd delete pod <ceph-csi-rbd-nodeplugin-xxxxx>
   ```

   The DaemonSet re-creates it at once. Wait for `3/3 Running` before the next node.

!!! warning "Don't use `kubectl rollout restart`"
    `rollout restart` writes a restart annotation into the DaemonSet's pod template. Argo CD (`ceph-csi-rbd` on labk3s, `selfHeal: true`) sees that as drift and reverts it, which rolls the pods again. Delete pods instead.

## Check it worked

The *Ceph CSI (RBD)* dashboard's *Node plugins live* stat equals the node count (5), and the alert resolves within 10 minutes. From an admin device, the metrics answer on the node's current address:

```sh
curl -s http://<node tailnet IP>:8681/metrics | grep -m1 csi_liveness
```

## If it didn't

- The pod doesn't start: `kubectl --context labk3s -n ceph-csi-rbd describe pod <pod>` and the `csi-rbdplugin` container's log.
- The pod runs and answers but the metric still doesn't arrive: the scrape goes node to node over the tailnet (`tag:k3s-node` to `tag:k3s-node`, tcp:8681) through k8s-monitoring's annotation autodiscovery (job `ceph-csi-rbd/nodeplugin`). See [labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/).
