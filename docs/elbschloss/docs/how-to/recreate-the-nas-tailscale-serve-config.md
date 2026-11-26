# Re-create the NAS's Tailscale serve config

Use this after the Tailscale package on the NAS was uninstalled and reinstalled, or when
`nas.sphinx-map.ts.net`, `stream.`, `node-exporter.` or `nfs.` stops answering while the NAS
itself is fine on the LAN.

**Before you start:** `ssh -J cedi@nyx king@nas.local`. The device must be called
`nas-elbschloss` on the tailnet and carry `tag:nas` (to serve the four Services) and
`tag:tsidp-client` (for DSM's SSO). A reinstall makes a new device; rename and tag it in the
admin console first ([Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)).

1. Look at what's served now:

    ```sh
    sudo /var/packages/Tailscale/target/bin/tailscale serve get-config --all
    ```

    Compare with the config in [Synology NAS](../reference/nas.md#serve-config). If it matches,
    the serve config isn't the problem.

2. Serve every port of every Service. Each Service must get all of its ports, or the NAS drops
    out of it ("required ports are missing"):

    ```sh
    ts=/var/packages/Tailscale/target/bin/tailscale
    sudo $ts serve --service=svc:nas --https=443 https+insecure://localhost:5001
    sudo $ts serve --service=svc:nas --tcp=5001 tcp://localhost:5001
    sudo $ts serve --service=svc:nas --tcp=6690 tcp://localhost:6690
    sudo $ts serve --service=svc:stream --https=443 http://localhost:8096
    sudo $ts serve --service=svc:node-exporter --tcp=9100 tcp://localhost:9100
    sudo $ts serve --service=svc:nfs --tcp=2049 tcp://127.0.0.1:2049
    ```

    Use `127.0.0.1` for NFS, not `localhost`: on the NAS that's `::1`, and DSM's NFS rule for
    `127.0.0.1` won't match ("access denied by server").

3. Check:

    ```sh
    sudo $ts serve get-config --all
    ```

    Four Services, six endpoints, as in the reference.

The policy's `autoApprovers` approve the NAS's advertisements for `tag:nas`; there's nothing
to approve by hand. tailscaled keeps this config across reboots and package updates.

## Check it worked

From your machine (an admin):

```sh
curl -s -o /dev/null -w "%{http_code}\n" https://nas.sphinx-map.ts.net/
curl -s https://stream.sphinx-map.ts.net/health
```

`200` and `Healthy`. From isa, the collector's view:

```sh
ssh cedi@isa "bash -c 'curl -s http://node-exporter.sphinx-map.ts.net:9100/metrics | grep -c ^node_'"
```

A count in the hundreds (470 on 2026-11-26). NFS gets used by isa's nightly backup at 01:30
UTC; the `buckle-backup-stale` alert fires if it fails for 26 h.

## If it didn't

- `svc:nas` still empty after serving: the Service definition in the admin console may list a
  port the NAS doesn't serve. The definitions are `svc:nas` tcp:443, 5001, 6690; `svc:stream`
  tcp:443; `svc:node-exporter` tcp:9100; `svc:nfs` tcp:2049.
- `http://nas.sphinx-map.ts.net` gets nothing by design: `svc:nas` has no port 80.
- Background: [The NAS and Tailscale](../explanation/nas-and-tailscale.md).
