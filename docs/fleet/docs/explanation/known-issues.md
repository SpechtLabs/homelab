# Known issues

Checked on 2026-11-26, updated 2026-11-27. The first two come from the README's list (found during the migration,
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

## The break-glass config on isa is stale

Found while writing these docs (2026-11-26): `/etc/buckle/server-breakglass.yaml` on isa differs
from `bootstrap/server-breakglass.yaml`. It still has `source.git.url` `cedi/homelab`,
`allowed_tags` `tag:homelab`, `tag:core-infra`, `tag:core-services` (all retired) and the NUC as
`join.server_url`. Started as it is, it would refuse every agent. The repo copy is current
(since 2026-11-27 it also trusts only isa as a proxy); installing it is a hand step
([Sign in when tsidp is down](../how-to/sign-in-when-tsidp-is-down.md), step 1).

## The NAS's ACLs can open up backup files

The Buckle database copy the old backup wrote to the NAS on 2026-11-26 over NFS v4.1 shows as
`-rwxrwxrwx` on the NAS, while the two copies before it, written over NFS v3, are `-rw-------`. The
`homelab` share carries Synology ACLs, and DSM applies them over the mode the client asks for.
`nas-backup` now sets 0600 after each copy, but whether DSM honours that over NFS v4.1 is
unverified: check `ls -l` on the NAS after the first night, and keep each backup folder's DSM
permissions to the admin account. The backups hold secrets.

## Smaller ones

- **Add an agent doesn't work.** It needs a Tailscale OAuth client to mint tagged keys, and
  `provisioning` is commented out in `server.yaml`. New hosts join the tailnet by hand
  ([Enrol a new host](../how-to/enrol-a-new-host.md)).
- **A comment that still says NUC.** `validate.yml`'s Nehalem step still names the NUC's CPU;
  that's still why it matters (the NUC runs an agent), though the server is on isa now.
- **apt calls die after 30 minutes.** Buckle's apt timeout isn't configurable. A long
  dist-upgrade on an SD card (clusterpi-worker2, 361 packages, 2026-11-19) got killed mid-configure;
  `base`'s `dpkg-repair` step now finishes such a state on the next run.
- **Ubuntu 26.04's `nut` packages start upsd with an empty config** before Buckle writes it, so the
  first apply of `nut-server` on a fresh host can fail. Retry passes.
- **Removing a module can fail on its own restart handler** for a unit it just deleted ("Unit not
  found"). Retry the host.
