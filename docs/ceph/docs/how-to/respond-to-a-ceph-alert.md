# Respond to a Ceph alert

Use this when an alert from the `ceph-health` group fires (Grafana: Infrastructure > Ceph). Each section below has the alert rule's exact title as its heading, so the rules' `runbook_url` can point straight at it.

**Before you start:** open the *Ceph - Status* dashboard ([spechtlabs.grafana.net/d/ceph-status](https://spechtlabs.grafana.net/d/ceph-status), Infrastructure > Ceph). Its Hosts table tells you which host is affected, and the alert's title says it too. For the Ceph CLI, SSH to any storage Pi (each holds the admin keyring):

```sh
ssh pi@storagepi-ceph1
sudo cephadm shell -- ceph -s
sudo cephadm shell -- ceph health detail
```

The systemd units are named `ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@<daemon>`, where `<daemon>` is what `ceph orch ps` lists (`osd.0`, `mon.storagepi-ceph1`, `mgr.storagepi-ceph2.ulrfqs`, ...). The alert descriptions write that fsid as `<fsid>`.

!!! tip "Several alerts at once from one host"
    Mon, OSD and daemon alerts that all name the same host mean its daemons stopped together. That has almost always been Docker restarting (an upgrade) or the host rebooting. Go to [Restart a daemon](restart-a-daemon.md#all-daemons-on-a-host-stopped) first.

While the cluster is unhealthy, Buckle won't touch the next Ceph host: the `cluster` health check fails, so the nightly upgrades and reboots stop there, and a rollout that was running pauses. Once you've fixed the cluster, resume or abort that rollout in the Buckle UI (<https://buckle.sphinx-map.ts.net>); a paused rollout blocks later config rollouts too.

## Ceph — HEALTH_ERR {#ceph-health_err}

**Fires:** a health check has been at HEALTH_ERR for 5 minutes. Critical. One alert per check, named in the summary.

1. See what the check is about:

   ```sh
   sudo cephadm shell -- ceph health detail
   ```

   It names the PGs, OSDs or daemons behind the check.
2. Act on what it names:
    - An OSD or mon down: see *Ceph — OSD down* and *Ceph — monitor out of quorum*.
    - `OSD_FULL` or `POOL_FULL`: writes have stopped. See *Ceph — OSD over 75% full*.
    - `PG_DAMAGED` (inconsistent PGs after a scrub): `ceph health detail` lists the PG ids.

!!! warning "Unverified"
    Nothing here has had a damaged PG yet. Ceph's tool for it is `ceph pg repair <pgid>` (it exists in this release's CLI), but nobody has run it on this cluster, and repairing before you know which copy is bad can spread the bad one. Read the OSD logs first.

**Check:** `ceph health detail` no longer shows the check at `[ERR]`; the alert resolves within a few minutes after.

## Ceph — HEALTH_WARN {#ceph-health_warn}

**Fires:** a health check has warned for 30 minutes. Warning. The three muted `AUTH_INSECURE_*` checks are left out of the rule by name.

1. Look at it:

   ```sh
   sudo cephadm shell -- ceph health detail
   ```

2. Typical ones:
    - `PG_DEGRADED` or undersized PGs after an OSD came back: recovery runs on its own. Watch `ceph -s` until all PGs are `active+clean`. If it doesn't move, an OSD is still down: *Ceph — OSD down*.
    - `RECENT_CRASH`: a daemon crashed and restarted. Read and acknowledge the crash:

      ```sh
      sudo cephadm shell -- ceph crash ls-new
      sudo cephadm shell -- ceph crash info <id>
      sudo cephadm shell -- ceph crash archive <id>
      ```

    - `MON_CLOCK_SKEW`: a mon's clock is off. `sudo cephadm shell -- ceph time-sync-status` shows by how much; fix the host's time sync ([Timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/)).
    - `OSD_NEARFULL` or `POOL_NEARFULL`: see *Ceph — OSD over 75% full*.
3. If the warning is deliberate and permanent, [mute it](mute-or-unmute-a-health-check.md) in the repo. Don't mute it by hand only: the alert reads the mgr's metrics, which keep reporting muted checks, so the rule's exclusion list has to change too.

**Check:** the check is gone from `ceph health detail`.

## Ceph — no cluster metrics {#ceph-no-cluster-metrics}

**Fires:** no `ceph_health_status` series from `cluster="homelab-ceph"` for 10 minutes. Critical. Fires on no data too. Either every mgr is down, the prometheus module is off, or Alloy on the storage Pis can't write to Mimir.

1. Does the cluster answer, and which mgr is active?

   ```sh
   sudo cephadm shell -- ceph -s
   sudo cephadm shell -- ceph mgr services
   ```

   `ceph -s` hangs or times out: the mons have no quorum. Check each host's mon unit ([Restart a daemon](restart-a-daemon.md)). `mgr:` shows no active mgr: start the mgr daemons.
2. Is the prometheus module on? `ceph mgr services` should list `"prometheus": "http://<active mgr's address>:9283/"`. If not:

   ```sh
   sudo cephadm shell -- ceph mgr module ls
   ```

   Buckle enables it (`ceph_mgr_modules` in [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml)) only when its resources script changes, so `sudo cephadm shell -- ceph mgr module enable prometheus` brings it back now.
3. On the host with the active mgr, the module should answer locally. Standbys answer with an empty body on purpose (`standby_behaviour: error`), and port 9283 isn't reachable between the hosts, so test on the host itself:

   ```sh
   curl -s http://localhost:9283/metrics | grep -m1 ceph_health_status
   ```

4. If the metrics are there, Alloy isn't shipping them. On that host:

   ```sh
   systemctl status alloy
   journalctl -u alloy --since -30min
   ```

   Alloy's own docs live with the [observability](https://backstage.k8s.specht-labs.de/docs/default/system/observability/) system.

**Check:** the *Exporters scraped* timeline on *Ceph - Status* turns green again and the stat panels fill.

## Ceph — OSD down {#ceph-osd-down}

**Fires:** an OSD has been down for 5 minutes. Warning. With three copies and `min_size` 2 the cluster still serves I/O with one OSD down; two down block writes (then *Ceph — placement groups inactive* follows).

1. On the host the alert names, look at the unit:

   ```sh
   sudo systemctl status ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@osd.<n>
   ```

2. The unit isn't running: start it ([Restart a daemon](restart-a-daemon.md)).
3. The unit runs but the OSD stays down: it can't reach the other hosts. Read its log, then check the tailnet:

   ```sh
   sudo cephadm logs --name osd.<n> -- --since -30min
   tailscale status
   systemctl status ceph-tailnet-route
   ```

4. The host itself is down or off the tailnet: the *Exporters scraped* row for it on *Ceph - Status* is red too. The OSD and mon alerts still fire because the other hosts report them. Get the host back (power, network), then come back here.
5. The NVMe is gone (`lsblk` shows no `nvme0n1`, or the kernel log shows I/O errors): see [Replace a failed OSD or host](replace-a-failed-osd-or-host.md). On 2026-11-18 NVMe drives dropped off the PCIe bus under load at Gen 3 and needed a power cycle; [Failure modes](../explanation/failure-modes.md) has the details.

**Check:** `sudo cephadm shell -- ceph osd tree` shows the OSD `up`, and `ceph -s` goes back to `HEALTH_OK` once recovery finishes.

## Ceph — placement groups inactive {#ceph-placement-groups-inactive}

**Fires:** some PGs haven't been active for 10 minutes. Critical. Data in them can't be read or written, so labk3s pods with `ceph-rbd` volumes hang on I/O. Usually fewer than `min_size` (2) OSDs hold those PGs, meaning two of three OSDs are down; sometimes PGs are stuck peering.

1. Which OSDs are down?

   ```sh
   sudo cephadm shell -- ceph osd tree
   sudo cephadm shell -- ceph pg dump_stuck inactive
   ```

2. Bring the OSDs back, one host at a time, with *Ceph — OSD down*.
3. If every OSD is up and PGs stay inactive, `ceph health detail` names the PGs and what they wait for.

**Check:** `ceph -s` shows every PG `active` (then `active+clean` after recovery).

## Ceph — monitor out of quorum {#ceph-monitor-out-of-quorum}

**Fires:** a mon has been out of quorum for 5 minutes. Warning. Two of three mons keep the cluster going; losing a second stops it.

1. On the host the alert names:

   ```sh
   sudo systemctl status ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@mon.<host>
   sudo cephadm logs --name mon.<host> -- --since -30min
   ```

2. Not running: start it ([Restart a daemon](restart-a-daemon.md)).
3. Running but out of quorum: check the clock first (`sudo cephadm shell -- ceph time-sync-status`, and `chronyc tracking` on the host). Then compare its address in the monmap with the host's tailnet address:

   ```sh
   sudo cephadm shell -- ceph mon dump
   tailscale ip -4
   ```

   They must match. A mon whose address changed won't start: that happens when the host was re-enrolled as a new Tailscale node. See [Replace a failed OSD or host](replace-a-failed-osd-or-host.md#the-host-got-a-new-tailnet-address).

**Check:** `ceph -s` lists all three mons in `quorum`.

## Ceph — OSD over 75% full {#ceph-osd-over-75-full}

**Fires:** an OSD has been over 75% full for 15 minutes. Warning. Ceph warns at 85% (nearfull) and stops writes at 95%. Every PG lives on all three OSDs, so they fill together: expect three alerts.

1. See where the space goes:

   ```sh
   sudo cephadm shell -- ceph df
   sudo cephadm shell -- ceph osd df
   ```

2. Pool `k3s` is labk3s's volumes. The *Ceph CSI (RBD)* dashboard lists volumes by size and use. Delete PVCs that aren't needed (`reclaimPolicy: Delete` removes the image with the PVC).
3. RGW pools (`default.rgw.buckets.data`): delete buckets or objects of user `experiments`.
4. If the data has to stay, add capacity: [Add a Ceph host](add-a-ceph-host.md).

**Check:** `ceph osd df` shows every OSD under 75%.

## Ceph — daemon not running {#ceph-daemon-not-running}

**Fires:** cephadm has reported a daemon as not running for 10 minutes. Warning. Covers every daemon cephadm deployed: mons, OSDs, mgrs (standbys too), RGW, crash, ceph-exporter. The value in the description is cephadm's status: 0 stopped, -1 error, 2 starting, -2 unknown. cephadm refreshes its inventory every few minutes, so this alert lags the others.

1. Several daemons on one host at once: the host or its Docker. Go to [Restart a daemon](restart-a-daemon.md#all-daemons-on-a-host-stopped).
2. One daemon:

   ```sh
   sudo systemctl status ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@<daemon>
   sudo cephadm shell -- ceph orch daemon restart <daemon>
   ```

3. Status `-1` (error) right after a restart: read the log with `sudo cephadm logs --name <daemon>`.

**Check:** `sudo cephadm shell -- ceph orch ps` shows the daemon `running`. The alert clears after cephadm's next refresh (`REFRESHED` column).

## Ceph CSI — no provisioner {#ceph-csi-no-provisioner}

**Fires:** no ceph-csi provisioner pod on labk3s reports `csi_liveness` for 5 minutes. Critical. Fires on no data too. New PVCs on `ceph-rbd` stay Pending, and attach and expand stop.

1. Look at the pods (always `--context labk3s`):

   ```sh
   kubectl --context labk3s -n ceph-csi-rbd get pods -l component=provisioner -o wide
   kubectl --context labk3s -n ceph-csi-rbd describe pod -l component=provisioner
   kubectl --context labk3s -n ceph-csi-rbd logs deploy/ceph-csi-rbd-provisioner -c csi-rbdplugin --tail=100
   ```

2. Pods aren't scheduled or keep crashing: check the Argo CD app `ceph-csi-rbd` on labk3s, and the labk3s nodes ([labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/)).
3. Pods run but the metric is missing: the `liveness-prometheus` container serves it. Check that container's log, and that k8s-monitoring scrapes job `ceph-csi-rbd/provisioner`.

**Check:** the *Provisioners live* stat on the *Ceph CSI (RBD)* dashboard shows 2.

## Ceph CSI — node plugin missing {#ceph-csi-node-plugin-missing}

**Fires:** fewer live node plugins than labk3s nodes for 10 minutes. Warning. Pods with `ceph-rbd` volumes can't start on the node without one (no mount or unmount).

Since labk3s moved to the tailnet (2026-11-26), the usual cause is a node plugin pod that's running but listening for metrics on an old address: it binds port 8681 to `POD_IP` once, at container start. Follow [Recover a ceph-csi node plugin](recover-a-ceph-csi-node-plugin.md).

**Check:** *Node plugins live* on *Ceph CSI (RBD)* equals the number of nodes (5 today).

## Ceph CSI — volume operations failing {#ceph-csi-volume-operations-failing}

**Fires:** create, delete, attach or expand calls have returned gRPC errors for 15 minutes. Warning.

1. The *Ceph CSI (RBD)* dashboard's *Errors* panel shows which method fails.
2. The provisioner's log says why:

   ```sh
   kubectl --context labk3s -n ceph-csi-rbd logs deploy/ceph-csi-rbd-provisioner -c csi-rbdplugin --tail=200
   ```

3. Common causes:
    - The Ceph cluster is unhealthy or unreachable: `ceph -s` on a storage Pi, then the Ceph alerts above.
    - A node can't map an image: the node's kernel log (`sudo dmesg | grep -i libceph` on the node). `libceph: Failed to parse secret: -524` means the client key is an aes256k key, which the nodes' kernel can't use ([Keys and ciphers](../explanation/keys-and-ciphers.md)).
    - The node can't reach the mons or OSDs on the tailnet: the node must carry `tag:ceph-client` ([Network and tailnet](../reference/network-and-tailnet.md)).

**Check:** the *Errors* panel goes flat.

## Ceph CSI — PVC over 85% full {#ceph-csi-pvc-over-85-full}

**Fires:** a PVC on `ceph-rbd` has been over 85% full for 15 minutes. Warning. The alert names namespace and PVC.

`ceph-rbd` expands volumes online (`allowVolumeExpansion: true`). Raise the PVC's `spec.resources.requests.storage` where it's defined, usually its app in SpechtLabs/k8s-deployment, and let Argo CD sync. For a PVC that isn't in git:

```sh
kubectl --context labk3s -n <namespace> patch pvc <pvc> \
  -p '{"spec":{"resources":{"requests":{"storage":"<new size>"}}}}'
```

!!! warning "Unverified"
    PVCs created from a StatefulSet's `volumeClaimTemplates` can't be resized through the template; patch the PVCs themselves. Nobody has resized one on this cluster yet.

**Check:** `kubectl --context labk3s -n <namespace> get pvc <pvc>` shows the new capacity, and the pod sees it (`df -h` inside it).
