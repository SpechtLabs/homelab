# Add a Tailscale Service on a host

Use this when a service on one of the homelab's own hosts (isa, the NAS, a
Pi) should be reachable on the tailnet as `<name>.sphinx-map.ts.net`, or when
clients that reach a device today should reach a Service instead. For a
Kubernetes workload, see [Expose a Kubernetes service on the tailnet](expose-a-kubernetes-service-on-the-tailnet.md).

**Before you start:** admin access to the Tailscale admin console, and a
shell on the host. The change takes two pushes: first the Service and its
grants, then (after the clients have moved) the removal of any old device
grant.

1. Make sure the name is free. A Service can't take a name a device already
   has in MagicDNS; that's why the NAS is `nas-elbschloss` and Home Assistant
   `hass-elbschloss`. Rename the device first if needed.

   ```sh
   dig +short <name>.sphinx-map.ts.net
   ```

   should print nothing.
2. Define the Service in the admin console (Services): its name and every
   port, e.g. `tcp:3493`. This definition is the one piece that lives
   nowhere in git; note it in the API's `definition` text.
3. Give the host its own tag. Add an entity to
   [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml),
   owned by admins only, like `tag-nut-server`:

   ```yaml
   spec:
     type: tag
     target: tailscale:sphinx-map
     owner: group:spechtlabs
     system: tailnet
     tag: tag:<host-tag>
     owners: [group:admins]
     appliesTo: [component:<the-serving-component>]
   ```

   Reuse a host tag that already exists if this host serves other Services
   (`tag:nas` serves four).
4. Let that tag, and only that tag, advertise the Service: add it to an
   entity in [`tailscale/policy/auto-approvers.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/auto-approvers.yaml)
   (`services: { svc:<name>: [tag:<host-tag>] }`). Never approve a Service
   for a broad tag: the Kubernetes operators' proxies can carry tags the
   operators own.
5. Describe the API and its users in the catalog: on the API entity,
   `specht-labs.de/tailnet-dst: svc:<name>`, `specht-labs.de/tailnet-ports`
   with every port, `specht-labs.de/tailnet-allow` for groups; on consuming
   Components, `consumesApis` and `specht-labs.de/tailnet-src`. Details in
   [Give a group or tag access to a Service](give-a-group-or-tag-access-to-a-service.md).
6. [Check it locally](check-a-policy-change-locally.md), push, and
   [merge Backstage's pull request](review-and-merge-the-policy-pull-request.md).
   The tag must be in the live policy before the next step.
7. Tag the host: [admin console > Machines](https://login.tailscale.com/admin/machines)
   > the host > Edit ACL tags, and add the host tag next to the ones it has.
   On a Buckle host keep `tag:buckle-agent`.
8. Serve every port of the definition on the host. Put it in the host's
   module so it survives a rebuild; [`modules/nut-server`](https://github.com/SpechtLabs/homelab/blob/main/modules/nut-server/module.yaml)
   does it like this:

   ```yaml
   - command.run:
       run: [tailscale, serve, --service=svc:nut, --tcp=3493, 'tcp://localhost:3493']
       unless: 'tailscale serve get-config --all | grep -q "\"tcp:3493\": \"tcp://localhost:3493\""'
     id: svc-nut
     removal: leave
   ```

   By hand (the NAS, which Buckle doesn't manage) it's one command per port,
   as in [`nas/README.md`](https://github.com/SpechtLabs/homelab/blob/main/nas/README.md):

   ```sh
   sudo tailscale serve --service=svc:nas --https=443 https+insecure://localhost:5001
   sudo tailscale serve --service=svc:nfs --tcp=2049 tcp://127.0.0.1:2049
   ```

   Write `127.0.0.1`, not `localhost`, when the backend checks the client
   address: on the NAS `localhost` is `::1`, and DSM's NFS rule for
   `127.0.0.1` then refuses every client ("access denied by server").
9. Move the clients to `<name>.sphinx-map.ts.net` (a var, a module, an app's
   config) and push that.
10. Once the clients work through the Service, remove the old grant to the
    device in a separate change and pull request, and add a test that denies
    the device's own address ([Add a policy test](add-a-policy-test.md);
    `test-nut` is the model).

## Check it worked

On the host:

```sh
tailscale serve status
```

lists every port with `(svc:<name>)`. From a client, `dig +short <name>.sphinx-map.ts.net`
prints the Service's VIP, `tailscale ping <name>.sphinx-map.ts.net` answers
from the host, and the port connects. The admin console's Services page
shows the host as serving, without "required ports are missing". Add the
new row to [Tailscale Services](../reference/services.md).

## If it didn't

- "required ports are missing": the host serves fewer ports than the
  definition lists. A host that misses one gets no traffic for any port.
- The host isn't approved: its tag isn't in the live policy yet (step 6), or
  the auto approver names a different tag.
- On the NAS (Tailscale 1.98.4 from DSM's package) a Service address passes
  every port through to the device, served or not. Grants to NAS Services
  must list ports; never `*`.
- To roll back, revert the catalog change and merge the next pull request.
  On the host, `tailscale serve drain svc:<name>` takes it out of the
  Service (the step [Move a Tailscale Service](move-a-tailscale-service-to-another-host.md)
  uses).

!!! warning "Unverified"
    Removing a Service's serve config from a host for good isn't recorded in
    the repos. One known trap: node-level serve handlers keyed to an old
    device name had to be removed through the LocalAPI's serve config,
    because the CLI's `off` looks up the device's current name.
