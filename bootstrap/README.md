# Bootstrapping the fleet

Everything here happens once, by hand. After that, a merged commit is a rollout.

## 1. Tailnet policy

The policy lives in `tailscale/policy.hujson` and already has the Buckle grant (agents with
`tag:buckle-agent` may reach `svc:buckle` on tcp:7700).
`.github/workflows/tailscale.yaml` tests it on PRs and applies it on `main`, using the repo
secrets `TS_OAUTH_ID`, `TS_OAUTH_SECRET` and `TS_TAILNET`.

The grant only matches once the server host carries the tag: admin console → Machines → isa → Edit
ACL tags → add `tag:buckle-server` next to its existing tags. Without it, its tailscaled logs
`Drop: TCP{… > 100.122.149.90:7700} no rules matched` for every agent.

Create an OAuth client (Settings → OAuth clients) with **Auth Keys: write**, limited to
`tag:buckle-agent`. The server uses it to mint single-use
keys for the "Add an agent" button. **Revoke the old `tailscale_authkey`** from the Ansible
inventory once this works.

## 2. Secrets

Pull the values out of the Ansible inventory one last time:

```sh
cd ~/src/gh/cedi/homelab-ansible
ansible -i inventory/homelab.yaml clusterpi-leader -m debug -a var=token --ask-vault-pass
```

On the server host (isa), one file per secret, root-owned, mode 0600:

| File in `/etc/buckle/secrets/` | Value |
|---|---|
| `K3S_TOKEN` | the k3s token above (unchanged: changing it breaks node joins) |
| `NUT_UPSTREAM_PASSWORD` | the Synology's NUT password (DSM fixes it to `secret`) |
| `NUT_ADMIN_PASSWORD` | new value; it was `foobar2342` in git |
| `NUT_MONITOR_PASSWORD` | new value; it was `secret` in git |

```sh
sudo install -d -m 0700 /etc/buckle/secrets
printf '%s' "$VALUE" | sudo install -m 0600 /dev/stdin /etc/buckle/secrets/K3S_TOKEN
```

Rotating the NUT passwords means the first `nut-server` + `nut-client` rollout changes both
ends. Do it in one rollout (it is: both modules are in the same revision).

## 3. Server on isa

```sh
# binary (same version as mise.toml)
curl -fsSL https://github.com/SierraSoftworks/buckle/releases/download/v2.15.0/install.sh | sudo sh -s --

# config
sudo install -d -m 0755 /etc/buckle
sudo install -m 0644 bootstrap/server.yaml /etc/buckle/server.yaml
sudo install -m 0600 bootstrap/server.env.example /etc/buckle/server.env   # then fill it in
sudo install -m 0644 bootstrap/buckle-server.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now buckle-server
journalctl -u buckle-server -f
```

The repository has to exist on GitHub first (`cedi/homelab`), with a fine-grained, read-only
token in `GIT_TOKEN`.

The UI and API are the Tailscale Service `svc:buckle`, at https://buckle.sphinx-map.ts.net.
Define it once in the admin console (Services → Define Service, name `buckle`, port `tcp:443`);
the policy auto-approves it for `tag:buckle-server`. Then, on isa:

```sh
ip=$(tailscale ip -4)
sudo tailscale serve --bg --service=svc:buckle --https=443 "http://$ip:7701"
sudo tailscale serve --bg --service=svc:buckle --tcp=7700 --proxy-protocol=2 "tcp://$ip:7700"
```

tailscaled keeps this across reboots. `web.base_url` in `server.yaml` is that URL, so tsidp's
Buckle client needs `https://buckle.sphinx-map.ts.net/api/v1/auth/callback` as a redirect URI.
Agents dial `buckle.sphinx-map.ts.net:7700` too (the `buckle` module owns the `server:` line of
their `agent.yaml`). The Service forwards it with a PROXY v2 header, and `agents.trusted_proxies`
in `server.yaml` lists the hosts allowed to send one, so the server still identifies each agent by
Tailscale whois of its own address. Define the Service with both ports (`tcp:443`, `tcp:7700`):
a host advertising it without serving every defined port gets no traffic at all.

**Moving the server to another host** (as from the NUC to isa on 2026-11-23, about two minutes
without a control plane, hosts unaffected): stage the binary, `/etc/buckle` and the units there
(listen address in `server.env`, the host in `trusted_proxies`), give it `tag:buckle-server`, then
`tailscale serve drain svc:buckle` and stop the server on the old host, copy `data_dir` with the
server stopped (over the LAN: Tailscale SSH refuses host-to-host logins), start it on the new host
and run the two `serve` commands there. Agents reconnect through the Service by themselves.

Nightly backup: the `buckle-server` module backs the database up at 01:30, kept 3 days on
the server host and 14 days on the NAS (NFS export `vars.buckle_backup_nfs_export`); Grafana alerts
when the NAS copy is older than 26 hours. Everything else can be rebuilt from git and the secrets.

