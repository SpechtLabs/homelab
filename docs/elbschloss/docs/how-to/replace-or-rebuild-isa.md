# Replace or rebuild isa

Use this when isa's hardware fails, or you reinstall it, or its roles move to another box. isa
runs four roles; this page covers moving all of them. Why they're together, and what's down
while they move, is in [isa, and why so much runs on it](../explanation/isa.md).

**Before you start:**

- If the old isa still runs, keep it running until the new one serves everything. The Buckle
  server's move costs about two minutes without a control plane; hosts aren't affected.
- Copy between hosts over the LAN (`ssh -A` from your machine): Tailscale SSH refuses
  host-to-host logins.
- The new host needs Ubuntu, passwordless sudo for `cedi` (`/etc/sudoers.d/90-cedi` on isa,
  made by hand; the dotfiles installer needs it), and Tailscale.

1. **Name and tags.** Join the new host to the tailnet by hand ("Add an agent" can't mint
   tagged keys). Give it the tags isa carries: `tag:buckle-agent`, `tag:buckle-server`,
   `tag:nut-server`, `tag:o11y-collector`, `tag:tsidp-client`. Each one opens a grant or an
   auto-approval the roles need ([Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)).

2. **The host id.** The groups `buckle-server`, `tsidp`, `nut-server` and `o11y-collector`,
   the `core` phase and `vars/host-isa.yaml` all select `host.id == "isa"` in
   [buckle.yaml](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml). Rebuilding
   under the same name: remove the old `isa` device from the tailnet first, or the new one
   becomes `isa-1`. A new name: change those references in one commit, and add the new host's
   tailnet IP to `agents.trusted_proxies` in
   [bootstrap/server.yaml](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/server.yaml).

3. **Buckle server.** Follow "Moving the server to another host" in
   [bootstrap/README.md](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/README.md)
   and the [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/). It
   moves `/etc/buckle` with the secrets in `/etc/buckle/secrets/`, which the NUT passwords are
   part of, and the database. If the old disk is gone, the newest database is on the NAS in
   `/volume1/homelab/buckle/`.

4. **tsidp.** Stop `tsidp` on the old host and copy its state directory `/data` (mode 0700,
   root) to the new host before Buckle starts tsidp there. It holds the `idp` node's key, the
   signing key `oidc-key.json` and the registered clients in `oidc-funnel-clients.json`.
   Without it tsidp comes up as a new node and every relying party (Buckle, DSM's `synology`
   client, Grafana, Argo CD, Backstage) has to be registered again. Keep the node name `idp`:
   the issuer and the email claims come from it.

    !!! warning "Unverified"
        Nothing backs up `/data`, and moving it hasn't been written down before. This step
        follows from what the directory holds
        ([modules/tsidp/module.yaml](https://github.com/SpechtLabs/homelab/blob/main/modules/tsidp/module.yaml):
        `tsidp_state_dir: /data`, never removed by Buckle).

5. **NUT.** Nothing to copy. Once the host is in `nut-server`, the module installs `nut`,
   writes the config and serves `svc:nut` (tcp:3493). On Ubuntu 26.04 the first apply can fail
   because the package's postinst starts upsd with an empty config; retry the host. On the old
   host, take it out of the Service so clients don't land on a dead upsd:

    ```sh
    sudo tailscale serve drain svc:nut
    ```

    The module's serve task has `removal: leave`, so leaving the group doesn't remove it.

6. **Collector.** Nothing to copy: `o11y-collector` brings the OTLP receiver, the NAS scrapes
   and the probes ([vars/group-o11y-collector.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/group-o11y-collector.yaml)).
   Anything that sends OTLP to isa by name or address must follow; see the
   [Observability docs](https://backstage.k8s.specht-labs.de/docs/default/system/observability/).

7. **Backup to the NAS.** Nothing on the NAS changes: `tag:buckle-server` grants `svc:nfs`, and
   DSM's rule is for `127.0.0.1` whichever host mounts.

## Check it worked

On the new host:

```sh
upsc ups@localhost ups.status        # OL
upsc -c ups@localhost                # one 127.0.0.1 line per client, 15 in total
sudo tailscale serve get-config --all   # svc:buckle and svc:nut
systemctl is-active tsidp alloy buckle-server nut-server nut-monitor
```

From a Pi: `upsc ups@nut.sphinx-map.ts.net ups.status` prints `OL`. From your machine:
`curl -s https://idp.sphinx-map.ts.net/.well-known/openid-configuration` returns the issuer,
and `https://buckle.sphinx-map.ts.net` lets you sign in. The six availability probes report
again in Grafana ([Monitoring](../reference/monitoring.md)). The next night,
`/volume1/homelab/buckle/` on the NAS gets a new `buckle-nightly-<date>.db`.

## If it didn't

- NUT clients still fail `ups-reachable`: [Check the UPS and the NUT chain](check-the-ups-and-the-nut-chain.md).
- Agents don't reconnect, or the Buckle UI won't load: [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/).
- A Service shows "required ports are missing": the host isn't serving every port of its
  definition ([Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)).
