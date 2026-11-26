# Ports, files and health checks

## Ports on each blade

| Port | Protocol | What | Who uses it |
|------|----------|------|-------------|
| 9666 | HTTP | `/metrics` (Prometheus), `/debug/pprof/`; no authentication | Alloy on the blade (job `blade_exporter`), Buckle's `metrics` check |
| 8081 | gRPC over mTLS | the bladectl API (`api:bladectl-api` in the catalog) | bladectl on your Mac, root's bladectl on the blade |
| 5353 | UDP, mDNS | `_compute-blade._tcp` announcement via avahi-daemon, TXT `version`, `api=v1alpha1`, `auth=mtls` | `bladectl discover`, `mise run bladectl-config` |
| 9243 | HTTP | rpi_exporter (not the agent) | Alloy, job `rpi_exporter` |

The API's protocol is vendored in [`modules/compute-blade-agent/blade.proto`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/blade.proto); Backstage shows it on the `bladectl-api` API's Definition tab.

## Files on each blade

| Path | Owner | What |
|------|-------|------|
| `/usr/bin/compute-blade-agent`, `/usr/bin/bladectl` | package | agent and CLI, from the release's `.deb` |
| `/etc/compute-blade-agent/config.yaml` | Buckle | the config ([Agent configuration](agent-configuration.md)) |
| `/etc/compute-blade-agent/ca.pem`, `ca-key.pem` | agent | the blade's own CA, 10 years (until 2035) |
| `/etc/compute-blade-agent/server.pem`, `server-key.pem` | agent | server certificate, 1 year; names `localhost`, `blade-piN`, `blade-piN.local` and the blade's IPs at creation |
| `/root/.config/bladectl/config.yaml` | agent | root's bladectl config with a client certificate (1 year), `server: localhost:8081`. What `mise run bladectl-config` copies |
| `/etc/systemd/system/compute-blade-agent.service.d/dev.conf`, `e2e.conf` | someone testing a build | removed by Buckle |
| `/usr/local/lib/cba-e2e/` | e2e test runs | removed by Buckle |
| `/usr/share/compute-blade-agent/fanunit.uf2` | package | smart fan unit firmware for this release |
| `/dev/ttyAMA5` | kernel | the smart fan unit's UART (GPIO 12/13) |

On the Mac: `~/.config/bladectl/config.yaml` (see [bladectl commands](bladectl.md#config-file)).

## Buckle tasks worth knowing

From [`modules/compute-blade-agent/module.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/module.yaml):

| Task id | Does |
|---------|------|
| (apt.package) | installs `compute-blade-agent` at exactly `compute_blade_agent_version` from the GitHub release |
| `agent-config` | writes the config, restarts the agent |
| `agent-certificates` | deletes the server certificate and root's bladectl config when either expires within 30 days (2592000 s); the restart makes new ones |
| `packaged-agent` | `daemon-reload` and restart when the running agent isn't `/usr/bin/compute-blade-agent` |

## Health checks

The first four are required: a failure on any blade pauses the rollout in the canary phase. `mdns-name` only shows in the Buckle UI.

| Check | Passes when |
|-------|-------------|
| `agent` | `compute-blade-agent` active for 30 s |
| `packaged-binary` | the running process is `/usr/bin/compute-blade-agent` |
| `metrics` | `http://127.0.0.1:9666/metrics` answers |
| `api-certificate` | `server.pem` valid for 14 more days or longer |
| `mdns-name` (informational) | avahi announces the blade under `$(hostname -s)`, not `blade-piN-2` ([Fix the blade's mDNS name](../how-to/fix-the-blades-mdns-name.md)) |
