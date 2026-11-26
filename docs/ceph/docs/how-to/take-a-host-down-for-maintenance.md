# Take a host down for maintenance

Use this to reboot a storage Pi outside the nightly runs, or to power one off for hardware work (NVMe, PoE HAT, cabling).

**Before you start:** one host at a time, never two. With one host down every PG still has two copies (`min_size` 2) and labk3s keeps working; with two down, writes stop. You need SSH to the host and the Buckle UI (<https://buckle.sphinx-map.ts.net>).

The nightly runs need none of this: `base/upgrade` (03:00) and `base/reboot-if-required` (05:30) reboot the Ceph hosts one at a time, because module `ceph` has `parallel: 1` and that limit counts every change on a Ceph host, reboots from `base` or `pi-firmware` included. Each host's `cluster` health check holds the next one until the cluster has every OSD and mon back and no degraded data.

1. Check the cluster is healthy and the host's OSD can stop:

   ```sh
   ssh pi@storagepi-ceph2
   sudo cephadm shell -- ceph -s
   sudo cephadm shell -- ceph osd tree          # which OSD lives on this host
   sudo cephadm shell -- ceph osd ok-to-stop osd.<n>
   ```

   `ok-to-stop` should say the OSD can stop without PGs going inactive. Don't go on while anything is degraded.
2. Keep Ceph from marking the OSD out while it's away (by default it does after 10 minutes, `mon_osd_down_out_interval` 600):

   ```sh
   sudo cephadm shell -- ceph osd set noout
   ```

3. Take the host down.
    - Reboot: run the action **Reboot** (module `base`) from the host's page in the Buckle UI, or `sudo reboot` on the host.
    - Hardware work: `sudo poweroff`, do the work, power it on.
4. Expect alerts while it's down: OSD down and monitor out of quorum after 5 minutes, daemon not running after 10, HEALTH_WARN after 30. They're about this host; nothing to do for them.
5. When it's back, wait for its mon and OSD:

   ```sh
   sudo cephadm shell -- ceph -s
   ```

   3 mons in quorum, 3 OSDs up. PGs show `degraded` for a while and then go `active+clean`.
6. Clear the flag:

   ```sh
   sudo cephadm shell -- ceph osd unset noout
   ```

## Check it worked

`ceph -s` shows `HEALTH_OK` (with the three muted checks) and no `noout flag(s) set` warning. `sudo /usr/local/sbin/ceph-buckle-health` prints `ok HEALTH_OK`.

## If it didn't

- The daemons didn't come back after the boot: [Restart a daemon](restart-a-daemon.md#all-daemons-on-a-host-stopped).
- The NVMe isn't there after the boot: [Replace a failed OSD or host](replace-a-failed-osd-or-host.md).
- A Buckle rollout ran into the downtime: the host's health check failed past the 2-minute settle time and the rollout paused. A paused rollout also holds later config rollouts (they sit in state `detected`). Once the cluster is healthy, resume or abort it in the Buckle UI; the [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/) cover rollouts.

!!! warning "Unverified"
    cephadm also has `ceph orch host maintenance enter <host>` / `exit <host>`, which stops the host's daemons and sets the flags itself. Nobody has used it on this cluster, and how it interacts with Buckle's restart drop-in and the health gate is untested. The steps above stick to a cluster flag and a plain reboot.
