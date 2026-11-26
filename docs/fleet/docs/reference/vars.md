# Vars

Vars are layered under `vars:` in
[`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml), broad to narrow; a
later layer wins. A list replaces the earlier list whole, which is why `vars/group-ceph.yaml`
repeats `hw-pi.yaml`'s `rpi_exporter` scrape. Module defaults
(`vars:` in each `module.yaml`) sit below all of them. Templates read them as `{{ vars.<name> }}`.

## Layers, in order

| # | When | Source |
|---|---|---|
| 1 | always | [`vars/defaults.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/defaults.yaml) |
| 2 | always | [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml) |
| 3 | always | [`vars/backups.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/backups.yaml) (`nas_backups`, [Backups](backups.md)) |
| 4 | a Raspberry Pi | [`vars/hw-pi.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/hw-pi.yaml) |
| 5 | group `blades` | [`vars/group-blades.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-blades.yaml) |
| 6 | group `nut-late` | inline: `nut_shutdown_affinity: late` |
| 7 | group `spechtlabs` | [`vars/group-spechtlabs.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-spechtlabs.yaml) |
| 8 | group `o11y-collector` | [`vars/group-o11y-collector.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-o11y-collector.yaml) |
| 9 | group `ceph` | [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml) |
| 10 | nuc | [`vars/host-nuc.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-nuc.yaml) |
| 11 | isa | [`vars/host-isa.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-isa.yaml) |
| 12 | meet | [`vars/host-meet.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-meet.yaml) |
| 13 | timepi | [`vars/host-timepi.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-timepi.yaml) |
| 14 | jumphost | inline: `dotfiles_preset: core` |

## Shared vars (`vars/defaults.yaml`)

| Var | Value | Used by |
|---|---|---|
| `tailnet` | `sphinx-map.ts.net` | Every tailnet name (`buckle.{{ vars.tailnet }}`, `nut.`, `nfs.`, ...) |
| `admin_user` | `pi`; `cedi` on nuc, isa, timepi; `root` in `spechtlabs` | `dotfiles` |
| `admin_home`, `login_shell` | derived; `/usr/bin/fish` | `dotfiles` |
| `o11y_loki_url`, `o11y_mimir_url`, `o11y_tempo_url` | homelab endpoints on `*.k8s.specht-labs.de` | `alloy` |
| `o11y_log_paths` | `["/var/log/*.log"]` | `alloy` |
| `o11y_local_scrapes` | `[]`; rpi_exporter on Pis, plus blade_exporter, Ceph mgr/exporter by group | `alloy` |
| `o11y_remote_scrapes`, `o11y_probes`, `o11y_otlp_receiver` | collector only (`group-o11y-collector.yaml`) | `alloy` |
| `o11y_textfile_dir` | `/var/lib/prometheus/node-exporter` | `alloy`, `buckle-server`, `time-sync`, `ptp-server` |
| `nut_server_host` | `nut.{{ vars.tailnet }}` (`svc:nut`) | `nut-client` |
| `ntp_server` | `192.168.0.109` (timepi on the LAN) | `time-sync` |

## Pinned versions (`vars/versions.yaml`)

| Var | Renovate | Note |
|---|---|---|
| `buckle_version` | github-releases `SierraSoftworks/buckle` | Majors off; keep `mise.toml` in step |
| `compute_blade_agent_version` | github-releases | Keep `mise.toml`'s bladectl in step |
| `k3s_version` | github-releases `k3s-io/k3s` | One minor at a time (CI enforces) |
| `alloy_version`, `rpi_exporter_version`, `tsidp_version` | github-releases | |
| `dotfiles_ref` | git-refs, branch `main` | A commit, so a dotfiles push isn't drift |
| `ceph_version`, `ceph_cephadm_sha256` | none | By hand, together |
| `argocd_seed_kustomize_version`, `argocd_seed_helm_version`, `argocd_seed_ksops_version` | github-releases | Keep in step with k8s-deployment's `.mise.toml` |

Values change; read the file for the current ones.

## Module vars worth knowing

| Var | Module | Default |
|---|---|---|
| `buckle_server_url` | `buckle` | `http://buckle.{{ vars.tailnet }}:7700` |
| `buckle_restart_delay` | `buckle` | `90` (seconds) |
| `nas_backup_nfs_root` | `nas-backup` | `nfs.{{ vars.tailnet }}:/volume1/homelab` (each backup's `folder` below it) |
| `tailscale_ssh`, `tailscale_exit_node` | `tailscale` | `true`, `false` |
| `dotfiles_preset` | `dotfiles` | `server` (`core` on jumphost) |
| `locale` | `base` | `en_US.UTF-8` |
| `k3s_server` | `k3s-agent` | `labk3s.{{ vars.tailnet }}` (`svc:labk3s`) |

Secrets are never vars: a `{{ secrets.X }}` in a var is a plan-time error
([Add or change a secret](../how-to/add-or-change-a-secret.md)).
