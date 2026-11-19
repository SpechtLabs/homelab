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
| `workloads/` | What Buckle applies to the k3s cluster (`labk3s`); see below |
| `schedules/` | Actions Buckle runs on a cron schedule (nightly package upgrades) |
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
| `headless` | Pis | No desktop: removes the Raspberry Pi OS desktop and its apps, boots to `multi-user.target` |
| `rpi-exporter` | Pis | cedi/rpi_exporter on :9243 |
| `nut-server` | nuc | upsd proxying the UPS Tower's NUT server to the Pis |
| `nut-client` | Pis | upsmon + upssched; early or late shutdown |
| `k3s-server` | clusterpi-leader | k3s control plane |
| `k3s-agent` | clusterpi-worker* | k3s workers; *action*: reboot |
| `time-sync` | Pis, nuc | systemd-timesyncd from timepi over the LAN, public pools as fallback |
| `ptp-server` | timepi | GPS + PPS discipline ntpsec (NTP); phc2sys copies the clock to eth0's PHC and ptp4l serves PTP from it; `time-metrics` exports ntpsec, gpsd, PPS and PTP state as node_exporter textfiles |
| `tsidp` | nuc | tailnet OIDC provider |
| `buckle` | all | Buckle itself at `buckle_version`; restarts the agent (and the server on the NUC) after the run |
| `compute-blade-agent` | blade-pi* | compute-blade-agent: fan curve, health LEDs (fan stall, under-voltage, throttling), power policy, button gestures (hold 5s: shutdown, 5 presses: power off), metrics on :9666, bladectl's mTLS API on :8081 announced via mDNS; renews its certificates |
| `jitsi` | meet | Jitsi Meet: Prosody, jicofo, videobridge, nginx, coturn configs and pinned package versions |
| `argocd-seed` | clusterpi-leader | installs Argo CD only on a cluster that has none, from k8s-deployment, with the age key |
| `ceph-disk` | storagepi-ceph* | split the NVMe into root + OSD partition from the initramfs; *action*: shrink-root |
| `ceph` | storagepi-ceph* | Ceph via cephadm over the tailnet: host prep, cluster specs, pools/keys/S3 users; *action*: bootstrap. See [docs/ceph.md](docs/ceph.md) |

## The k3s cluster

`buckle.yaml` declares the cluster `labk3s`: the k3s server is its executor and uses its own
admin kubeconfig. Ownership is split so Buckle and Argo CD never manage the same object:

- **Buckle** brings up k3s (`k3s-server`, `k3s-agent`), seeds Argo CD once on a cluster that has
  none (`argocd-seed`: renders k8s-deployment's `apps/argocd/cluster/labk3s` with ksops and the
  age key, like its `docs/first-deployment.md`), and owns the root Application
  (`workloads/argocd-root`: `1-meta-labk3s`, with `Prune=false`).
- **Argo CD** deploys everything else from
  [SpechtLabs/k8s-deployment](https://github.com/SpechtLabs/k8s-deployment), itself included.

On fresh Pis that's the whole bootstrap: enrol them, and the rollout installs k3s, seeds Argo CD
and creates the root app. The only secret involved is `ARGOCD_AGE_KEY` on the Buckle server.

## Day to day

```sh
mise install                       # the buckle CLI, pinned in mise.toml
mise exec -- buckle validate --config . $(printf -- '--facts %s ' fixtures/facts/*.json)
```

- **Change something**: open a PR. CI dry-plans every host, and once it's merged the server
  rolls it out.
- **Upgrade k3s / Alloy / rpi_exporter / tsidp**: merge the renovate PR that bumps
  `vars/versions.yaml`. k3s goes server first, then two agents at a time.
- **Upgrade Buckle**: merge renovate's `buckle` PR (`buckle_version` in `vars/versions.yaml` and
  the CLI in `mise.toml`). The `buckle` module updates every host through the phases: the blades
  (`canary`, all four), then the NUC (server) with the rest of `core` (two at a time), then `fast`
  (two at a time) and `slow` (one at a time: the Ceph hosts); agents restart into the new version
  90 seconds after their run.
  Major versions are left to you: read the release notes and upgrade the server first.
- **Package upgrades**: `schedules/nightly-upgrades.yaml` runs `base: upgrade` on every host at
  03:00 Europe/Berlin through the normal phases, and reboots only the hosts that need it, one
  or two at a time. Its runs show on the Schedules page; a failed host pauses that night's
  rollout like any other.
- **Blades from here**: `mise run bladectl-config` finds the blades with `bladectl discover`
  (mDNS, so on their LAN; elsewhere it refreshes the configured ones) and fetches each one's
  bladectl client config (mTLS, made by its agent) into `~/.config/bladectl/config.yaml`; then
  `bladectl -A get fan`, `bladectl --blade blade-pi3 set identify`, `bladectl -A events`. Rerun
  it after the agent renews its certificates. Grafana: the Compute Blades dashboard.
- **Change Jitsi** (meet): edit `modules/jitsi/files/`. They are the quick-install's own files,
  adopted as they were, so each change is visible in the plan's diff. Secrets
  (`JITSI_JVB_PASSWORD`, `JITSI_FOCUS_PASSWORD`, `JITSI_TURN_SECRET`) are in the server's secret
  store; the first two must match the `jvb` and `focus` accounts in Prosody.
- **Upgrade Jitsi**: bump every version in `vars/host-meet.yaml`'s `jitsi_packages` together; one
  apt transaction installs the set (an apt pin keeps the nightly upgrade off them). Before that,
  check what the new packages want from the configs Buckle owns, because their postinsts edit
  configs on upgrade and Buckle would write the old ones back:
  1. `apt-get download` the new versions on meet; compare the templates they ship
     (`/usr/share/jitsi-meet-prosody/prosody.cfg.lua-jvb.example`,
     `/usr/share/jitsi-meet-web-config/jitsi-meet.example`) with `modules/jitsi/files/`.
     Prosody's site config and the nginx site are those templates filled in for meet (domain,
     `focus`, TURN secret; `"polls"` commented out and the colibri websocket proxy enabled, as
     the postinsts do).
  2. Upgrade an `ubuntu:24.04` amd64 container from the old to the new versions over the rendered
     templates (dummy secrets) and diff the configs afterwards; start Prosody there and check
     its log for module errors, and `nginx -t`.
  3. `buckle plan` on meet with the working tree, then merge.
  The `bridge-available` check fails if jicofo can't see the videobridge afterwards.
- **Reboot or patch a host now**: the host page's actions (`base: upgrade`, `base: reboot`,
  `k3s-agent: reboot`).
- **Reset k3s**: by hand. It is deliberately not a Buckle removal hook.

## Known issues

Found during the migration (2026-11-17/18); none of them caused by it.

- **NUC on an end-of-life release.** Ubuntu 24.10 is EOL and `archive.ubuntu.com` dropped it, which
  broke every `apt-get update`. `/etc/apt/sources.list.d/ubuntu.sources` points at
  `old-releases.ubuntu.com` by hand (original: `ubuntu.sources.bak-20261118`). apt works, but there
  are no security updates: move the NUC to 26.04 LTS.
- **GitHub API rate limit.** `github.release` spends one anonymous API call (60/h per IP, shared
  by every host at home) per plan while a host isn't on the pinned version. Fine in steady state;
  a fleet-wide upgrade of many hosts at once can exhaust it, so roll those in phases.
