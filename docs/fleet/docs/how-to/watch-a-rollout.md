# Watch a rollout

Use this after a merge to `main`, a Renovate automerge, or a nightly schedule, when you want to see
where the change is and whether it's healthy.

**Before you start:** access to <https://buckle.sphinx-map.ts.net>, or the API set up as in
[Call the Buckle API](call-the-buckle-api.md).

1. Open **Rollouts** in the UI. Each commit the server has seen is a row, newest first, with a
   three-word name (`wet.left.talk`) and its state. Scheduled runs sit between the commits with an
   alarm clock, named after their schedule. A rejected commit shows its validation errors and
   never rolls out.

    From a terminal, the same list:

    ```sh
    curl -s -b "$J" "$B/api/v1/rollouts" | python3 -c '
    import json, sys
    for r in json.loads(sys.stdin.read(), strict=False)["items"][:8]:
        print(r["name"], r["state"], r["revision"][:8], r["triggered_by"])'
    ```

    `triggered_by` is `controller` for a commit and `schedule:<name>` for a schedule.

2. Open the rollout. The pipeline shows `canary`, `core`, `fleet` and `stragglers` as stages, each
   host as a block coloured by its state. Per phase:

    ```sh
    curl -s -b "$J" "$B/api/v1/rollouts/wet.left.talk" | python3 -c '
    import json, sys
    r = json.loads(sys.stdin.read(), strict=False)
    print(r["name"], r["state"], "phase", r["current_phase"], "done", r["hosts_done"], "of", r["hosts_total"], "failed", r["hosts_failed"])
    for p in r["phases"]:
        print(" ", p["name"], p["state"])
        for h in p.get("hosts", []):
            print("    ", h["host"], h["state"], "changes", h["plan_changes"])'
    ```

    The path takes the rollout's name or its id. `hosts_total` is 18: the 17 hosts and the
    `labk3s` cluster.

3. Read a host's plan before or while it applies: expand its row under **Targets**. Hosts whose
   plan changes nothing go healthy within seconds; hosts with `changes` above 0 apply, may
   reboot (`rebooting`), and then wait for their required health checks for up to 2 min
   (`settle`).

4. On a host, for the agent's side of it:

    ```sh
    ssh pi@blade-pi1 "bash -c 'sudo buckle status | head -20'"   # last run, every step
    ssh pi@blade-pi1 "bash -c 'sudo buckle health'"              # the applied modules' checks, now
    ssh pi@blade-pi1 "bash -c 'sudo journalctl -u buckle-agent -e --no-pager | tail -50'"
    ```

    Log in as `pi` on the Pis, `cedi` on isa, the NUC and timepi, `root` on meet
    ([Hosts and phases](../reference/hosts.md)).

## Check it worked

The rollout's state is `completed`, `hosts_failed` is 0, and the commit shows as the stable
revision. `sudo buckle status` on a host prints `revision  applied <commit> · stable <commit>`.

## If it didn't

- State `paused`: a host failed or a health check stayed red past `settle`. Go to
  [Fix a paused rollout](fix-a-paused-rollout.md).
- State `detected` for a new commit while an older rollout sits `paused`: the older one blocks it
  (`supersede: latest` finishes the current rollout first). Fix or abort the paused one.
- A host stays `plan_pending`: its agent is offline. It moves to `stragglers` and converges when it
  reconnects.
- A host stays `held`: it was unhealthy before its wave (`health.baseline: hold`) and waits for you
  to force or skip it.
- Row and rollout states are listed in [Rollout policy](../reference/rollout-policy.md#states).
