# Respond to a labk3s alert

Use this when Grafana pages or notifies about labk3s: the API availability SLO is burning, or one of the `Ceph CSI —` rules fired. The full list is in [Alerts and dashboards](../reference/alerts-and-dashboards.md).

**Before you start:** [kubectl access](get-kubectl-access.md), and SSH to the nodes (`ssh pi@clusterpi-leader`; the login shell is fish, so wrap commands in `bash -c '...'`). Grafana is <https://spechtlabs.grafana.net>.

## "Homelab — labk3s API availability - Error Budget Burn Rate is High / Very High"

The probe runs on isa (the o11y collector) every 30 s against `https://labk3s.sphinx-map.ts.net:6443/readyz` and counts a `401` as up. So the alert means the API didn't answer through `svc:labk3s`, which can be the Service, the server, or isa's view of either.

1. Try the same path yourself:

   ```sh
   dig +short labk3s.sphinx-map.ts.net
   curl -sk -o /dev/null -w '%{http_code}\n' https://labk3s.sphinx-map.ts.net:6443/readyz
   ```

   You should see `100.67.145.122` and `401`. A different address means the Service changed; see step 4.
2. Ask the API with credentials:

   ```sh
   KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s get --raw /readyz
   ```

   `ok` here while isa's probe fails points at isa or its grant, not at labk3s.
3. If it fails for you too, look at the server:

   ```sh
   ssh pi@clusterpi-leader "bash -c 'systemctl status k3s --no-pager; journalctl -u k3s -n 100 --no-pager'"
   ```

   The unit restarts by itself (`Restart=always`), and its start waits up to 2 minutes for `tailscale0` to get its IPv4. A k3s that never comes up after a reboot often means tailscaled didn't.
4. Open `clusterpi-leader` in the Buckle UI (<https://buckle.sphinx-map.ts.net>). The `k3s-server` checks say which layer broke: `apiserver` (local `/readyz`), `svc-api` (the same through the Service, checking the certificate name) and `svc-ip` (MagicDNS still returns `k3s_service_ip`). If `svc-ip` fails, the Service's VIP no longer matches [`k3s_service_ip`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-server/module.yaml) and the cluster advertises a dead address: update the var to the new VIP and let the rollout restart k3s.
5. Check the Service is still served from the leader. The `svc-k3s` task in `modules/k3s-server` (re)runs `tailscale serve --service=svc:labk3s --tcp=6443 tcp://localhost:6443` whenever the serve config lacks it; a Buckle rollout or drift correction puts it back. The host needs `tag:k3s-server` to be auto-approved for the Service.

## "Ceph CSI — node plugin missing"

A node has no live `csi-rbdplugin` reporting metrics, so pods with `ceph-rbd` volumes can't mount there.

1. List the node plugin pods:

   ```sh
   KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide
   ```

   Five pods, `3/3 Running`, one per node, with the node's `100.x` address as pod IP.
2. If all five run but the alert holds, the plugin is probably listening on an old address. That happened on 2026-11-26 after the nodes moved to the tailnet; follow [Restart pods after the nodes change address](restart-pods-after-the-nodes-change-address.md).
3. If a pod is missing or crashing, `kubectl describe` and its logs come next. The Ceph side (mons reachable, `client.k3s` key) is in the [Ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/).

## "Ceph CSI — no provisioner", "volume operations failing", "PVC over 85% full"

- **No provisioner:** `kubectl --context labk3s -n ceph-csi-rbd get pods -l component=provisioner`. Two replicas; new PVCs stay `Pending` while none is live.
- **Operations failing:** the *Ceph CSI (RBD)* dashboard (Infrastructure > Ceph) shows which gRPC method fails; the provisioner's logs say why.
- **PVC over 85%:** `ceph-rbd` volumes expand. Raise the PVC's request in k8s-deployment ([Deploy or change an app](deploy-or-change-an-app.md)), not with `kubectl edit`.

## Check it worked

The rule goes back to Normal in Grafana. For the SLO, the burn-rate alert clears once the short window recovers; the error budget itself stays spent.

## If it didn't

A node that's `NotReady` gets no alert of its own on labk3s (the `Node NotReady` rule covers specht-labs only). Check `kubectl --context labk3s get nodes`, then the node's `k3s-agent` unit the same way as step 3, and [Drain and reboot a node](drain-and-reboot-a-node.md).
