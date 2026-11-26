# Schedules

Files under [`schedules/`](https://github.com/SpechtLabs/homelab/tree/main/schedules); the file
name is the schedule's name. The server runs the **stable** revision's schedules.

| Schedule | `cron` | `timezone` | Action | `approval` | `window` | `note` |
|---|---|---|---|---|---|---|
| `nightly-upgrades` | `0 3 * * *` | Europe/Berlin | `base: upgrade` | `auto` | `2h` | Nightly package upgrades |
| `nightly-kernel-reboots` | `30 5 * * *` | Europe/Berlin | `base: reboot-if-required` | `auto` | `2h` | Nightly reboots for pending kernels |

Neither sets `select`, so both run on every host offering the action (all 17), through the rollout
phases and module limits: blades together, `core` two at a time, then one Ceph host and one k3s
node at a time, each node drained around its reboot.

Behaviour that matters here:

- `approval: auto`: unattended. A failed host still pauses that night's rollout
  (`on_failure: pause`).
- `window: 2h`: an occurrence that finds another rollout under way waits up to 2 h, then is
  skipped. A push at 03:00 delays the upgrades; after 05:00 that night's run is skipped.
- After a server outage only the latest missed occurrence starts, and only inside its window.
- Their rollouts appear on **Rollouts** with an alarm clock, `triggered_by: schedule:<name>` in
  the API.

Related timer outside Buckle's schedules: `nas-backup.timer` on isa and clusterpi-leader, 02:00
Europe/Berlin, up to 5 min random delay, so the backups are done before the upgrades start
([Backups](backups.md)).

API: `GET /api/v1/schedules`, `GET /api/v1/schedules/<name>`.
