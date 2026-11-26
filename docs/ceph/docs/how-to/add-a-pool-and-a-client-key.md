# Add a pool and a client key

Use this when something new needs RBD images of its own: a second Kubernetes cluster, a VM host, a test.

**Before you start:** you change [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml) and push to `main`. Buckle renders `/etc/ceph/buckle/resources.sh` on `storagepi-ceph1` and runs it in `cephadm shell` whenever the file changes. The script only creates and sets: taking an entry out later removes nothing from the cluster.

1. Add the pool to `ceph_rbd_pools`:

   ```yaml
   ceph_rbd_pools: [k3s, <pool>]
   ```

   The script creates it (`ceph osd pool create`) with the cluster defaults (3 copies, `min_size` 2, PG autoscaler on) and runs `rbd pool init` on it.
2. Add the client to `ceph_clients`, with the key type and its caps:

   ```yaml
   ceph_clients:
     k3s:
       ...
     <name>:
       key_type: aes256k
       caps:
         mon: profile rbd
         osd: profile rbd pool=<pool>
         mgr: profile rbd pool=<pool>
   ```

   Pick `key_type` by who maps the images. Kernel rbd on the Pi kernels (6.6, 6.12), which is what ceph-csi uses, can't parse `aes256k` keys: give such clients `aes`. Userspace clients (librbd) can stay on `aes256k`, Tentacle's default. [Keys and ciphers](../explanation/keys-and-ciphers.md) explains why.
3. For per-image metrics on the RBD dashboards, add the pool to `mgr/prometheus/rbd_stats_pools` under `ceph_config.mgr` (comma-separated, today `k3s`).
4. Push. The rollout reaches `storagepi-ceph1` and runs the script at the end of that host's run.
5. Read the key, on any storage Pi:

   ```sh
   sudo cephadm shell -- ceph auth get-key client.<name>
   ```

   An `aes` key starts with `AQ`, an `aes256k` key with `Ag`. Put it in the client's secret (SOPS in k8s-deployment, never in this repo).

## Check it worked

```sh
sudo cephadm shell -- ceph osd pool ls detail
sudo cephadm shell -- ceph auth get client.<name>
```

The pool is there with `application rbd`; the client has the caps you set.

## If it didn't

- The run fails at the `resources` step with `client.<name> has a key of another type than ...`: the client already existed with a key of the other type. Buckle won't rotate it, because that breaks every holder of the old key. [Rotate a client key](rotate-a-client-key.md).
- A second `aes` client raises no warning: `AUTH_INSECURE_CLIENT_KEY_TYPE` is muted for good because of `client.k3s`. Keep the list of `aes` clients in this file honest.
- To remove a pool or client, do it by hand (`ceph osd pool rm`, `ceph auth rm`) after taking it out of the vars. Pool deletion needs `mon_allow_pool_delete`, which is off.

!!! warning "Unverified"
    Nobody has removed a pool or client from this cluster yet; the last point is Ceph's standard behaviour, not something tried here.
