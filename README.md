# homelab

Fleet configuration for the homelab, applied by [Buckle](https://buckle.sierrasoftworks.com).
The Buckle server runs on the NUC and watches this repository; every commit on `main` becomes a
revision that rolls out through the phases in `buckle.yaml`, gated on health checks. Agents
connect over the tailnet and are identified by their Tailscale node, so there is no SSH and no
inventory.

Replaces `homelab-ansible`. Why and how: [docs/buckle-migration.md](docs/buckle-migration.md).
First-time setup: [bootstrap/README.md](bootstrap/README.md).

## Layout

| Path | What |
|---|---|
| `buckle.yaml` | Groups (derived from facts), vars layering, secret references, rollout phases |
| `vars/` | Shared values, broad to narrow: `defaults`, `versions` (renovate), `hw-*`, `group-*`, `host-*` |
| `modules/` | One concern each; see below |
| `fixtures/facts/` | One facts file per host; CI dry-plans every host against them |
| `bootstrap/` | The server's own config, installed by hand on the NUC |
| `nas/` | Compose projects for the Synology, deployed through DSM (not Buckle) |
| `tailscale/policy.hujson` | The tailnet policy; tested on PRs and applied on `main` by `.github/workflows/tailscale.yaml` |

## Modules

| Module | Hosts | Does |
|---|---|---|
| `base` | all | hostname, locale, bootstrap packages; *actions*: upgrade packages, reboot |
| `dotfiles` | all | cedi/dotfiles and fish as login shell for each host's login account (`admin_user`) |
| `tailscale` | all | keeps tailscaled current; `--ssh`, exit node on `hole` |
| `alloy` | all | logs and metrics to Loki/Mimir (homelab or spechtlabs); OTLP receiver on the collector |
| `pi-facts` | Pis | custom fact `host.facts.script.rpi` from the HAT EEPROM |
| `pi-firmware` | Pis | `config.txt` (PoE+ HAT fan, Pi 5 cooling/PCIe, GPS/PPS wiring), cgroups in `cmdline.txt`; reboots on change |
| `pi-tools` | Pi 5 | rpi-clone |
| `rpi-exporter` | Pis | cedi/rpi_exporter on :9243 |
| `nut-server` | nuc | upsd proxying the Synology's UPS |
| `nut-client` | Pis | upsmon + upssched; early or late shutdown |
| `k3s-server` | clusterpi-leader | k3s control plane |
| `k3s-agent` | clusterpi-worker* | k3s workers; *action*: reboot |
| `ptp-server` | timepi | gpsd + PPS into ntpsec; ptp4l/phc2sys behind `ptp_enabled` |
| `tsidp` | nuc | tailnet OIDC provider |

## Day to day

```sh
mise install                       # the buckle CLI, pinned in mise.toml
mise exec -- buckle validate --config . $(printf -- '--facts %s ' fixtures/facts/*.json)
```

- **Change something**: open a PR. CI dry-plans every host, and once it's merged the server
  rolls it out.
- **Upgrade k3s / Alloy / rpi_exporter / tsidp**: merge the renovate PR that bumps
  `vars/versions.yaml`. k3s goes server first, then one agent at a time.
- **Upgrade Buckle**: bump `mise.toml` and `desired_version` in `bootstrap/server.yaml`; update
  the server binary, then upgrade agents from the UI (canary first).
- **Reboot or patch a host**: the host page's actions (`base: upgrade`, `base: reboot`,
  `k3s-agent: reboot`).
- **Reset k3s**: by hand. It is deliberately not a Buckle removal hook.
