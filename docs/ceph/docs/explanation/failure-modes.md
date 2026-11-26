# Failure modes seen so far

What has actually gone wrong since the cluster was built, newest first, and what changed because of it.

## 2026-11-26: node plugin metrics on a stale address

labk3s moved from the LAN to the tailnet: every node's node IP changed. *Ceph CSI — node plugin missing* fired although every node plugin pod was running. The node plugin runs in the host network and binds its metrics port (8681) to `POD_IP`, which it reads once at container start, so it kept listening on the old LAN address and the scrapes failed. Volumes were fine the whole time.

The fix was to delete the node plugin pods one node at a time; kernel rbd mappings survive that. `kubectl rollout restart` would have been worse: it changes the DaemonSet's pod template, Argo CD's selfHeal reverts the change, and the pods roll twice. Any future change to how the labk3s nodes connect needs the same restart afterwards. [Recover a ceph-csi node plugin](../how-to/recover-a-ceph-csi-node-plugin.md).

## 2026-11-25: Docker restart left a host's daemons down for 7 hours

The nightly `base/upgrade` installed a new docker-ce on storagepi-ceph1. Docker restarted and was back within 8 seconds, but its restart had stopped every container with SIGTERM, the Ceph daemons exited 0, and cephadm's units (`Restart=on-failure`) counted that as a clean stop. The mon, mgr and OSD on storagepi-ceph1 stayed down for 7 hours. The cluster kept serving on two copies.

Two changes came out of it:

- Buckle's drop-in `ceph-<fsid>@.service.d/buckle-restart.conf` with `Restart=always`. Proven afterwards with `systemctl restart docker`: everything was back in about 20 seconds.
- The alerts went per instance, with the host in the title: the old "one OSD is down" didn't say which one.

A second effect showed up the same night. The failed `cluster` health gate paused the nightly action rollout, and a paused rollout blocks later config rollouts too (they sit in state `detected`) until someone resumes or aborts it in the Buckle UI. After any Ceph outage, look for a paused rollout.

## 2026-11-18: BlueStore on 16K pages

Creating the first OSD failed with a BlueStore assertion in `BlueFS::append_try_flush` on the Pi 5's default 16K-page kernel. The storage Pis boot `kernel8.img` (4K pages) since. [Kernel, disk and hardware](kernel-disk-and-hardware.md).

## 2026-11-18: aes256k keys and the Pi kernels

While ceph-csi went in: Tentacle issues `aes256k` keys, and the labk3s nodes' kernel rbd can't read them (`libceph: Failed to parse secret: -524`). `client.k3s` has an `aes` key since, with the matching mon setting and three muted warnings. [Keys and ciphers](keys-and-ciphers.md).

## 2026-11-18: NVMe off the bus at PCIe Gen 3

Under load, the NVMe drives in clusterpi-leader, storagepi-ceph1 and storagepi-ceph3 dropped off the PCIe bus and stopped doing I/O until power-cycled. The fleet runs PCIe Gen 2 since. If an OSD vanishes together with its disk, power-cycle the host before you suspect the drive.

## Things that bite when you work on it

- `cephadm shell` reads stdin. In `ssh host bash -s <<EOF` it swallows the rest of the heredoc; give it `</dev/null`. Nested SSH quoting breaks easily: copy a script over and run it with `cephadm shell --mount /tmp:/mnt:ro -- sh /mnt/x.sh`.
- Buckle evaluates a `command.run` task's `unless` guard when it makes the plan, before templates are written. That's why the specs and resources apply through handlers as well as guarded tasks.
- Mons refuse quorum on clock skew. The storage Pis run ptp4l and chrony against timepi ([Timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/)).
- The mgr exports muted health checks as active. Every new mute has to go into the alert rule and the status dashboard as well as the vars ([Mute or unmute a health check](../how-to/mute-or-unmute-a-health-check.md)).
