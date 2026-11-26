# Respond to a labk3s alert

Use this when Grafana pages or notifies about labk3s. Each rule's `runbook_url` points at its section here. The full list is in [Alerts and dashboards](../reference/alerts-and-dashboards.md).

**Before you start:** [kubectl access](get-kubectl-access.md), and SSH to the nodes (`ssh pi@clusterpi-leader`; the login shell is fish, so wrap commands in `bash -c '...'`). Grafana is <https://spechtlabs.grafana.net>; the cluster's own rules are in *Infrastructure > Kubernetes Platform*, group `labk3s-platform`. Run kubectl from outside the k8s-deployment checkout ([why](get-kubectl-access.md#the-kubeconfig-trap)):

```sh
export KUBECONFIG=~/.kube/configs/labk3s
```

## labk3s — telemetry missing {#labk3s-telemetry-missing}

Critical. No kubelet scrape from labk3s reached the homelab Mimir tenant for 10 minutes, so every other labk3s rule and the Ceph CSI rules are blind. It fires on NoData and on query errors on purpose.

1. Is the cluster up? `kubectl --context labk3s get nodes`. If the API doesn't answer either, go to *Homelab — labk3s API availability* below.
2. Is Alloy running?

   ```sh
   kubectl --context labk3s -n monitoring get pods
   ```

   `grafana-k8s-monitoring-alloy-metrics-0` and the other Alloy pods should be `Running`.
3. Can it reach the LGTM front door? Alloy posts to `http://lgtm.sphinx-map.ts.net`, which in-cluster DNS resolves to the egress proxy `ts-lab-lgtm-egress-*` (namespace `tailscale`, device `monitoring-lab-lgtm-egress`, `tag:o11y-agent`). Check that pod runs, then the Alloy logs for push errors:

   ```sh
   kubectl --context labk3s -n tailscale get pods -l tailscale.com/parent-resource=lab-lgtm-egress
   kubectl --context labk3s -n monitoring logs grafana-k8s-monitoring-alloy-metrics-0 --tail=50
   ```

4. If the homelab's other telemetry (the Buckle hosts' Alloy) is missing too, the problem is on the specht-labs side (`svc:lgtm`, Mimir), not here.

## labk3s — node NotReady {#node-notready}

A node's kubelet hasn't reported Ready for 10 minutes. A drained reboot normally takes a few minutes, so this one didn't come back.

1. `kubectl --context labk3s get nodes -o wide`, then on the node:

   ```sh
   ssh pi@clusterpi-worker2 "bash -c 'systemctl status k3s-agent --no-pager; ip -4 addr show tailscale0; journalctl -u k3s-agent -n 50 --no-pager'"
   ```

   (`k3s` instead of `k3s-agent` on `clusterpi-leader`.) No `100.x` address on `tailscale0` means tailscaled is the problem; k3s waits for it.
2. The host's page in Buckle shows whether a rollout is holding it (drained, failed check).
3. Reboot it if it's hung: [Drain and reboot a node](drain-and-reboot-a-node.md).

## labk3s — pod restarting repeatedly {#pod-restarting-repeatedly}

A container restarted more than 3 times in 6 hours. The summary carries the last termination reason.

- **OOMKilled:** raise the memory limit in the app's overlay in k8s-deployment ([Deploy or change an app](deploy-or-change-an-app.md)).
- **Error** or anything else: read the previous container's log, as the alert's description says:

  ```sh
  kubectl --context labk3s -n <namespace> logs <pod> -c <container> --previous
  ```

