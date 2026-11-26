# Get the NUC off its end-of-life Ubuntu

Use this to deal with the NUC's Ubuntu 24.10, which is end of life. `archive.ubuntu.com`
dropped it, which broke every `apt-get update` (found during the migration to Buckle,
2026-11-17/18). Since then
`/etc/apt/sources.list.d/ubuntu.sources` points at `old-releases.ubuntu.com` by hand (the
original is `ubuntu.sources.bak-20261118`). apt works, the nightly upgrades run, but there are
no security updates.

**Before you start:** `ssh cedi@nuc`. The NUC is a plain host since isa took over on
2026-11-23: a Buckle agent, `nut-client` (early shutdown), time sync over NTP, Alloy, and
Incus plus Docker that nothing in the repo manages. No Service and no other host depends on
it. Check that's still true for Incus and Docker before you wipe anything:

```sh
ssh cedi@nuc "bash -c 'sudo incus list; sudo docker ps'"
```

Two ways out. The README asks for the first; the second is simpler if nothing on it matters.

## Option A: reinstall on Ubuntu 26.04 LTS

1. Save what you want from Incus and Docker.
2. Install Ubuntu 26.04 LTS. Keep the hostname `nuc`.
3. Remove the old `nuc` device from the tailnet, then join the new install by hand with
   `tag:buckle-agent`, so it gets the name `nuc` again.
4. Enrol it with Buckle as in the [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/).
   Buckle keys the host by its tailnet name, so `vars/host-nuc.yaml` (`admin_user: cedi`), the
   `nut-client` group and the `core` phase pick it up unchanged.
5. Refresh its facts fixture, `fixtures/facts/nuc.json`, the way the Fleet docs describe.

The CPU is a Celeron without AVX (x86-64-v2). Buckle 2.14.0 crashed on it with `SIGILL`, which
is why CI runs `buckle validate` on an emulated Nehalem; that check keeps mattering after the
reinstall.

!!! warning "Unverified: in-place upgrade"
    `do-release-upgrade` from 24.10 would have to go through 25.04 and 25.10, all past their
    support. Nobody has tried it on this box.

## Option B: retire the NUC

Everything in the repo that names it:

| File | What to change |
|---|---|
| [buckle.yaml](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml) | `nut-client`: drop `\|\| host.id == "nuc"`; `core` phase: drop `"nuc"`; the `host.id == "nuc"` vars entry |
| [vars/host-nuc.yaml](https://github.com/SpechtLabs/homelab/blob/main/vars/host-nuc.yaml) | delete |
| [fixtures/facts/nuc.json](https://github.com/SpechtLabs/homelab/blob/main/fixtures/facts/nuc.json) | delete |
| [catalog/hardware.yaml](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml) | the `nuc` Resource |
| [bootstrap/server.yaml](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/server.yaml), `server-breakglass.yaml` | `100.122.149.90` in `trusted_proxies` (a leftover from the server move); the live copy on isa too |
| [tailscale/policy/policy.yaml](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/policy.yaml), [ssh-tests.yaml](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/ssh-tests.yaml) | the `nuc` host and its SSH and port tests; Backstage re-renders `policy.hujson` |
| `.github/workflows/validate.yml`, `mise.toml`, `renovate.json` | the Nehalem check exists for the NUC; decide whether to keep it |
| comments in modules, the README, `schedules/nightly-upgrades.yaml` | "the NUC" mentions |

Then remove the agent from Buckle ([Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/)),
the device from the tailnet, and switch the box off.

## Check it worked

Option A:

```sh
ssh cedi@nuc "bash -c 'lsb_release -ds; grep -h URIs /etc/apt/sources.list.d/ubuntu.sources'"
```

`Ubuntu 26.04... LTS` and `archive.ubuntu.com` (not `old-releases`). In Buckle the host is
healthy, and on isa `upsc -c ups@localhost` lists 16 again (15 secondaries and isa's primary).

Option B: `buckle validate` passes (`mise run validate`), and `upsc -c ups@localhost` on isa
lists 15 (14 secondaries and isa's primary).

## If it didn't

Enrolment trouble and agent versions: [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/).
