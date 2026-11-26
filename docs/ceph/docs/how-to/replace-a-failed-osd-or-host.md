# Replace a failed OSD or host

Use this when an OSD's NVMe has died, or a storage Pi has to be rebuilt from scratch.

**Before you start:** on these hosts the NVMe holds the OS as well as the OSD (root on `nvme0n1p2`, the OSD on `nvme0n1p3`), so a new NVMe means a new OS install: replacing the disk and rebuilding the host are the same job. The other two hosts keep every PG at two copies meanwhile. There's no fourth host to recover onto, so the PGs stay undersized until the new OSD is in; a second failure in that window blocks writes.

!!! warning "Unverified"
    No OSD or host has been replaced on this cluster yet. The repo's modules cover preparing the new host (disk split, LV, cephadm access, the spec). The Ceph-side removal and the mon re-add below use stock cephadm commands that exist in this release's CLI but haven't been run here. Read `ceph orch osd rm -h` before you start, and go slowly.

## First, make sure it's the disk

An OSD that's down with a healthy disk only needs a restart: [Respond to a Ceph alert: OSD down](respond-to-a-ceph-alert.md#ceph-osd-down). The disk is gone if `lsblk` on the host shows no `nvme0n1`, or the kernel log shows NVMe I/O errors or the controller dropping off the bus. On 2026-11-18 three NVMe drives (two of them in storage Pis) dropped off at PCIe Gen 3 and came back after a power cycle; the fleet runs Gen 2 since (`rpi_pciex1_gen` in [`modules/pi-firmware`](https://github.com/SpechtLabs/homelab/blob/main/modules/pi-firmware/module.yaml)). Power-cycle once before you order a drive.

## Replace the host

1. Note the OSD id that lived on the host (`osd.0` on storagepi-ceph1, `osd.1` on -ceph3, `osd.2` on -ceph2 as of 2026-11-26):

   ```sh
   sudo cephadm shell -- ceph osd tree
   ```

2. Take the old OSD out of the cluster, keeping its id for the replacement:

   ```sh
   sudo cephadm shell -- ceph orch osd rm <id> --replace
   sudo cephadm shell -- ceph orch osd rm status
   ```

3. Install the OS on the new NVMe with the same host name and enrol it in Tailscale (`tag:ceph`) and Buckle ([Fleet](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/)).
4. If the host came back with a different tailnet address, do [The host got a new tailnet address](#the-host-got-a-new-tailnet-address) now.
5. Continue with [Add a Ceph host](add-a-ceph-host.md) from step 2 (split the NVMe): the host is still in `ceph_hosts` and in cephadm's host list, so Buckle prepares it and cephadm puts its daemons back, the OSD on the new LV.

## The host got a new tailnet address

A new Tailscale node gets a new 100.x address. The monmap stores mon addresses, and a mon whose address changed won't start, so the host's mon has to be re-added at the new address. Everything that lists the mons by IP needs the new one too:

- `ceph_hosts` in [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml): the mon placement (`host:ip`) and `ceph-tailnet-route` come from it.
- `csiConfig[].monitors` in k8s-deployment [`apps/ceph-csi-rbd/cluster/labk3s/helm-values.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/ceph-csi-rbd/cluster/labk3s/helm-values.yaml) (by IP, because labk3s's DNS can't resolve the storage Pis).
- The `ceph-rbd` API definition in [`modules/ceph/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/catalog-info.yaml).

!!! warning "Unverified"
    How the old mon leaves the monmap isn't settled. With the spec updated, cephadm should redeploy the mon at the new address; if the old entry stays in `ceph mon dump`, `ceph mon rm <name>` drops it while the other two keep quorum. Check `ceph mon dump` after each step and never let the count of reachable mons fall below two.

## Check it worked

```sh
sudo cephadm shell -- ceph -s
sudo cephadm shell -- ceph osd tree
sudo cephadm shell -- ceph mon dump
```

Three mons in quorum at the addresses in `ceph_hosts`, three OSDs up, PGs back to `active+clean` once backfill finishes.
