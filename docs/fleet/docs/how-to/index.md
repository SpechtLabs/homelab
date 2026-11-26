# How-to guides

Rollouts and actions

- [Call the Buckle API](call-the-buckle-api.md): sign in from a terminal, the CSRF helper the other pages use.
- [Watch a rollout](watch-a-rollout.md): where a change is, per phase and per host.
- [Fix a paused rollout](fix-a-paused-rollout.md): retry, skip, waive a check, roll back or abort.
- [Run an action on a host](run-an-action-on-a-host.md): upgrade packages or reboot one host now.
- [Reboot a k3s or Ceph host](reboot-a-k3s-or-ceph-host.md): the same as an action rollout, drained and one at a time.
- [Pause a host for manual work](pause-a-host-for-manual-work.md): keep drift correction off while you test by hand.
- [Change the nightly upgrades](change-the-nightly-upgrades.md): last night's result, moving or stopping the schedules.

Hosts

- [Enrol a new host](enrol-a-new-host.md): tailnet tag, agent install, repo changes.
- [Update a host's fixture](update-a-host-fixture.md): refresh the facts CI plans against.
- [Retag or rename a host](retag-or-rename-a-host.md): keep `tag:buckle-agent`, rename in two pushes.
- [Retire a host](retire-a-host.md): take a machine out of the fleet.

Changing the config

- [Upgrade Buckle](upgrade-buckle.md): Renovate for minors, server first by hand for majors.
- [Bump a pinned version](bump-a-pinned-version.md): k3s, Alloy, tsidp and the rest in `vars/versions.yaml`.
- [Add or change a secret](add-or-change-a-secret.md): a file on isa plus a reference in `buckle.yaml`.
- [Add a module](add-a-module.md): the skeleton, how to test it, the gotchas.

The server

- [Respond to a backup alert](respond-to-a-backup-alert.md): the nightly database backup to the NAS.
- [Restore the server database](restore-the-server-database.md): put a backup back.
- [Sign in when tsidp is down](sign-in-when-tsidp-is-down.md): the break-glass server on localhost.
- [Move the server to another host](move-the-server-to-another-host.md): the 2026-11-23 NUC to isa recipe.
