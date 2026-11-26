# CI and Renovate

`main` has no required checks. Renovate merges its own PRs only after every check on the PR
passed, and a merge to `main` is a fleet rollout.

## Workflows

| Workflow | Trigger | Job | What it checks |
|---|---|---|---|
| [`validate.yml`](https://github.com/SpechtLabs/homelab/blob/main/.github/workflows/validate.yml) | PRs, pushes to `main` | `k3s-one-minor` (PRs only) | `k3s_version` moves at most one minor from `main` |
| | | `buckle` | `buckle validate --config .` with `--facts` for every `fixtures/facts/*.json` (dry plan per host); the same again with the pinned linux-amd64 binary under `qemu-x86_64 -cpu Nehalem` |
| | | `docs` | `mise run docs`: every TechDocs site under `docs/` built strict |
| [`renovate-config.yaml`](https://github.com/SpechtLabs/homelab/blob/main/.github/workflows/renovate-config.yaml) | changes to `renovate.json` | `validate` | `renovate-config-validator --strict` |
| [`tailscale.yaml`](https://github.com/SpechtLabs/homelab/blob/main/.github/workflows/tailscale.yaml) | changes to `tailscale/policy.hujson` | `policy` | Tests the tailnet policy on PRs, applies it on `main` ([tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)) |

The Nehalem run exists because Buckle 2.14.0's amd64 build used instructions the NUC's Celeron
(x86-64-v2, no AVX) lacks and crashed with SIGILL. The NUC still runs an agent.

Locally, `mise run validate` is the `buckle` job's first step and `mise run docs` the `docs` job.
Neither CI nor a Mac can do a full plan of apt or systemd tasks; that happens on the hosts, in the
rollout.

## Renovate

Rules from [`renovate.json`](https://github.com/SpechtLabs/homelab/blob/main/renovate.json):

| What | Rule |
|---|---|
| Watched pins | Lines in `vars/*.yaml` under a `# renovate: datasource=... depName=...` comment; `dotfiles_ref` by git commit on `main`; the buckle and bladectl pins in `mise.toml` (Renovate's own mise manager, which names them `github:<owner>/<repo>`); GitHub Actions digests |
| Automerge | digest, pin, patch and minor; Renovate merges after checks pass (`platformAutomerge: false`) |
| Release age | third-party GitHub releases wait 3 days, the `mise.toml` CLIs too; `cedi/rpi_exporter` and compute-blade-agent don't wait |
| Majors | automerge once 7 days old, except Buckle majors (disabled) |
| k3s | minors separate from patches, one minor per PR, merged only before 06:00 on Mondays; patches automerge |
| Groups | `buckle` (`buckle_version` + the CLI, matched by both names), `compute-blade-agent` (agent + bladectl, same), GitHub Actions |
| Limits | 2 PRs an hour, 8 open; Europe/Berlin |

Not watched: `ceph_version` and its sha256, Jitsi's packages in `vars/host-meet.yaml`.
