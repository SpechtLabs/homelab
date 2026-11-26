# Update a host's fixture

Use this after enrolling a host, after hardware changes (a HAT, an NVMe, a new NIC), or when a
fact a selector reads changed, so CI dry-plans the host as it really is. CI plans each host
against `fixtures/facts/<host id>.json`; a stale file means a green PR that fails on the real host.

**Before you start:** the API signed in ([Call the Buckle API](call-the-buckle-api.md)) and the
repo checked out. The repo is public: keep only what selectors and templates read, never raw facts
(they carry MAC addresses, public IPv6, local users and every systemd unit). Tailscale's own
addresses stay in (`tailscale.ips`): the k3s modules template `node-ip` from them, and they're
tailnet-internal.

1. Pull the host's current facts from the server and trim them:

    ```sh
    trim='{os, hardware: (.hardware | del(.disks, .disk)), net: {hostname: .net.hostname, fqdn: .net.fqdn}, tailscale: (.tailscale | if . then {hostname, tags, ips, online, backend_state, tailnet} else null end), script, cloud}'
    h=timepi
    curl -s -b "$J" "$B/api/v1/hosts/$h/facts" | jq "$trim" > "fixtures/facts/$h.json"
    ```

    For every host at once, loop over `curl -s -b "$J" "$B/api/v1/fleet" | jq -r '.hosts[].id'`.
2. Read the diff. Expect only the facts you meant to change:

    ```sh
    git diff fixtures/facts/
    ```

3. Validate and open a PR:

    ```sh
    mise run validate
    ```

    The line for the host lists its groups and selected modules; check them against what the host
    is for.

## Check it worked

`mise run validate` ends with `ok: no problems found` and the host's line shows the groups you
expect. CI's `validate` job passes on the PR.

## If it didn't

- `host.facts.script.rpi` or `host.facts.script.ptp` missing: those come from the `pi-facts` and
  `ptp-facts` modules and appear only after they applied once. Capture again after the host's
  first rollout.
- `jq` fails to parse: the response was an error (`{"error": ...}`), usually a `401`. Sign in again.
