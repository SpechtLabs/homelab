# Move a Tailscale Service to another host

Use this when a Service's host is replaced or retired (as the NUC handed
`svc:buckle` to isa on 2026-11-23). Clients keep using
`<name>.sphinx-map.ts.net` and its VIP; no client config or grant changes.

**Before you start:** the new host is on the tailnet and runs the backend.
For `svc:buckle` follow the full server move in
[`bootstrap/README.md`](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/README.md)
("Moving the server to another host"), which adds the data copy and
`agents.trusted_proxies`; this page is the tailnet part.

1. Give the new host the Service's host tag (admin console > Machines > the
   host > Edit ACL tags). The auto approver names the tag, not the host, so
   nothing in the policy changes. Update the tag entity's `appliesTo` in
   [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml)
   if it names the host.
2. On the old host, take it out of the Service:

   ```sh
   sudo tailscale serve drain svc:<name>
   ```

3. Stop the backend on the old host if only one instance may run (the Buckle
   server, NUT's upsd).
4. On the new host, serve every port of the definition. For a Buckle-managed
   Service that's the module's serve task, which runs once the host is in the
   module's group (`buckle.yaml` selects these by host id, e.g.
   `nut-server: 'host.id == "isa"'`). By hand, the same commands as on the old
   host; for `svc:buckle`:

   ```sh
   ip=$(tailscale ip -4)
   sudo tailscale serve --bg --service=svc:buckle --https=443 "http://$ip:7701"
   sudo tailscale serve --bg --service=svc:buckle --tcp=7700 --proxy-protocol=2 "tcp://$ip:7700"
   ```

5. Remove the host tag from the old host once it no longer serves.

## Check it worked

```sh
tailscale ping <name>.sphinx-map.ts.net
```

answers from the new host, and `tailscale serve status` there lists every
port. For `svc:buckle` the agents reconnect on their own; for `svc:nut`, the
clients' health check `ups-reachable` passes again.

## If it didn't

- The new host serves but gets no traffic: a port of the definition is
  missing ("required ports are missing" in the admin console), or the host
  lacks the host tag.
- Back out by serving again on the old host and draining the new one.
