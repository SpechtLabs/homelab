# Server and agents

Checked on isa on 2026-11-26. The repo copies of the server's files are in
[`bootstrap/`](https://github.com/SpechtLabs/homelab/tree/main/bootstrap); the live ones are
installed by hand ([why](../explanation/why-the-server-config-is-installed-by-hand.md)).

## The server host

| | |
|---|---|
| Host | isa: HP EliteDesk 800 G6 Mini (i5-10500), Ubuntu 26.04.1 LTS, clock in UTC |
| Addresses | tailnet `100.70.89.41`, LAN `192.168.0.118` |
| Tags | `tag:buckle-agent`, `tag:buckle-server`, `tag:nut-server`, `tag:o11y-collector`, `tag:tsidp-client` |
| Binary | `/usr/local/bin/buckle` (server and agent share it; the `buckle` module keeps it at `buckle_version`) |
| Server since | 2026-11-23 (before: the NUC) |

## Files

| Path on isa | What | Repo copy |
|---|---|---|
| `/etc/buckle/server.yaml` | Server config | `bootstrap/server.yaml` |
| `/etc/buckle/server-breakglass.yaml` | Same server without sign-in, on localhost | `bootstrap/server-breakglass.yaml` |
| `/etc/buckle/server.env` (0600) | `BUCKLE_LISTEN_ADDR`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | `bootstrap/server.env.example` |
| `/etc/buckle/secrets/` (0700, files 0600) | One file per secret | none (password manager) |
| `/etc/systemd/system/buckle-server.service` | Enabled; `Restart=on-failure` | `bootstrap/buckle-server.service` |
| `/etc/systemd/system/buckle-server-breakglass.service` | Never enabled; `Conflicts=buckle-server`, `RuntimeMaxSec=4h` | `bootstrap/buckle-server-breakglass.service` |
| `/var/lib/buckle-server/` (0700) | `data_dir`: `buckle.db` (SQLite, WAL), `source.git`, `revisions/`, `identity/` | none |
| `/etc/buckle/agent.yaml` | isa's own agent | written by `buckle up` |

## `server.yaml` settings

| Key | Value |
|---|---|
| `listen.grpc` | `${BUCKLE_LISTEN_ADDR}:7700` (isa's tailnet IP) |
| `listen.http` | `${BUCKLE_LISTEN_ADDR}:7701`; break-glass: `127.0.0.1:7701` |
| `listen.tls` | `mode: none` (WireGuard encrypts) |
| `source.git` | `https://github.com/SpechtLabs/homelab.git`, branch `main`, `poll: 30s`, no credentials (public repo) |
| `agents.auth` | `[tailscale]`: identity by Tailscale whois of the agent's address |
| `agents.registration` | `auto` |
| `agents.trusted_proxies` | `100.122.149.90` (nuc), `100.70.89.41` (isa): may send PROXY v2 headers |
| `agents.tailscale.allowed_tags` | `["tag:buckle-agent"]`: any other node is refused |
| `agents.tailscale.provisioning` | commented out (no OAuth client, so **Add an agent** can't mint keys) |
| `agents.join.server_url` | `http://buckle.sphinx-map.ts.net:7700` |
| `agents.minimum_agent_version` | `2.13.0` |
| `web.base_url` | `https://buckle.sphinx-map.ts.net` |
| `web.oidc` | tsidp at `https://idp.sphinx-map.ts.net`, scopes `openid profile email offline_access` |
| `web.user_acl`, `web.admin_acl` | `"buckle-admins" in claims.groups` |
| `secrets.providers.file.root` | `/etc/buckle/secrets` |
| `telemetry.otlp_endpoint` | `http://127.0.0.1:4317` (isa's Alloy) |

## Network

| | |
|---|---|
| Service | `svc:buckle`, served by isa, auto-approved for `tag:buckle-server` |
| UI/API | `https://buckle.sphinx-map.ts.net` (`tcp:443`), proxied to `http://100.70.89.41:7701` |
| Agents | `buckle.sphinx-map.ts.net:7700` (`tcp:7700`), forwarded to `100.70.89.41:7700` with `--proxy-protocol=2` |
| Who reaches what | `tag:buckle-agent` to `tcp:7700`; `group:admins` and `group:sre` to `tcp:443` (tailnet policy) |
| Readiness | `GET /readyz`, no sign-in; probed every 30 s by isa's Alloy for the SLO |

The Service is defined with both ports; a host that serves only one gets no traffic.

## Sign-in

OIDC through tsidp. tsidp adds `groups: ["buckle-admins"]` to tokens of `group:admins` (a
capability grant in the tailnet policy), and both ACLs require it, so who may use Buckle is a
policy change. The OIDC client was registered by tsidp's dynamic client registration; its redirect
URI is `https://buckle.sphinx-map.ts.net/api/v1/auth/callback`. Sessions are revalidated against
tsidp and don't survive a server restart. Without tsidp:
[Sign in when tsidp is down](../how-to/sign-in-when-tsidp-is-down.md).

## Secrets

Declared in `buckle.yaml`, one file each in `/etc/buckle/secrets/`.

| Secret | Used by | Note |
|---|---|---|
| `K3S_TOKEN` | `k3s-server`, `k3s-agent` | Changing it breaks node joins |
| `NUT_UPSTREAM_PASSWORD` | `nut-server` | The Synology's NUT password (DSM fixes it) |
| `NUT_ADMIN_PASSWORD`, `NUT_MONITOR_PASSWORD` | `nut-server`, `nut-client` | Both ends change in one rollout |
| `ARGOCD_AGE_KEY` | `argocd-seed` | age key for k8s-deployment's SOPS secrets |
| `JITSI_JVB_PASSWORD`, `JITSI_FOCUS_PASSWORD` | `jitsi` | Must match the `jvb` and `focus` Prosody accounts |
| `JITSI_TURN_SECRET` | `jitsi` | coturn and Prosody |

## Backup

| | |
|---|---|
| Timer | `buckle-backup.timer`: daily 01:30 isa time (UTC), `RandomizedDelaySec=5m`, `Persistent=true` |
| Script | `/usr/local/sbin/buckle-backup` (`modules/buckle-server/files/buckle-backup.sh`) |
| Local | `/var/backups/buckle/buckle-nightly-YYYY-MM-DD.db`, 0600, deleted after 3 days; manual `buckle-pre-*.db` copies live here too |
| NAS | `/mnt/nas/backups` = `nfs.sphinx-map.ts.net:/volume1/homelab/buckle`, NFS v4.1, mounted on demand by `mnt-nas-backups.mount`, deleted after 14 days |
| Metric | `buckle_backup_last_success_timestamp_seconds`, `target` `local` or `nas`, in `/var/lib/prometheus/node-exporter/buckle_backup.prom` |
| Not in it | `/etc/buckle` (config in git, secrets in the password manager) |

## Agents

| | |
|---|---|
| Unit | `buckle-agent.service` on every host |
| Config | `/etc/buckle/agent.yaml`: `server: http://buckle.sphinx-map.ts.net:7700` (owned by `modules/buckle`, var `buckle_server_url`), `host_id: null`, `tls.insecure_plaintext: true`, `drift: { interval: 15m, correct: true }` |
| State | `/var/lib/buckle` (resources, shadows, cached stable revision and its secrets) |
| Host id | the tailnet node name |
| On the host | `sudo buckle status`, `sudo buckle health`, `sudo buckle plan`, `sudo journalctl -u buckle-agent` |
| Upgrade | `modules/buckle`: `buckle update --to <buckle_version>`, restart 90 s after the run via `buckle-upgrade-<version>.timer` |

On the k3s server the agent is also `labk3s`'s executor (`identity: local`,
`/etc/rancher/k3s/k3s.yaml`).
