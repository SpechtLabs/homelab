# Restart pods after the nodes change address

Use this after anything changes the nodes' addresses: a change to `node-ip`, `flannel-iface` or `advertise-address`, a node re-joining the tailnet with a new IP, or "Ceph CSI — node plugin missing" firing right after such a change.

**Before you start:** [kubectl access](get-kubectl-access.md). The only hostNetwork pods on labk3s are the ceph-csi node plugins (`ceph-csi-rbd-nodeplugin-*`, one per node). Their `csi-rbdplugin` container binds its metrics port 8681 to `POD_IP`, read once at container start. On a hostNetwork pod that's the node's address, so after a change it keeps listening on the old one and the scrape fails. Existing RBD mappings survive a restart.

1. List them with their nodes:

   ```sh
   export KUBECONFIG=~/.kube/configs/labk3s
   kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide
   ```

   Compare the `IP` column with `kubectl --context labk3s get nodes -o wide`.
2. Delete them one node at a time, waiting for each replacement to be `3/3 Running`:

   ```sh
   kubectl --context labk3s -n ceph-csi-rbd delete pod -l component=nodeplugin --field-selector spec.nodeName=clusterpi-worker1
   kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide -w
   ```

   Repeat for `clusterpi-worker2` to `clusterpi-worker4` and `clusterpi-leader`. Don't use `kubectl rollout restart`: it writes an annotation into the DaemonSet, which Argo CD's self-heal sees as drift and reverts.

To find other hostNetwork pods if more appear later:

```sh
kubectl --context labk3s get pods -A -o jsonpath='{range .items[?(@.spec.hostNetwork==true)]}{.metadata.namespace}/{.metadata.name} {.spec.nodeName}{"\n"}{end}'
```

## Check it worked

The new pods show the node's current address as pod IP, and "Ceph CSI — node plugin missing" returns to Normal within its 10-minute window. The *Ceph CSI (RBD)* dashboard (Grafana, Infrastructure > Ceph) shows a live node plugin per node.

## If it didn't

A plugin that stays down after a restart isn't an address problem. Go to the Ceph side: the [Ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/) cover a ceph-csi node plugin that can't reach the mons. Why a change to the node addresses must reach all nodes at once is in [k3s over the tailnet](../explanation/k3s-over-the-tailnet.md#changing-how-the-nodes-connect).
