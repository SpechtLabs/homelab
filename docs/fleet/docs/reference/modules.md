# Modules

The 25 modules in [`modules/`](https://github.com/SpechtLabs/homelab/tree/main/modules), checked
against each `module.yaml` on 2026-11-26. "Selected by" is the module's `when` (groups are in
[Groups](groups.md)); hosts are what that selects today. Health checks per module are in
[Health checks](health-checks.md).

| Module | Selected by | Hosts | Does |
|---|---|---|---|
| `base` | `debian` | all | Hostname = host id, locale, `git curl sudo locales`, masks PackageKit, repairs a half-configured dpkg first |
| `dotfiles` | `debian` | all | cedi/dotfiles at `dotfiles_ref` for the login account (`admin_user`), fish as its login shell |
| `tailscale` | `debian` | all | Keeps tailscaled installed and current, `--ssh`, an exit node where `tailscale_exit_node` is set; never touches tags |
| `alloy` | `debian` | all | Grafana Alloy: own exporters and logs to Loki/Mimir/Tempo (homelab, or spechtlabs on meet); OTLP receiver and remote scrapes on the collector |
| `ptp-facts` | `debian` | all | Script fact `host.facts.script.ptp`: is timepi on this host's LAN, does that NIC timestamp PTP in hardware |
| `buckle` | (no `when`) | all | Buckle at `buckle_version`; owns the `server:` line of `agent.yaml`; restarts the agent (and the server on isa) 90 s after the run |
| `pi-facts` | `pi` | Pis | Script fact `host.facts.script.rpi`: HAT EEPROM, NVMe, GPIO PPS input |
| `pi-firmware` | `pi` | Pis | `config.txt` `[all]` (PoE+ HAT fan, Pi 5 cooling/PCIe, GPS/PPS), cgroups in `cmdline.txt`, WiFi off, hardware watchdog; reboots on change |
| `headless` | `pi` | Pis | Removes the Raspberry Pi OS desktop and its apps, boots to `multi-user.target` |
| `rpi-exporter` | `pi` | Pis | cedi/rpi_exporter on :9243 |
| `pi-tools` | `pi5` | Pi 5s | rpi-clone |
| `nut-client` | `nut-client` | Pis, nuc | upsmon + upssched against `svc:nut`; early or late (`nut-late`) shutdown |
| `nut-server` | `nut-server` | isa | upsd proxying the Synology's UPS to the Pis and Home Assistant, served as `svc:nut` |
| `time-sync` | `ntp-client` | home LAN hosts but timepi | chrony from timepi; PTP with hardware timestamps where `ptp-client`, NTP elsewhere; public pool as fallback |
| `ptp-server` | `ptp-grandmaster` | timepi | gpsd + PPS discipline ntpsec; ptp4l/phc2sys serve PTP; time metrics as textfiles |
| `tsidp` | `tsidp` | isa | The tailnet's OIDC provider (`idp.sphinx-map.ts.net`) |
| `buckle-server` | `buckle-server` | isa | Keeps `/etc/buckle/secrets` root-only (0700); the rest of the server's config is installed by hand |
| `nas-backup` | `buckle-server`, `tsidp` or `k3s-server` | isa, clusterpi-leader | Nightly backups from `vars/backups.yaml` to the NAS (NFS v4.1 via `svc:nfs`), kept locally too, with a metric per backup |
| `k3s-server` | `k3s-server` | clusterpi-leader | k3s control plane (single server, SQLite/kine) |
| `k3s-agent` | `k3s-agent` | clusterpi-worker1..4 | k3s workers, joined through `svc:labk3s` |
| `argocd-seed` | `k3s-server` | clusterpi-leader | Installs Argo CD from k8s-deployment, only on a cluster that has none |
| `ceph-disk` | `ceph` | storagepi-ceph1..3 | Splits the NVMe into root + OSD partition from the initramfs, once |
| `ceph` | `ceph` | storagepi-ceph1..3 | Ceph via cephadm over the tailnet: host prep, specs, pools, keys, S3 users |
| `compute-blade-agent` | `blades` | blade-pi1..4 | Fan curve, LEDs, power policy, buttons, metrics :9666, bladectl's mTLS API :8081 |
| `jitsi` | `jitsi` | meet | Jitsi Meet (Prosody, jicofo, videobridge, nginx, coturn), pinned packages |

The one workload, [`workloads/argocd-root`](https://github.com/SpechtLabs/homelab/tree/main/workloads/argocd-root),
applies the root Argo CD Application `1-meta-labk3s` to `labk3s` (`removal: keep`); Argo CD deploys
everything else from SpechtLabs/k8s-deployment.

## Ordering, limits and disruption

| Module | Setting | Effect in a rollout |
|---|---|---|
| `ceph` | `parallel: 1` | At most one Ceph host changing at a time, whatever module changes it (a reboot from `base` or `pi-firmware` counts) |
| `k3s-agent` | `parallel: 1` | At most one k3s worker changing at a time, same counting |
| `k3s-agent` | `needs: [base, 'group:k3s-server']` | Workers apply after the k3s server, also within the `fleet` phase |
| `k3s-server`, `k3s-agent` | `disrupts: node` | A change to them drains the node first (`labk3s` `maintenance`) |
| `nas-backup`, `time-sync`, `ptp-server` | `needs: [alloy]` (and others) | The textfile directory their metrics go to exists first |
| `pi-firmware` | `needs: [pi-facts]` | The PoE HAT task reads `host.facts.script.rpi` |

## Actions

| Module | Action | Confirm |
|---|---|---|
| `base` | `upgrade`, `reboot-if-required` | no |
| `base` | `reboot` | yes |
| `k3s-agent` | `reboot` | yes |
| `ceph` | `bootstrap` | yes |
| `ceph-disk` | `shrink-root` | yes |

What each does: [Run an action on a host](../how-to/run-an-action-on-a-host.md#the-actions).
