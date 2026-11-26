# Health checks

Each module's `health:` list, from `modules/*/module.yaml` on 2026-11-26. **Required** checks gate
rollouts: after an apply, a host counts as healthy only once they pass, and one that keeps failing
past `settle` (2 min) fails the host and pauses the rollout. **Informational** ones
(`required: false`) report but never hold a rollout. Agents also run them on every 15-minute drift
pass.

Run them on a host: `sudo buckle health`. Names in the UI and API are `<module>/<check>`, the form
`waive_checks` takes.

| Check | Required | What it looks at |
|---|---|---|
| `alloy/ready` | yes | `http://127.0.0.1:12345/-/ready` |
| `alloy/unit` | yes | `alloy` active, up 30 s |
| `tailscale/connected` | yes | `tailscale ip -4` succeeds |
| `pi-firmware/watchdog-armed` | yes | systemd's `RuntimeWatchdogUSec` is `15s` |
| `rpi-exporter/metrics` | yes | `:9243` answers with metrics |
| `nut-client/monitor` | yes | `nut-monitor` active, up 30 s |
| `nut-client/ups-reachable` | yes | `upsc ups@nut.sphinx-map.ts.net ups.status` answers |
| `time-sync/synchronized` | yes | `chronyc tracking` shows `Leap status : Normal` |
| `time-sync/source` | no | chrony's selected source is PTP (`ptp-client`) or timepi |
| `compute-blade-agent/agent`, `packaged-binary`, `metrics`, `api-certificate` | yes | Unit up 30 s, running `/usr/bin/compute-blade-agent`, `:9666/metrics`, server certificate valid for 14 more days |
| `k3s-server/unit`, `kubelet`, `apiserver` | yes | `k3s` active, up 60 s; kubelet `:10248/healthz`; API `/readyz` says `ok` |
| `k3s-server/svc-api`, `svc-ip`, `nodes-ready` | no | `/readyz` through `svc:labk3s`, the Service's address resolves, every node `Ready` |
| `k3s-agent/unit` | yes | `k3s-agent` active, up 60 s |
| `k3s-agent/kubelet` | yes | `http://127.0.0.1:10248/healthz` says `ok` |
| `argocd-seed/argocd-server` | no | `argocd-server` deployment has an available replica |
| `ceph/tailnet-route` | yes | The tailnet route in the main table that Ceph binds to |
| `ceph/cluster` | yes | `ceph-buckle-health` prints `ok`: every OSD and mon back, no degraded or unavailable data; other warnings pass, `HEALTH_ERR` fails |
| `nut-server/upsd`, `proxied-ups` | yes | upsd running; `upsc ups@localhost ups.status` answers |
| `nut-server/svc-nut` | no | the same through `nut.sphinx-map.ts.net` |
| `ptp-server/gpsd`, `ntpsec`, `ntp-synced`, `ptp4l-master`, `phc2sys` | yes | timepi's time chain |
| `ptp-server/gps-pps-selected`, `metrics` | no | ntpsec on GPS/PPS, time metrics written |
| `tsidp/unit` | yes | `tsidp` active, up 30 s |
| `tsidp/discovery` | yes | `https://idp.sphinx-map.ts.net/.well-known/openid-configuration` has an issuer |
| `nas-backup/recent` | no | `nas-backup check`: every backup the host runs has a NAS copy younger than 26 h |
| `jitsi/prosody`, `jicofo`, `videobridge`, `bridge-available`, `coturn`, `site`, `internal-certificate`, `certificate` | yes | Jitsi's services; `bridge-available` fails if jicofo can't see the videobridge |

Modules without checks: `base`, `buckle`, `buckle-server`, `ceph-disk`, `dotfiles`, `headless`, `pi-facts`,
`pi-tools`, `ptp-facts`.

What each check runs exactly is in its `module.yaml`; check names change with the modules, so the
file is the source of truth. For the Systems these checks guard, see the
[ceph](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/),
[labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/) and
[timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/) docs.
