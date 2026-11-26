# Add an S3 user

Use this when something needs its own S3 credentials on the cluster's gateway, `http://storagepi-ceph2.sphinx-map.ts.net:7480`.

**Before you start:** RGW is for experiments (Backstage lifecycle `experimental`): one gateway, no TLS, no grant for anyone but admins. Tailnet clients other than admins can't reach port 7480 today; `tag:ceph-client` is explicitly denied it in the policy tests.

1. Add the user to `ceph_rgw_users` in [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml), uid and display name:

   ```yaml
   ceph_rgw_users:
     experiments: S3 experiments
     <uid>: <display name>
   ```

2. Push to `main`. Buckle's `resources` step on `storagepi-ceph1` runs `radosgw-admin user create` for any uid that doesn't exist yet.
3. Get the keys, on any storage Pi:

   ```sh
   sudo cephadm shell -- radosgw-admin user info --uid=<uid>
   ```

   `keys[0].access_key` and `secret_key` are the credentials. Keep them out of git, or in SOPS.

## Check it worked

```sh
sudo cephadm shell -- radosgw-admin user list
```

The list has your uid (next to `experiments` and `dashboard`, the user the mgr dashboard made for itself).

## If it didn't

The `resources` step's output is in the Buckle run for `storagepi-ceph1`. To reach the gateway from somewhere other than an admin's device, the consumer needs a tailnet grant to `tag:ceph` on tcp:7480; today the `ceph-s3` API in [`modules/ceph/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/catalog-info.yaml) has no `specht-labs.de/tailnet-*` annotations, so Backstage renders no grant for it. Removing a user from the vars doesn't delete it: `radosgw-admin user rm --uid=<uid>` by hand (stock radosgw-admin, not run on this cluster yet).
