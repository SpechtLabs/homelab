# Debug "I can't reach X"

Use this when a person or a host can't open something on the tailnet: a web
UI times out, an agent can't dial its server, a scrape fails, SSO breaks.

**Before you start:** a shell on the client that fails (or the person's
login and device), and Backstage. Everything below is read-only.

1. Check the name resolves to what you expect.

   ```sh
   dig +short <name>.sphinx-map.ts.net
   ```

   A Tailscale Service answers with its own VIP (list in
   [Tailscale Services](../reference/services.md)); a device with its node
   address. No answer means the Service or device doesn't exist under that
   name, or MagicDNS is off on the client.

2. Find out who the client is on the tailnet. On the client:

   ```sh
   tailscale whois $(tailscale ip -4)
   ```

   You'll see its `Tags:` line for a tagged device, or `User:` for a
   person's device. A person's groups come from Backstage (Group pages, or
   [Groups](../reference/groups.md)). On the destination host, `tailscale whois <client-ip>`
   tells you who an unexpected source address is.

3. Check the policy allows it. In Backstage open **Tailscale > Preview
   access**, choose "from" and pick the login or tag from step 2. The list
   shows every destination and port it reaches. Missing? The grant isn't
   there: see [Give a group or tag access to a Service](give-a-group-or-tag-access-to-a-service.md).
   Present but the policy on `main` is older? Check the last apply:

   ```sh
   gh run list --repo SpechtLabs/homelab --workflow tailscale.yaml --limit 3
   gh pr list --repo SpechtLabs/homelab --head backstage/tailnet-policy
   ```

   An open pull request from `backstage/tailnet-policy` means the catalog has
   changes that aren't applied yet ([Review and merge it](review-and-merge-the-policy-pull-request.md)).

4. Try the port itself. From a Mac:

   ```sh
   nc -vz <name>.sphinx-map.ts.net <port>
   ```

   The Pis have no `nc`; use bash:

   ```sh
   timeout 3 bash -c '</dev/tcp/<name>.sphinx-map.ts.net/<port>' && echo open || echo closed
   ```

5. Find the host behind a Service and check it serves every port.

   ```sh
   tailscale ping <name>.sphinx-map.ts.net
   ```

   The pong names the serving device (`pong from isa (100.70.89.41) ...` for
   `svc:nut`). On that host:

   ```sh
   tailscale serve status
   ```

   Every port of the Service's definition must be listed. A host that misses
   one drops out of the Service; the admin console's Services page then shows
   "required ports are missing". On the NAS, `serve status` prints "No serve
   config" even when it serves; use
   `sudo /var/packages/Tailscale/target/bin/tailscale --socket /var/packages/Tailscale/var/tailscaled.sock serve get-config --all`
   (shell: `ssh -J cedi@nyx king@nas.local`).

6. For device destinations (Ceph, the labk3s node mesh, tsidp, TKA), ping the
   device: `tailscale ping <device>`. No pong means the device is offline or
   unreachable, which no grant fixes.

## Check it worked

The step that failed now passes, and the user's request (the page, the
`upsc`, the scrape) works from the same client.

## Causes seen before

| Symptom | Cause | Fix |
|---|---|---|
| DSM SSO, Argo CD or Buckle sign-in fails after a retag | the relying party's device lost `tag:tsidp-client` (the NAS, 2026-11-25) | [Retag a device](retag-a-device.md), add `tag:tsidp-client` back |
| A Kubernetes egress proxy is refused although the annotation names the right tag | the operator applies tags only when it creates the proxy | delete the k8s Service and let Argo CD re-create it ([Retag a device](retag-a-device.md)) |
| A Buckle agent stops connecting after a retag | the server refuses devices without one of `agents.tailscale.allowed_tags` | widen `allowed_tags` in [`bootstrap/server.yaml`](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/server.yaml) first |
| `svc:nas` or `svc:stream` answers on a port it doesn't serve (`nas.<tailnet>:8096` reaches Jellyfin) | the NAS's Tailscale 1.98.4 passes every port of a Service address through to the device | not a bug; grants to those Services list their ports. Test again after a package update |
| `http://nas.sphinx-map.ts.net` gets nothing | `svc:nas` has no port 80 | use `https://` |
| "Ceph CSI — node plugin missing" after the labk3s nodes changed address | hostNetwork pods bound to the old `POD_IP` | restart ceph-csi's node plugin pods ([labk3s docs](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/)) |
| A change made in the admin console's policy editor is gone | the workflow applies `policy.hujson` on every merge | make the change in the catalog |
| NFS mount "access denied by server" through `svc:nfs` | the serve forward names `localhost`, which is `::1` on the NAS | forward to `127.0.0.1` ([Add a Tailscale Service](add-a-tailscale-service-on-a-host.md)) |

Why the NAS behaves differently, and which destinations are devices on
purpose: [Why some destinations stay devices](../explanation/why-some-destinations-stay-devices.md).
