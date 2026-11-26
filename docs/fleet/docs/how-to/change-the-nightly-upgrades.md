# Change the nightly upgrades

Use this to check how last night's package upgrades and kernel reboots went, to move them, or to
stop them for a while. Two schedules in
[`schedules/`](https://github.com/SpechtLabs/homelab/tree/main/schedules) run every night,
Europe/Berlin time:

| Schedule | When | Runs |
|---|---|---|
| `nightly-upgrades` | 03:00 | `base: upgrade` on every host; reboots only where the upgrade installed a newer kernel |
| `nightly-kernel-reboots` | 05:30 | `base: reboot-if-required` on every host; reboots where a newer kernel is installed than the one running |

Both go through the normal phases (blades together, `core` two at a time, then `fleet` with one
Ceph host and one k3s node at a time, nodes drained around their reboot) with `approval: auto`.

## See how last night went

1. In the UI, **Schedules**: each schedule with its next run and how its latest went. A
   schedule's page lists the hosts it picks and every run it started or skipped.
2. From the API:

    ```sh
    curl -s -b "$J" "$B/api/v1/schedules/nightly-upgrades" | python3 -m json.tool | less
    ```

3. A failed host pauses that night's rollout like any other: [Fix a paused rollout](fix-a-paused-rollout.md).
   Aborting it is fine; the next night runs it again.

## Move or change a schedule

1. Edit the file, e.g. `cron: "0 3 * * *"` in `schedules/nightly-upgrades.yaml`. Keep
   `nightly-kernel-reboots` after the upgrades are done (they take up to the 2 h `window`), and
   both after the NAS backups at 02:00 Berlin (`nas-backup.timer`).
2. `mise run validate` checks the cron expression, the time zone and that `base` declares the
   action. PR, merge.
3. The server runs the **stable** revision's schedules, so the change takes effect once its commit
   has rolled out completely.

## Stop them for a while

There's no pause switch for a schedule. Either:

- delete (or move out of `schedules/`) the file in a commit, and restore it later; or
- abort tonight's rollout once it has started (**Rollouts**, the alarm-clock row, **Abort…**).

An occurrence that finds another rollout under way waits up to its `window` (2 h), then is
skipped; after a server outage only the latest missed occurrence starts, and only within its
window.

## Check it worked

```sh
curl -s -b "$J" "$B/api/v1/schedules" | python3 -c '
import json, sys
for s in json.loads(sys.stdin.read(), strict=False): print(s["name"], s["cron"], s["timezone"], "next", s["next_at"])'
```

shows the new cron and the next run (in UTC).
