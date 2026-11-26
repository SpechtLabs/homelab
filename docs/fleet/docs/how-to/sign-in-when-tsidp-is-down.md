# Sign in when tsidp is down

Use this when <https://buckle.sphinx-map.ts.net> can't sign you in because tsidp
(`https://idp.sphinx-map.ts.net`, also on isa) is down, and you need the UI or API now: a paused
rollout to fix, an action to run. Existing sessions stop working within the hour, because Buckle
revalidates them against tsidp. Agents and rollouts don't depend on tsidp and keep going.

The break-glass server is the same binary and database with
`/etc/buckle/server-breakglass.yaml`: no sign-in, UI and API on `127.0.0.1:7701` only, agents
unaffected. Starting it stops `buckle-server` (`Conflicts=`); stopping it, or 4 hours passing
(`RuntimeMaxSec=4h`), starts `buckle-server` again.

**Before you start:** SSH to isa as `cedi`. It doesn't need tsidp: Tailscale SSH or the LAN
(192.168.0.118) both work.

!!! warning "Drift found on 2026-11-26"
    isa's copy of `server-breakglass.yaml` still had the NUC-era values: `source.git.url`
    `cedi/homelab`, the retired `allowed_tags` (`tag:homelab`, `tag:core-infra`,
    `tag:core-services`) and `join.server_url` on the NUC. Under it, every agent (they carry
    only `tag:buckle-agent` of those) would be refused. Run step 1 before every use until the
    repo copy has been installed on isa.

1. Check that isa's break-glass config matches the repo. It's installed by hand and can drift:

    ```sh
    cd ~/src/gh/cedi/homelab
    ssh cedi@isa "bash -c 'sudo cat /etc/buckle/server-breakglass.yaml'" | diff - bootstrap/server-breakglass.yaml
    ```

    No output means it matches. If it differs, install the repo's copy first:

    ```sh
    scp bootstrap/server-breakglass.yaml cedi@isa:/tmp/
    ssh cedi@isa "bash -c 'sudo install -m 0644 /tmp/server-breakglass.yaml /etc/buckle/server-breakglass.yaml'"
    ```

2. Start the break-glass server:

    ```sh
    ssh cedi@isa sudo systemctl start buckle-server-breakglass
    ```

3. Tunnel to it and open <http://localhost:7701>:

    ```sh
    ssh -L 7701:127.0.0.1:7701 cedi@isa
    ```

    Whoever reaches that port is admin. For the API, use `B=http://localhost:7701` and the
    `bpost` helper from [Call the Buckle API](call-the-buckle-api.md) without signing in.
4. Do what you came for.
5. Go back to the normal server:

    ```sh
    ssh cedi@isa sudo systemctl stop buckle-server-breakglass
    ```

## Check it worked

While break-glass runs: `ssh cedi@isa systemctl is-active buckle-server-breakglass buckle-server`
prints `active` then `inactive`, and `curl -s http://localhost:7701/readyz` through the tunnel
answers 200. After step 5 both flip back, and <https://buckle.sphinx-map.ts.net/readyz> answers
200 again.

## If it didn't

- `buckle-server` doesn't come back after stop: `sudo systemctl start buckle-server` and read
  `journalctl -u buckle-server-breakglass -u buckle-server -n 50`.
- tsidp itself: it's a `tsidp` module on isa (`systemctl status tsidp`, health checks
  `tsidp/unit` and `tsidp/discovery`). Who may sign in (`buckle-admins` claim for
  `group:admins`) is in the tailnet policy, not here.
