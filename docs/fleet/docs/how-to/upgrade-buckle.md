# Upgrade Buckle

Use this when a Buckle release is out: a Renovate PR named `buckle` for a minor or patch, or a new
major (Renovate never proposes those).

Two pins move together: `buckle_version` in
[`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml) (what
the `buckle` module installs on every host, server included) and `"github:SierraSoftworks/buckle"`
in [`mise.toml`](https://github.com/SpechtLabs/homelab/blob/main/mise.toml) (the CLI CI validates
with).

## Minor and patch releases

1. Let Renovate do it. It waits three days after the release, then opens the PR and merges it
   itself once every check passes. `validate.yml` runs `buckle validate` with the new CLI, and again
   under an emulated x86-64-v2 CPU, because 2.14.0's amd64 build crashed the NUC with SIGILL.
2. The merge rolls out like any change. `modules/buckle` runs `buckle update --to <version>` on
   each host (one GitHub API call per host) and restarts the agent 90 s after the run, from a
   transient `buckle-upgrade-<version>` unit, so the run reports first. Order: the four blades,
   then `core` two at a time (isa restarts `buckle-server` and its agent together), then `fleet`.
3. Both pins arrive in one PR. Renovate's own mise manager reports the `mise.toml` pin as
   `github:SierraSoftworks/buckle`, so `renovate.json` names it in the `buckle` group and the
   three-day wait; before that, 2.22.2 reached `mise.toml` alone on 2026-11-26 while the fleet
   stayed on 2.22.0. If they ever differ again, bump the one behind by hand.

### Check it worked

```sh
curl -s -b "$J" "$B/api/v1/hosts" | python3 -c '
import json, sys
for h in json.loads(sys.stdin.read(), strict=False): print(h["id"], h["agent_version"], h["connection"])'
ssh cedi@isa "bash -c 'buckle --version'"
```

Every host reports the new version a couple of minutes after its phase. The `buckle` module's
`buckle-restart-stale` step catches a host whose restart didn't happen: on the next run it
restarts any unit still running the replaced binary.

## Major releases

The canary blades would otherwise upgrade before the server, and a protocol break there takes the
control plane down. So the server goes first, by hand.

**Before you start:** the release notes read; SSH to isa as `cedi`; no rollout running (check
**Rollouts**; the controller resumes rollouts after a restart, but a quiet moment is easier to
verify).

1. Back up the database on isa:

    ```sh
    ssh cedi@isa "bash -c 'sudo sqlite3 /var/lib/buckle-server/buckle.db \".backup /var/backups/buckle/buckle-pre-<version>-\$(date +%Y%m%d%H%M%S).db\"'"
    ```

2. Replace the binary and restart the server:

    ```sh
    ssh cedi@isa "bash -c 'sudo buckle update --to <version> && sudo systemctl restart buckle-server'"
    ```

3. Watch it come up and migrate:

    ```sh
    ssh cedi@isa "bash -c 'sudo journalctl -u buckle-server -n 50 --no-pager'"
    curl -s https://buckle.sphinx-map.ts.net/readyz
    ```

    `/readyz` answers 200 once the database, the rollout controller and the agent listener work;
    503 names what doesn't. Agents reconnect by themselves (the **Needs attention** bell lists
    those on another version).
4. Bump `buckle_version` and the `mise.toml` pin in one PR, `mise run validate`, merge. The rollout
   upgrades the agents through the phases. On isa the binary is already current, but the agent
   still runs the old one, so `buckle-restart-stale` restarts both units there once more.
5. Raise `agents.minimum_agent_version` in `bootstrap/server.yaml` (and `server-breakglass.yaml`)
   only after every host runs the new version; the server refuses older agents. That file is
   installed by hand ([Server and agents](../reference/server-and-agents.md)).

### If it didn't

- The server doesn't start after a schema change: go back with `sudo buckle update --to <old>`
  and a restart. A release that changes the schema leaves `buckle.db.schema-N` next to the
  database for seven days; the old version restores it and sets the newer database aside.
  Whatever the new version recorded meanwhile is lost; agents report their state again.
- Past seven days, restore the backup from step 1:
  [Restore the server database](restore-the-server-database.md).
