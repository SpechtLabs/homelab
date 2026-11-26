# Open the Ceph dashboard

Use this when you want Ceph's own web UI (the mgr dashboard), or need to reset its admin password.

**Before you start:** the dashboard runs on the active mgr, on port 8443 at that host's tailnet address. Admins reach it; `tag:ceph-client` is denied it. Which mgr is active changes (on 2026-11-26 it was storagepi-ceph2), so ask the cluster.

1. Find the active mgr's URL, on any storage Pi:

   ```sh
   sudo cephadm shell -- ceph mgr services
   ```

   ```json
   {
       "dashboard": "https://100.107.71.68:8443/",
       "prometheus": "http://100.107.71.68:9283/"
   }
   ```

2. Open the `dashboard` URL from an admin device and sign in as `admin`. The certificate comes from cephadm's own CA (`cephadm-root-<fsid>`), so the browser warns. The initial password was in the bootstrap action's output (2026-11-18).

## Reset the admin password

`ac-user-set-password` reads the password from a file, and `cephadm shell` runs in a container, so mount the file in:

```sh
mkdir -m 0700 /tmp/dash
printf '%s' '<new password>' > /tmp/dash/pw
sudo cephadm shell --mount /tmp/dash:/mnt/dash:ro -- ceph dashboard ac-user-set-password admin -i /mnt/dash/pw
rm -r /tmp/dash
```

## Check it worked

The sign-in with the new password works. If the URL doesn't answer, the mgr may just have failed over: run `ceph mgr services` again.
