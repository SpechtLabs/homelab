# Pause a host for manual work

Use this before you change a host by hand in a way Buckle would undo: testing a hotfix to a file
a module owns, stopping a service it keeps running, debugging with a modified config. Every agent
re-plans its applied revision every 15 minutes and corrects drift, so a hand edit to a managed file
lasts at most that long on an active host.

A paused host stays in the fleet but rollouts skip it and its agent stops correcting drift. Actions
are refused while it's paused.

**Before you start:** the API with `bpost` ([Call the Buckle API](call-the-buckle-api.md)), or
the host's page in the UI (**Pause…** / **Resume**).

1. Pause it:

    ```sh
    bpost hosts/meet/pause '{}'
    ```

    The response is the host's summary with `"status":"paused"`.
2. Do your work. Rollouts that start now leave the host out; it catches up later.
3. Put what you want to keep into the repo, or undo your hand changes. On resume, the next drift
   pass (or rollout) puts every managed file back to the repo's version.
4. Resume it:

    ```sh
    bpost hosts/meet/resume '{}'
    ```

## Check it worked

```sh
curl -s -b "$J" "$B/api/v1/hosts/meet" | python3 -c '
import json, sys; print(json.loads(sys.stdin.read(), strict=False)["status"])'
```

prints `paused` after step 1 and `active` after step 4. On the host, `sudo buckle plan` shows what
drift correction would change back.

## If it didn't

- `Target 'meet' is Paused; it cannot be paused.` (or the reverse): it already was. Check who
  paused it in the audit log (`GET /api/v1/audit`) before resuming someone else's pause.
- Narrower option: Buckle can suspend one module on one host instead of the whole host
  (**Suspend…** on the module's row of the host page). Nobody has used it in this homelab yet.
