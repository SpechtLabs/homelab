# Add a Ceph host

Use this to grow the cluster with a fourth storage Pi, or to bring a rebuilt host back in.

**Before you start:** the new Pi runs Raspberry Pi OS from its NVMe (root on `nvme0n1p2`, ext4, boot on `nvme0n1p1`), is on the tailnet with `tag:ceph`, and runs a Buckle agent. Enrolling a host in Tailscale and Buckle belongs to the [Fleet](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/) and [Tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) docs. Its Buckle host id must match `storagepi-ceph*`: that's what puts it in group `ceph` ([`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml)).

1. Add the host and its tailnet IPv4 to `ceph_hosts` in [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml), and push to `main`. Do this first: module `ceph` runs on every host in group `ceph`, and its `ceph-tailnet-route` unit is rendered from the host's entry there.

   ```sh
   tailscale ip -4     # on the new host
   ```

   ```yaml
   ceph_hosts:
     storagepi-ceph1: 100.105.212.35
     storagepi-ceph2: 100.107.71.68
     storagepi-ceph3: 100.118.224.54
     storagepi-ceph4: 100.x.y.z
   ```

   The rollout's run on the new host installs lvm2, cephadm, the sshd on port 2222 with cephadm's key for root, and `ceph-tailnet-route`. On `storagepi-ceph1` it re-renders `/etc/ceph/buckle/cluster.yaml` and applies it: the host joins with labels `_admin, mon, mgr, osd`, and cephadm places a mon at its tailnet address, a mgr, a crash collector and ceph-exporter.
2. Split its NVMe. On the host's page in the Buckle UI, run the action **Split the NVMe for Ceph** (module `ceph-disk`, action `shrink-root`). It asks for confirmation, arms the initramfs and reboots; the shrink runs before root is mounted.
   Afterwards, on the host:

   ```sh
   cat /boot/firmware/shrinkroot.log
   lsblk
   ```

   You should see `nvme0n1p2` at 64G and a new `nvme0n1p3` over the rest. The script refuses (and boots normally) if root uses more than half of 64 GiB, if root isn't partition 2, or if the disk is split already; the log says which.
3. The next Buckle run on the host creates LV `ceph/osd` on `nvme0n1p3`; `sudo lvs ceph/osd` shows it. cephadm's OSD spec (`osd.nvme`, path `/dev/ceph/osd`) then puts an OSD on it.
4. Add a `Resource` for the host in [`catalog/hardware.yaml`](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml) (system `ceph`), and the host to `appliesTo` of `tag-ceph` in [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml).

## Check it worked

```sh
sudo cephadm shell -- ceph orch host ls
sudo cephadm shell -- ceph orch ps storagepi-ceph4
sudo cephadm shell -- ceph -s
```

The host is listed with its tailnet address, its daemons run, and `ceph -s` shows 4 mons and 4 OSDs. Data rebalances onto the new OSD for a while.

## If it didn't

- No mon on the new host: cephadm can't see the host's tailnet address in `public_network`. Check the route, then make cephadm look again:

  ```sh
  ip route show table main dev tailscale0      # must show <ip> scope link src <ip>
  sudo cephadm shell -- ceph orch device ls --refresh
  ```

- No OSD: `sudo lvs ceph/osd` on the host. Buckle creates the LV only on a blank `nvme0n1p3`; a partition with another signature is refused and the run says so. A failed OSD creation makes ceph-volume wipe the LV; the next Buckle run recreates it.
- cephadm can't reach the host: it connects as root to `<host>.sphinx-map.ts.net` on port 2222. `sudo sshd -T | grep -i port` on the host, and the `tag:ceph` grant for tcp:2222.

!!! warning "Unverified"
    All three hosts joined on 2026-11-18, while the cluster was new and empty. Adding a fourth to the running cluster follows from the module's design but hasn't been done, and how soon cephadm picks up the LV once it appears is untested (`ceph orch device ls --refresh` makes it look again). Also check the alert rules and the *Ceph - Status* dashboard for anything that assumes three hosts.
