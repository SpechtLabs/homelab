# From Ansible to Buckle

Until November 2026 the homelab ran from `homelab-ansible`: an inventory, vaulted secrets,
playbooks run over SSH with `--ask-pass`, a fork of `k3s-ansible`. It was disliked and partly
broken (`site.yml` imported a `metrics-collector.yml` that didn't exist). The goal for its
replacement was a cluster-manager-style, declarative fleet with Tailscale built in, and the
migration treated Buckle as a redesign, not a port. The full design record, written on 2026-11-17
before the build, is [`docs/buckle-migration.md`](https://github.com/SpechtLabs/homelab/blob/26d76a6/docs/buckle-migration.md);
this page keeps what still explains today's setup.

## What went away

| Ansible | Buckle |
|---|---|
| `inventory/homelab.yaml`, hand-kept `raspberry_pi_4`/`_5` groups, a 60-line regex parser for the Pi model | Groups from facts (`host.facts.hardware.raspberry_pi.*`, script facts) |
| SSH with per-host users and `--ask-pass` | Agents dial the server; identity is the tailnet node |
| `ansible-vault` blobs, NUT passwords in plain text | Secrets as files on the server, fingerprinted in plans; the NUT passwords were rotated in the move |
| `serial: 1`, `k3s-upgrade.yml`, `k3s-reboot.yml` | Phases, module `parallel`, health gates, node drains |
| `--check` | `buckle validate` with per-host fixtures in CI, and the live plan in each rollout |
| No drift detection | Every agent re-plans every 15 min and corrects drift |
| Removing a role does nothing | Removing a task removes what it created (`removal: cleanup`) |
| The vaulted `tailscale_authkey` | Gone; hosts keep their Tailscale install and tags |

## Decisions that shaped the repo

- **Alloy on every host.** The old collector scraped 16 hosts by name and 11 Tailscale exporters by
  hard-coded IP, and Buckle templates can't read other hosts' data. Each host now runs Alloy,
  scrapes itself and ships directly; Alloy's embedded node_exporter replaced the standalone one,
  keeping `job="node_exporter"` and `instance="<host>:9100"` so dashboards didn't notice.
- **The NAS stays out.** DSM isn't Debian and Buckle has no container lifecycle; its compose files
  live in `nas/` and deploy through DSM.
- **k3s reset isn't ported.** A `command.run` with `remove:` runs whenever its rendered command
  changes, so a refactor could wipe the cluster. Resetting k3s is a manual job.
- **Lists can't be templated.** Buckle coerces rendered strings to scalars, so `pi-firmware` uses
  one task per hardware concern with literal lists rather than a generated include file.
- **Ansible's leftovers were removed by the modules that replaced them** (old apt `.list` files,
  `k3s*.service.env`, the standalone node_exporter), each with `removal: leave` so they never come
  back, instead of a separate cleanup module.

## How it went live

| Date | Step |
|---|---|
| 2026-11-17 | Design written; server on the NUC; agents enrolled with `rollout.trigger: manual` to compare plans against what Ansible had left |
| 2026-11-17/18 | Modules rolled out in order of risk; timepi's GPS and PTP fixed along the way; `trigger: auto` once a full rollout went cleanly |
| 2026-11-18 | UI behind the Tailscale Service `svc:buckle` (agents followed when the server moved) |
| 2026-11-19 | Renovate ported from SpechtLabs/sigil; nightly kernel reboots added after three workers sat on an installed but unbooted kernel |
| 2026-11-23 | Server moved from the NUC to isa in about two minutes, hosts unaffected |
| 2026-11-24 | Buckle 2.22.0: node maintenance (cedi's buckle#907); phases rebuilt as `canary`/`core`/`fleet` with module limits, no bakes |
| 2026-11-26 | Repo moved from cedi/homelab to SpechtLabs/homelab |

## The phase plan that didn't survive

The first design had six phases (`canary` on one blade with a 10-minute bake, `k3s-server`,
`k3s-agents`, `ceph`, `core` with `approval: required`, `rest`) and planned kured inside the
cluster for patch reboots. Two things replaced that. Health checks that mean "the host can do its
job" made bakes pointless, and nobody approves rollouts by hand, so every phase went `auto`. And
once module `parallel` limits counted any change on a host, one `fleet` phase could run Ceph and
k3s side by side while still taking each one host at a time; with Buckle draining nodes itself,
kured wasn't needed.

## Gaps known from the start

Templates can't read other hosts' data, there are no task loops, Buckle can't run containers, and
the server has no HA. The last one is acceptable because agents keep enforcing their last revision
while the server is down; a nightly backup and a server config in git cover rebuilding it.
