# Known issues

Checked on 2026-11-26. The first two come from the README's list (found during the migration,
2026-11-17/18, not caused by it); the rest turned up since.

## The NUC runs an end-of-life Ubuntu

Still true. The NUC is on Ubuntu 24.10, which `archive.ubuntu.com` dropped, breaking every
`apt-get update`. `/etc/apt/sources.list.d/ubuntu.sources` points at `old-releases.ubuntu.com` by
hand (the original is `ubuntu.sources.bak-20261118`). apt works and the nightly upgrades run, but
there are no security updates. The fix is a move to 26.04 LTS. Since isa took over its roles on
2026-11-23 the NUC is a plain host, so the urgency dropped.

## GitHub's anonymous API limit

Each `github.release` task and each `buckle update` spends one anonymous GitHub API call; the limit
is 60 an hour per IP, and every host at home shares one IP. `tsidp` and `rpi-exporter` moved to
`file.download` of the release asset after the rpi_exporter 1.0.11 bump used up an hour and left
the Ceph Pis unable to plan. `k3s-server` and `k3s-agent` still use `github.release`, and the
`buckle` module calls `buckle update` once per host per upgrade. Fine in steady state; a release
that touches many hosts at once can hit the limit, and the phases are what spread it out.

## Kubernetes drains don't wait for the pods

Buckle 2.22's drain evicts the node's pods once and carries on without waiting for them to leave,
so `deadline: 10m` doesn't bound anything yet. cedi's SierraSoftworks/buckle#908 makes the drain
re-evict and wait until the node is empty; once it's released, upgrade the fleet.

## The break-glass config on isa is stale

Found while writing these docs: `/etc/buckle/server-breakglass.yaml` on isa differs from
`bootstrap/server-breakglass.yaml`. It still has `source.git.url` `cedi/homelab`, `allowed_tags`
`tag:homelab`, `tag:core-infra`, `tag:core-services` (all retired) and the NUC as
`join.server_url`. Started as it is, it would refuse every agent. Fix: install the repo copy
([Sign in when tsidp is down](../how-to/sign-in-when-tsidp-is-down.md), step 1).
`server.yaml` matches the repo.

## Renovate splits the Buckle bump

The `buckle` group in `renovate.json` is meant to move `buckle_version` and the CLI pin in
`mise.toml` in one PR. On 2026-11-26 it didn't: PR #19 bumped only `mise.toml` to 2.22.2, named
after the dependency `github:sierrasoftworks/buckle`, so the CLI and CI validate with 2.22.2 while
the fleet runs 2.22.0. The `mise.toml` line seems to be picked up by Renovate's own mise manager,
which neither matches the group's `depName` nor waits the 3-day release age. Until that's fixed,
bump `buckle_version` by hand when only `mise.toml` moved.

## Smaller ones

- **Add an agent doesn't work.** It needs a Tailscale OAuth client to mint tagged keys, and
  `provisioning` is commented out in `server.yaml`. New hosts join the tailnet by hand
  ([Enrol a new host](../how-to/enrol-a-new-host.md)).
- **`server.yaml`'s comment on `allowed_tags` is wrong.** It says other nodes "wait in the UI";
  with `allowed_tags` set, Buckle refuses untagged nodes outright.
- **Fixtures carry old tags.** `fixtures/facts/*.json` still list `tag:homelab` and friends; no
  selector reads tags, so plans don't change, but a refresh would make them honest.
- **Comments that still say NUC.** `validate.yml`'s Nehalem step says the server runs on the NUC
  (it's isa; the NUC's agent is why the check still matters), `bootstrap/README.md`'s install and
  enrol commands use v2.15.0 and the NUC's address, and `buckle-backup.timer`'s comment puts the
  upgrades at 02:00 (they're at 03:00 Berlin). The timer itself fires at 01:30 UTC, which is 03:30
  in Berlin summer time, after the upgrades start.
- **apt calls die after 30 minutes.** Buckle's apt timeout isn't configurable. A long
  dist-upgrade on an SD card (clusterpi-worker2, 361 packages, 2026-11-19) got killed mid-configure;
  `base`'s `dpkg-repair` step now finishes such a state on the next run.
- **Ubuntu 26.04's `nut` packages start upsd with an empty config** before Buckle writes it, so the
  first apply of `nut-server` on a fresh host can fail. Retry passes.
- **Removing a module can fail on its own restart handler** for a unit it just deleted ("Unit not
  found"). Retry the host.
