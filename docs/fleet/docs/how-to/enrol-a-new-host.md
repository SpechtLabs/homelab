# Enrol a new host

Use this when a new Debian, Ubuntu or Raspberry Pi OS machine should be managed by Buckle, or when
you reinstall one.

**Before you start:**

- The host's name. Its **tailnet node name is its Buckle host id**: `buckle.yaml`, `vars/`, the
  fixtures and `base`'s `hostname.set` all key off it. Pick it before the host joins the tailnet.
- A shell on the host (console or SSH on the LAN) with sudo.
- The Buckle UI's **Add an agent** button doesn't work here: it needs a Tailscale OAuth client to
  mint tagged keys, and `provisioning` is commented out in `bootstrap/server.yaml`. The host joins
  the tailnet by hand instead.

1. Put the host on the tailnet with `tag:buckle-agent`. The server only trusts nodes carrying that
   tag (`agents.tailscale.allowed_tags`); any other node is refused, not queued. On the host:

    ```sh
    curl -fsSL https://tailscale.com/install.sh | sh
    sudo tailscale up --hostname=<name> --advertise-tags=tag:buckle-agent --ssh
    ```

    Sign in as an admin when it prints the login URL (`group:admins` owns `tag:buckle-agent`).
    Add the role tags the host needs for network access at the same time; which ones is the
    [tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)' business.
    Check with `tailscale status --self` that the name is exactly the one you picked.

2. Install the agent at the fleet's version and point it at `svc:buckle`. On your Mac, from the
   repo:

    ```sh
    v=$(sed -n 's/^buckle_version: //p' vars/versions.yaml)
    ssh <user>@<name> "curl -fsSL https://github.com/SierraSoftworks/buckle/releases/download/v$v/install.sh | sudo sh -s -- --version $v up --server http://buckle.sphinx-map.ts.net:7700 --insecure-plaintext"
    ```

    `--insecure-plaintext` is right here: the connection runs inside WireGuard and the server
    identifies the agent by Tailscale whois. Don't pass `--host-id` unless the system hostname
    differs from the node name, and then pass the node name: an agent claiming another id than
    the tailnet's is refused.

3. Check that it registered. Tagged nodes become `active` at once (`registration: auto`):

    ```sh
    curl -s -b "$J" "$B/api/v1/hosts/<name>" | python3 -c '
    import json, sys; h = json.loads(sys.stdin.read(), strict=False); print(h["status"], h["agent_version"], h["groups"])'
    ```

    The groups come from its facts ([Groups](../reference/groups.md)). If they're not what the
    host is for, fix the facts or the selectors before it converges, not after.

4. Tell the repo about anything hardware can't. In a branch:
    - Its login account if it isn't `pi`: add a `vars/host-<name>.yaml` with `admin_user: <user>`
      and a matching `- when: 'host.id == "<name>"'` entry under `vars:` in `buckle.yaml`. The
      dotfiles installer also needs passwordless sudo for that account (isa has
      `/etc/sudoers.d/90-cedi`, made by hand).
    - A phase other than `fleet`: only the four `core` hosts are listed by id
      ([Hosts and phases](../reference/hosts.md)).
    - A role with no hardware fact (Buckle server, k3s server, Jitsi): a `host.id` group in
      `buckle.yaml`. Prefer a fact where one exists ([Facts over hostnames](../explanation/facts-over-hostnames.md)).
    - Its facts fixture, so CI plans it: [Update a host's fixture](update-a-host-fixture.md).

    Run `mise run validate`, open a PR, merge.

5. Let it converge. The host joins the next rollout's phase, or the current rollout's
   `stragglers` stage. To converge it now, start a rollout of the stable revision: **Rollouts**,
   **Re-apply…** on the stable revision's row.

## Check it worked

```sh
ssh <user>@<name> "bash -c 'sudo buckle status | head -3; sudo buckle health | tail -1'"
```

shows the agent connected to `http://buckle.sphinx-map.ts.net:7700`, the stable revision applied,
and `health   healthy`. The host's page lists it with its groups; Grafana gets its metrics and logs
from Alloy (label `hostname="<name>"` on logs).

## If it didn't

- The agent log (`sudo journalctl -u buckle-agent -e`) says `The tailnet node '<name>' is not
  trusted as an agent`: the node lacks `tag:buckle-agent`. Add it in the admin console (Machines,
  the host, Edit ACL tags) and restart the agent.
- It says `This agent claims to be 'x', but the tailnet says it is 'y'`: `host_id` in
  `/etc/buckle/agent.yaml` doesn't match the node name. Set it to `null` (or the node name) and
  `sudo systemctl restart buckle-agent`.
- The agent can't reach the server at all (connection timeouts in its log): check that the
  tailnet policy still grants `tag:buckle-agent` access to `svc:buckle` on `tcp:7700`, and that
  `tailscale serve status` on isa lists `svc:buckle` with both ports.
- The first apply of `dotfiles` fails on sudo: the admin account lacks passwordless sudo.