## 4. Enrol the existing hosts

`rollout.trigger` is `manual`, so enrolling changes nothing yet: agents report facts and plans.

Every host is already on the tailnet, so only the agent gets installed. The host id must equal
the tailnet node name; pass `--host-id` where the system hostname differs.

```sh
enrol() {  # enrol HOST SSH_USER
  tailscale ssh "$2@$1" -- \
    'curl -fsSL https://github.com/SierraSoftworks/buckle/releases/download/v2.15.0/install.sh \
       | sudo sh -s -- up --server http://nuc.sphinx-map.ts.net:7700 --insecure-plaintext'
}
for h in nuc meet; do enrol "$h" root; done
enrol timepi cedi
for h in jumphost clusterpi-leader \
         clusterpi-worker1 clusterpi-worker2 clusterpi-worker3 clusterpi-worker4 \
         storagepi-ceph1 storagepi-ceph2 storagepi-ceph3 \
         blade-pi1 blade-pi2 blade-pi3 blade-pi4; do
  enrol "$h" pi
done
```

A brand-new host joins with **Add an agent** in the UI instead, which installs Tailscale with
the right tags and the agent in one paste.

## 5. Replace the placeholder facts

`fixtures/facts/*.json` started as hand-written placeholders. Once a host is enrolled, the
server has its facts; pull them from the API (no SSH needed) so CI plans against reality:

```sh
# Keep only what selectors and templates read: the repo is public, and raw
# facts include MAC addresses, public IPv6, local users and every systemd unit.
trim='{os, hardware: (.hardware | del(.disks, .disk)), net: {hostname: .net.hostname, fqdn: .net.fqdn}, tailscale: (.tailscale | if . then {hostname, tags, online, backend_state, tailnet} else null end), script, cloud}'
for h in $(curl -s http://nuc.sphinx-map.ts.net:7701/api/v1/fleet | jq -r '.hosts[].id'); do
  curl -s "http://nuc.sphinx-map.ts.net:7701/api/v1/hosts/$h/facts" | jq "$trim" > "fixtures/facts/$h.json"
done
```

`host.facts.script.rpi` (HAT, NVMe) only appears after `pi-facts` has applied once; re-capture
after the first rollout.

## 6. First rollouts

**Enrol every Pi before the first rollout.** The NUC's new Alloy config stops scraping the
Pis centrally, so a Pi that isn't running Buckle's Alloy yet goes dark. The `core` phase (NUC,
meet) runs last for this reason, but it can't cover hosts that aren't enrolled.

Start one from the Rollouts page and read every host's plan before approving. What to look for:

- **`pi-firmware`**: Ansible inserted `config.txt` lines with `insertafter: "[all]"`, a regex
  character class, so some ended up in other sections. A plan that *adds* a line which already
  exists elsewhere in the file means a duplicate; delete the stray one by hand first.
- **`alloy`**: retires the standalone node_exporter. Series keep `job="node_exporter"` and
  `instance="<host>:9100"`. Remove nothing in Grafana until every host reports.
- **`k3s-*`**: the unit files change (flags move to `/etc/rancher/k3s/config.yaml`), so every
  node restarts once, one at a time. The binary itself is a no-op unless the version differs.
- **`ptp-server`**: removes ntpsec and keeps chrony.

Once a full rollout has gone through cleanly, set `rollout.trigger: auto`.

## Sign-in and break-glass

The UI and API (https://buckle.sphinx-map.ts.net) sign in through tsidp. tsidp puts
`groups: ["buckle-admins"]` into the tokens of `group:admins` (`tailscale/policy.hujson`), and
`server.yaml`'s `user_acl` and `admin_acl` require it: changing who may use Buckle is a policy
change. The OIDC client was registered with tsidp's dynamic client registration; its ID and
secret live in `/etc/buckle/server.env` (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`).

Sign-in needs tsidp: without it there is no new login, and existing sessions stop working
within the hour, as Buckle revalidates them against tsidp. Agents and rollouts don't depend on
it. When tsidp is down:

```sh
ssh cedi@isa sudo systemctl start buckle-server-breakglass   # stops buckle-server
ssh -L 7701:127.0.0.1:7701 cedi@isa                          # then open http://localhost:7701
ssh cedi@isa sudo systemctl stop buckle-server-breakglass    # back to sign-in
```

`buckle-server-breakglass` is the same server and database with `server-breakglass.yaml`: no
sign-in, API/UI on `127.0.0.1:7701` only, agents unaffected. It reverts to `buckle-server`
when stopped and after 4 hours at most. SSH to isa doesn't depend on tsidp (Tailscale SSH or
the LAN). Keep `server-breakglass.yaml` identical to `server.yaml` apart from `web` and
`listen.http`.
