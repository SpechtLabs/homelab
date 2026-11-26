# Restore tsidp

Use this when tsidp on isa lost its state: sign-in through `https://idp.sphinx-map.ts.net` fails
for every relying party (Buckle, Backstage, the k8s clusters), clients are gone, or isa was
rebuilt. The `tsidp` backup is a nightly tarball of tsidp's state directory `/data`
([Backups](../reference/backups.md)):

| File in `/data` | What losing it costs |
|---|---|
| `oidc-key.json` | The OIDC signing key: every relying party's tokens stop validating; everyone signs in again once it's back or replaced |
| `oidc-funnel-clients.json` | The registered OIDC clients (Buckle's from dynamic registration and the rest): each would have to register again and its relying party get the new ID and secret |
| `tailscaled.state`, `profile-data/` | The `idp` node's tailnet identity: without it tsidp joins as a new node and needs an auth key |
| `certs/` | TLS certificates for `idp.sphinx-map.ts.net`; reissued on demand |

!!! danger "Root-only"
    The tarball holds the signing key and every client secret. Extract it as root, on isa only.

!!! warning "Unverified"
    Nobody has restored tsidp from this backup yet. The steps follow from what's in `/data` and
    how `modules/tsidp` runs it (`tsidp -dir /data`).

**Before you start:** SSH to isa as `cedi`; the Buckle API or UI to pause isa
([Pause a host for manual work](pause-a-host-for-manual-work.md)). Without the pause, the agent's
drift pass restarts the `tsidp` unit you stopped within 15 minutes. If tsidp being down is why
you can't sign in to Buckle, use the break-glass server
([Sign in when tsidp is down](sign-in-when-tsidp-is-down.md)).

1. Pause isa in Buckle (`bpost hosts/isa/pause '{}'`, or **Pause…** on its page).
2. Pick the copy: `sudo ls -lt /var/backups/tsidp/`, or mount the NAS folder `tsidp` as in
   [Restore the Buckle secrets](restore-the-buckle-secrets.md), step 1.
3. Stop tsidp and set the current state aside:

    ```sh
    ssh cedi@isa
    bash
    sudo systemctl stop tsidp
    sudo mv /data /data.broken-$(date +%Y%m%d%H%M%S)
    ```

4. Unpack the copy; the tarball's top directory is `data/`:

    ```sh
    sudo tar -C / -xzf /var/backups/tsidp/tsidp-nightly-<date>.tar.gz
    sudo ls -la /data
    ```

    To restore only the key or the clients, extract into `/root/tsidp-restore` instead and copy
    that one file into the old `/data` (moved back in place) with `install -m 0600`.
5. Start it and resume isa:

    ```sh
    sudo systemctl start tsidp
    ```

    `bpost hosts/isa/resume '{}'`.

## Check it worked

```sh
curl -s https://idp.sphinx-map.ts.net/.well-known/openid-configuration | head -c 200
ssh cedi@isa "bash -c 'sudo buckle health | grep tsidp'"
```

The discovery document has an `issuer`, `tsidp/unit` and `tsidp/discovery` pass, and signing in to
<https://buckle.sphinx-map.ts.net> works.

## If it didn't

- tsidp logs that it needs to log in: the node's tailnet identity is gone (the `idp` machine was
  removed from the tailnet). It needs a new auth key with `tag:tsidp`, through the
  [tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/).
- A relying party still fails after the restore: its client was registered after the backup.
  Register it again with tsidp's dynamic client registration and update the relying party (for
  Buckle: `OIDC_CLIENT_ID`/`OIDC_CLIENT_SECRET` in `/etc/buckle/server.env`, then restart
  `buckle-server`).
