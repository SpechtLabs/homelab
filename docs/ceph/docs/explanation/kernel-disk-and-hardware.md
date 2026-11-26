# Kernel, disk and hardware

## A 4K-page kernel on a Pi 5

The Pi 5's default kernel (`kernel_2712.img`) uses 16K pages. On it, BlueStore asserts while creating an OSD (`BlueFS::append_try_flush`, the check `p2aligned(pos1 ^ pos2, _page_size)`; seen with Ceph 20.2.5 on 2026-11-18). The Pi 5 can also boot `kernel8.img`, Raspberry Pi's v8 kernel with 4K pages, and BlueStore works there. So `vars/group-ceph.yaml` sets `rpi_kernel: kernel8.img`, which module `pi-firmware` writes into `config.txt`.

You can check on a host: `getconf PAGESIZE` prints `4096`, and `uname -r` ends in `-rpi-v8` (`6.12.115+rpt-rpi-v8` on 2026-11-26). Don't drop the setting to "simplify" the fleet; OSD creation breaks, and existing OSDs on 16K pages are untested territory.

## One disk for everything

Each Pi boots from its NVMe, and the OS install had grown root over the whole disk. Ceph wants a device of its own, so the disk got split: root shrunk to 64 GiB (10-15 GB were in use; the OS, container images and the mon store live there) and the rest became `nvme0n1p3`, 867 GiB.

A mounted ext4 can grow but not shrink, which is why the split runs from the initramfs, before root is mounted. `ceph-disk`'s action arms it by putting `shrinkroot=64G` on the kernel command line; the premount script takes the token off first, so a failure or a hang never turns into a boot loop. Each step leaves a bootable disk behind it.

The cost: the OSD and the OS share a drive. A dead NVMe takes the host's OS, mon store and OSD at once, and replacing it means reinstalling the host.

## The OSD sits on an LV

ceph-volume refuses partitions; it takes whole disks or LVs. Buckle makes VG `ceph` with LV `osd` over `nvme0n1p3`, and the OSD spec points at `/dev/ceph/osd`. The task only touches a blank partition (no filesystem or other signature, not in another VG) and never undoes anything. One more quirk: when OSD creation fails, ceph-volume wipes the LV, and the next Buckle run recreates it.

## Memory

8 GB per host has to hold a mon, a mgr (three in the cluster), an OSD, the crash collector, ceph-exporter and on storagepi-ceph2 RGW. cephadm's memory autotune landed below the OSD's 896 MiB minimum here, so autotune is off and `osd_memory_target` is 2 GiB.

## PCIe Gen 2

On 2026-11-18, at PCIe Gen 3 (what the old Ansible setup used), NVMe drives dropped off the bus under load: clusterpi-leader, storagepi-ceph1 and storagepi-ceph3 stopped doing I/O until power-cycled. Gen 2 is the Pi 5's certified speed, and `rpi_pciex1_gen: 2` (module `pi-firmware`) is the fleet default since. Raise it only per host, and watch it.
