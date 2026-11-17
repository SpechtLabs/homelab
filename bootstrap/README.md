# Bootstrapping the fleet

Everything here happens once, by hand. After that, a merged commit is a rollout.

## 1. Tailnet policy

Add a tag for the server and let the existing tags reach it:

```jsonc
"tagOwners": {
  "tag:buckle-server": ["autogroup:admin"]
},
"grants": [
  // agents dial out to the server's gRPC port
  { "src": ["tag:homelab", "tag:core-infra", "tag:core-services"],
    "dst": ["tag:buckle-server"], "ip": ["tcp:7700"] },
  // you, for the UI and API
  { "src": ["autogroup:admin"], "dst": ["tag:buckle-server"], "ip": ["tcp:7701"] }
]
```

Then give the NUC `tag:buckle-server` in the admin console (Machines → nuc → Edit ACL tags),
next to the tags it already has.

Create an OAuth client (Settings → OAuth clients) with **Auth Keys: write**, limited to
`tag:homelab`, `tag:core-infra` and `tag:core-services`. The server uses it to mint single-use
keys for the "Add an agent" button. **Revoke the old `tailscale_authkey`** from the Ansible
inventory once this works.

## 2. Secrets

Pull the values out of the Ansible inventory one last time:

```sh
cd ~/src/gh/cedi/homelab-ansible
ansible -i inventory/homelab.yaml clusterpi-leader -m debug -a var=token --ask-vault-pass
```

On the NUC, one file per secret, root-owned, mode 0600:

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

## 3. Server on the NUC

```sh
# binary (same version as mise.toml)
curl -fsSL https://github.com/SierraSoftworks/buckle/releases/download/v2.13.0/install.sh | sudo sh -s --

# config
sudo install -d -m 0755 /etc/buckle
sudo install -m 0644 bootstrap/server.yaml /etc/buckle/server.yaml
sudo install -m 0600 bootstrap/server.env.example /etc/buckle/server.env   # then fill it in
sudo install -m 0644 bootstrap/buckle-server.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now buckle-server
journalctl -u buckle-server -f
```

The repository has to exist on GitHub first (`cedi/homelab`), with a fine-grained, read-only
token in `GIT_TOKEN`. The UI is at http://nuc.sphinx-map.ts.net:7701.

Nightly backup: install `bootstrap/backup.sh` as a cron job or timer on the NUC. Everything
else can be rebuilt from git and the secrets.

## 4. Enrol the existing hosts

`rollout.trigger` is `manual`, so enrolling changes nothing yet: agents report facts and plans.

Every host is already on the tailnet, so only the agent gets installed. The host id must equal
the tailnet node name; pass `--host-id` where the system hostname differs.

```sh
enrol() {  # enrol HOST SSH_USER
  tailscale ssh "$2@$1" -- \
    'curl -fsSL https://github.com/SierraSoftworks/buckle/releases/download/v2.13.0/install.sh \
       | sudo sh -s -- up --server http://nuc.sphinx-map.ts.net:7700 --insecure-plaintext'
}
for h in nuc hole meet; do enrol "$h" root; done
enrol timepi cedi
for h in jumphost timepi-gps clusterpi-leader \
         clusterpi-worker1 clusterpi-worker2 clusterpi-worker3 clusterpi-worker4 \
         storagepi-ceph1 storagepi-ceph2 storagepi-ceph3 \
         blade-pi1 blade-pi2 blade-pi3 blade-pi4 lora lyv; do
  enrol "$h" pi
done
```

A brand-new host joins with **Add an agent** in the UI instead, which installs Tailscale with
the right tags and the agent in one paste.

## 5. Replace the placeholder facts

`fixtures/facts/*.json` were written by hand from the old inventory. Swap each for the real thing
so CI plans against what the hosts actually report:

```sh
# Keep only what selectors and templates read: the repo is public, and raw
# facts include MAC addresses, public IPv6, local users and every systemd unit.
trim='{os, hardware: (.hardware | del(.disks, .disk)), net: {hostname: .net.hostname, fqdn: .net.fqdn}, tailscale: (.tailscale | if . then {hostname, tags, online, backend_state, tailnet} else null end), script, cloud}'
for h in $(ls fixtures/facts | sed 's/\.json$//'); do
  tailscale ssh "$h" -- sudo buckle facts | jq "$trim" > "fixtures/facts/$h.json"   # user@ as above
done
```

Check one Pi before anything else: `jq .os fixtures/facts/jumphost.json` must say
`"family": "debian"`. Every apt task depends on it.

## 6. First rollouts

**Enrol every Pi before the first rollout.** The NUC's new Alloy config stops scraping the
Pis centrally, so a Pi that isn't running Buckle's Alloy yet goes dark. The `core` phase (NUC,
hole, meet) runs last for this reason, but it can't cover hosts that aren't enrolled.

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