The leftovers nothing deploys (`gossip`, `chaos-mesh`, see [Who owns what](../reference/ownership.md#nobody-yet)) have a history of restarts; they're not worth fixing.

## labk3s — pod not ready {#pod-not-ready}

A pod has been Pending, or Running but not Ready, for 15 minutes.

```sh
kubectl --context labk3s -n <namespace> describe pod <pod>
```

The events at the bottom say why: `FailedScheduling` (no node fits, often a node still cordoned after a failed rollout: `kubectl --context labk3s uncordon <node>`), `FailedAttachVolume`/`FailedMount` (ceph-csi, see the Ceph CSI sections), an image pull error, or a failing readiness probe.

## labk3s — volume almost full {#volume-almost-full}

A PVC that isn't on `ceph-rbd` has under 10 % free. Those are `local-path` volumes: a directory on the node's root filesystem, so the number is the **node's disk**. On 2026-11-27 the only reporting one, TKA's `tka-tsnet-state` on `clusterpi-worker1`, showed 22 % free.

1. Find the node and what fills it:

   ```sh
   kubectl --context labk3s -n <namespace> get pod -o wide   # the pod using the PVC
   ssh pi@<node> "bash -c 'df -h /; sudo du -xh --max-depth=2 /var/lib/rancher/k3s 2>/dev/null | sort -h | tail'"
   ```

   Container images under `/var/lib/rancher/k3s/agent/containerd` are the usual weight.
2. Free space there, or move the data to a `ceph-rbd` volume, which can grow.

`ceph-rbd` volumes have their own rule, *Ceph CSI — PVC over 85% full*.

## labk3s — Argo CD app unhealthy {#argo-cd-app-unhealthy}

An Application has been Degraded, Missing or Unknown for 30 minutes.

1. Open it at <https://lab-argocd.sphinx-map.ts.net> ([Reach the labk3s Argo CD](reach-the-labk3s-argo-cd.md)); the resource tree marks the unhealthy resource.
2. Or from the shell: `kubectl --context labk3s -n argocd get application <name> -o yaml` and look at `.status.resources` for the one that isn't `Healthy`.
3. Fix it in git; a live edit gets reverted.

## labk3s — Argo CD app out of sync {#argo-cd-app-out-of-sync}

An Application has been OutOfSync for an hour. Every labk3s app auto-syncs with self-heal, so either its syncs keep failing or Argo CD won't retry: it syncs a revision once and says "already attempted sync" until the next commit.

1. In the UI, the app's *Sync status* and *Last sync* say which resource differs and why the sync failed.
2. A sync that fails on a missing CRD: `SkipDryRunOnMissingResource=true`. A field a controller keeps rewriting: `ignoreDifferences` (see [Deploy or change an app](deploy-or-change-an-app.md#if-it-didnt)).
3. Once fixed in git, the next commit triggers a new attempt. Without a commit, **Sync** in the UI retries.

`1-meta-labk3s` flips to OutOfSync for a few seconds every couple of minutes: its child Application `grafana-k8s-monitoring` looks changed, self-heal re-applies it (a no-op), and it's Synced again. The cause wasn't found (2026-11-27); the hour keeps it quiet, but if it ever sticks, that's where to look.

## Homelab — labk3s API availability {#labk3s-api-availability}

Fires as *Error Budget Burn Rate is Very High* (critical) or *High* (warning).

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

## Ceph CSI — node plugin missing {#ceph-csi-node-plugin-missing}

The Ceph docs carry the runbook the alert links to; this is the labk3s side.

A node has no live `csi-rbdplugin` reporting metrics, so pods with `ceph-rbd` volumes can't mount there.

1. List the node plugin pods:

   ```sh
   KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide
   ```

   Five pods, `3/3 Running`, one per node, with the node's `100.x` address as pod IP.
2. If all five run but the alert holds, the plugin is probably listening on an old address. That happened on 2026-11-26 after the nodes moved to the tailnet; follow [Restart pods after the nodes change address](restart-pods-after-the-nodes-change-address.md).
3. If a pod is missing or crashing, `kubectl describe` and its logs come next. The Ceph side (mons reachable, `client.k3s` key) is in the [Ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/).

## The other Ceph CSI rules {#ceph-csi-other}

For *no provisioner*, *volume operations failing* and *PVC over 85% full* the alerts link the [Ceph runbooks](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/). From labk3s:

- **No provisioner:** `kubectl --context labk3s -n ceph-csi-rbd get pods -l component=provisioner`. Two replicas; new PVCs stay `Pending` while none is live.
- **Operations failing:** the *Ceph CSI (RBD)* dashboard (Infrastructure > Ceph) shows which gRPC method fails; the provisioner's logs say why.
- **PVC over 85%:** `ceph-rbd` volumes expand. Raise the PVC's request in k8s-deployment ([Deploy or change an app](deploy-or-change-an-app.md)), not with `kubectl edit`.

## Check it worked

The rule goes back to Normal in Grafana. For the SLO, the burn-rate alert clears once the short window recovers; the error budget itself stays spent.

## If it didn't

Start from the node: `kubectl --context labk3s get nodes`, then the node's k3s unit as under *labk3s — node NotReady* above.
