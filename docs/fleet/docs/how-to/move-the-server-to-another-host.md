# Move the server to another host

Use this when the Buckle server has to leave isa: new hardware, a reinstall, a failing disk. The
move from the NUC to isa on 2026-11-23 went this way, with about two minutes without a control
plane and no effect on the hosts. Agents dial `svc:buckle`, not a host, so they follow the Service
by themselves.

**Before you start:**

- The new host is enrolled as a Buckle agent ([Enrol a new host](enrol-a-new-host.md)) and you can
  SSH to both hosts. Host-to-host SSH over the tailnet is refused by the policy (Tailscale SSH), so
  copy between them over their LAN addresses with `ssh -A` from your Mac.
- No rollout running.
- Its tailnet IPv4 (`tailscale ip -4` on it). Below, `<old>` is isa and `<new>` the new host.

1. Prepare the repo in a PR, but don't merge yet:
    - `bootstrap/server.yaml` and `bootstrap/server-breakglass.yaml`: add `<new>`'s tailnet IP to
      `agents.trusted_proxies` (keep the old one until the move is done).
    - `buckle.yaml`: point the id-based roles at `<new>`: `buckle-server` (its backups of the
      database and secrets follow the group, `vars/backups.yaml`), and whichever of
      `o11y-collector`, `tsidp`, `nut-server` move with it; the `core` phase's list.
    - The tailnet policy (via the
      [tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)):
      `<new>` needs `tag:buckle-server` (approver of `svc:buckle`, and its access to `svc:nfs` for
      the backup) and, for sign-in, tsidp access as a relying party.
2. Stage the server on `<new>`. The binary at the fleet's version is already there
   (`/usr/local/bin/buckle`, the agent's). Copy `server.env` and the secrets from `<old>`, leaving
   `<new>`'s own `agent.yaml` alone (both hosts need passwordless sudo for this):

    ```sh
    ssh -A cedi@<old> "sudo tar -C /etc/buckle -cf - server.env secrets | ssh <user>@<new-lan-ip> 'sudo tar -C /etc/buckle -xf -'"
    ```

    Then install the config and units from the PR's branch, and set `BUCKLE_LISTEN_ADDR` in
    `/etc/buckle/server.env` to `<new>`'s tailnet IP:

    ```sh
    scp bootstrap/server.yaml bootstrap/server-breakglass.yaml bootstrap/*.service <user>@<new>:/tmp/
    ssh <user>@<new>
    bash
    sudo install -m 0644 /tmp/server.yaml /tmp/server-breakglass.yaml /etc/buckle/
    sudo install -m 0644 /tmp/buckle-server.service /tmp/buckle-server-breakglass.service /etc/systemd/system/
    sudoedit /etc/buckle/server.env          # BUCKLE_LISTEN_ADDR=<new's tailnet IP>
    sudo systemctl daemon-reload
    ```

    Don't start it yet.
3. Give `<new>` the tag `tag:buckle-server` in the admin console, and check the policy change from
   step 1 is live.
4. Stop the old server and take `svc:buckle` off it:

    ```sh
    ssh cedi@<old> "bash -c 'sudo tailscale serve drain svc:buckle && sudo systemctl disable --now buckle-server'"
    ```

    From here the control plane is down; agents keep running.
5. Copy the data directory with the server stopped, over the LAN:

    ```sh
    ssh -A cedi@<old> "sudo tar -C /var/lib -cf - buckle-server | ssh <user>@<new-lan-ip> 'sudo tar -C /var/lib -xf -'"
    ```

6. Start the server on `<new>` and serve the Service there, both ports:

    ```sh
    ssh <user>@<new>
    bash
    sudo systemctl enable --now buckle-server
    ip=$(tailscale ip -4)
    sudo tailscale serve --bg --service=svc:buckle --https=443 "http://$ip:7701"
    sudo tailscale serve --bg --service=svc:buckle --tcp=7700 --proxy-protocol=2 "tcp://$ip:7700"
    ```

    A host that advertises the Service without serving every defined port gets no traffic, so run
    both commands.
7. Merge the PR from step 1. The rollout installs `nas-backup` on `<new>` and removes it from
   `<old>`, along with any other role that moved. The first night's copies on `<new>` continue
   the same NAS folders.
8. Once every agent is back, drop `<old>`'s IP from `trusted_proxies` (by hand on `<new>`, and in
   the repo) and remove `tag:buckle-server` from `<old>`.

## Check it worked

```sh
curl -s https://buckle.sphinx-map.ts.net/readyz
ssh <user>@<new> "bash -c 'tailscale serve status; systemctl is-active buckle-server'"
```

`/readyz` answers 200, `serve status` lists `svc:buckle` with `tcp:443` and `tcp:7700`, and the
Hosts page shows every host online within a minute or two. The next night's backup alert stays
quiet ([Respond to a backup alert](respond-to-a-backup-alert.md) if not).

## If it didn't

- Agents log PROXY header errors or show up under the wrong identity: `<new>`'s tailnet IP is
  missing from `agents.trusted_proxies`.
- `svc:buckle` gets no traffic on `<new>`: the host lacks `tag:buckle-server` (the policy
  auto-approves the Service for that tag only), or one port isn't served.
- Going back: stop the server on `<new>` and drain its Service, then start it on `<old>` and run the
  two `serve` commands there. The data directory on `<old>` is as you left it at step 4, minus
  whatever happened on `<new>` since.
