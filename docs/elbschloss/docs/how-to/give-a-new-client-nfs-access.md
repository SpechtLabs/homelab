# Give a new client NFS access

Use this when another host or workload needs a folder on the NAS over NFS.

**Before you start:**

- The client is on the tailnet with an attribute tag that says what it is (for example
  `tag:buckle-server`), and it can mount NFS v4.1.
- Every NFS client looks like `127.0.0.1` to DSM, so DSM can't keep clients apart: once the
  policy lets a client reach `svc:nfs`, it can mount every folder that has a `127.0.0.1` rule.
  If that's not acceptable for this client, stop here and read
  [The NAS and Tailscale](../explanation/nas-and-tailscale.md#nfs-through-127001).
- Policy changes go through the catalog and Backstage's pull request, not by editing
  `tailscale/policy.hujson` ([Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)).

1. Grant the client `svc:nfs`. On the client's Backstage Component, add the NFS API and the tag
    its traffic comes from, like
    [modules/nas-backup/catalog-info.yaml](https://github.com/SpechtLabs/homelab/blob/main/modules/nas-backup/catalog-info.yaml)
    does:

    ```yaml
    metadata:
      annotations:
        specht-labs.de/tailnet-src: tag:<client-tag>
    spec:
      consumesApis:
        - api:nas-nfs
    ```

    Push to `main`. Backstage updates its pull request from the branch
    `backstage/tailnet-policy`; check it adds a grant from `tag:<client-tag>` to `svc:nfs` on
    `tcp:2049`, let the `tailscale` workflow's test pass, and merge it.

2. If the client needs a folder that isn't exported yet, add the export in DSM: Control Panel >
    Shared Folder > select the folder > Edit > NFS Permissions > Create. Set hostname or IP to
    `127.0.0.1`, the privilege and squash the client needs, and tick "Allow connections from
    non-privileged ports". For a folder under an exported one (like `/volume1/homelab/buckle`)
    skip this: the rule is per shared folder.

3. Record the export in the `api:nas-nfs` definition in
    [nas/catalog-info.yaml](https://github.com/SpechtLabs/homelab/blob/main/nas/catalog-info.yaml),
    one line per path with its rights and who uses it.

4. Mount it on the client:

    ```sh
    sudo mount -t nfs -o nfsvers=4.1 nfs.sphinx-map.ts.net:/volume1/<folder>/<path> /mnt/<where>
    ```

    On a Buckle host, put it in a module instead. For a nightly backup there's one already:
    add an entry to [vars/backups.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/backups.yaml),
    and `modules/nas-backup` mounts `/volume1/homelab/<folder>` for the run with
    `nfsvers=4.1,soft,timeo=150,retrans=3`.

## Check it worked

On the client:

```sh
findmnt /mnt/<where>
touch /mnt/<where>/.nfs-test && rm /mnt/<where>/.nfs-test
```

`findmnt` shows `nfs4` from `nfs.sphinx-map.ts.net`, and the write succeeds if you granted
read/write. On the NAS, `sudo cat /etc/exports` lists the folder with a `127.0.0.1(...)` entry.

## If it didn't

| Symptom | Likely cause |
|---|---|
| Mount hangs, then times out | No grant yet (Backstage's pull request not merged), or the NAS isn't serving `svc:nfs` ([Re-create the NAS's Tailscale serve config](recreate-the-nas-tailscale-serve-config.md)) |
| `access denied by server` | No `127.0.0.1` rule on that shared folder, or the serve forward names `localhost` (`::1`) instead of `127.0.0.1` |
| Mount works, writes fail | The rule's privilege or squash setting |
| Asked for NFS v3 | Not possible: `svc:nfs` carries only tcp:2049, and v3 needs the portmapper and mountd |
