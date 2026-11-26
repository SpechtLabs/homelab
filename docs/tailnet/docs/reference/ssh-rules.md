# SSH rules

Tailscale SSH rules from
[`tailscale/policy/ssh.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/ssh.yaml).
`accept` lets the user in; `check` asks for a fresh sign-in first, at most
every `checkPeriod` (the members' root rule sets none).

| Entity | Source | Destination | Users | Action |
|---|---|---|---|---|
| `ssh-admins-infra-root` | `group:admins`, `tag:jumphost` | `tag:ceph`, `tag:k3s-node`, `tag:compute-blade`, `tag:smarthome` | `autogroup:nonroot`, `root` | accept |
| `ssh-admins-buckle-hosts` | `group:admins`, `tag:jumphost` | `tag:buckle-agent` | `autogroup:nonroot` | accept |
| `ssh-admins-buckle-hosts-root` | `group:admins` | `tag:buckle-agent` | `root` | check, 8h |
| `ssh-sre-infra` | `group:sre` | `tag:ceph`, `tag:compute-blade`, `tag:k3s-node` | `autogroup:nonroot` | accept |
| `ssh-sre-infra-root` | `group:sre` | `tag:ceph`, `tag:compute-blade`, `tag:k3s-node` | `root` | check, 8h |
| `ssh-members-own-devices` | `autogroup:member` | `autogroup:self` | `autogroup:nonroot` | accept |
| `ssh-members-own-devices-root` | `autogroup:member` | `autogroup:self` | `root` | check |

So, as an admin: root directly on the Ceph hosts, labk3s nodes, blades and
Home Assistant boxes; root after a fresh sign-in on isa, nuc, timepi, the
jumphost and meet. The jumphost can open sessions to every Buckle host and
the Pi clusters, but not as root on the hosts outside them.

Which local user to log in as differs per host: the Pi clusters and the
blades use `pi` (`ssh pi@blade-pi1`), isa and timepi `cedi`. meet's admin user is root, so
`ssh cedi@meet` is refused by design.

Hosts can't open Tailscale SSH sessions to each other: the only tag that's
a source in any rule is `tag:jumphost`. Copy data between hosts over the LAN.

SSH tests are in [`ssh-tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/ssh-tests.yaml):
`user:cedi` gets `cedi` on nuc directly and `root` in check mode.

The tailscaled side is [`modules/tailscale`](https://github.com/SpechtLabs/homelab/blob/main/modules/tailscale/module.yaml):
`tailscale_ssh: true` (the default) runs `tailscale set --ssh=true` on every
Debian host.
