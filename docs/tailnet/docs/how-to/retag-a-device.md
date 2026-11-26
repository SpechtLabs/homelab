# Retag a device

Use this when a device should carry different tags: it takes on a new role,
loses one, or a tag gets retired. Tags are identity here; every grant source
that isn't a person is a tag, so a retag changes what the device reaches.

**Before you start:** list what the device does with its current tags.

- In Backstage, **Tailscale > Preview access**, "from" each tag it carries:
  everything it reaches today.
- Every relying party of tsidp needs `tag:tsidp-client`. Find them with
  `git grep -n 'api:tsidp-oidc'` in SpechtLabs/homelab and
  SpechtLabs/k8s-deployment. The NAS lost SSO on 2026-11-25 because a retag
  dropped this.
- SSH rules target tags (`tag:buckle-agent`, `tag:ceph`, `tag:k3s-node`,
  `tag:compute-blade`, `tag:smarthome`): without them you lose Tailscale SSH
  to the device ([SSH rules](../reference/ssh-rules.md)).
- A new tag has to exist in [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml)
  and be live (merged and applied) first.

## A host

1. On a Buckle host that's to lose `tag:buckle-agent`, widen the server's
   `agents.tailscale.allowed_tags` in
   [`bootstrap/server.yaml`](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/server.yaml)
   first and restart the server. It refuses a device that carries none of
   them, even one that's already registered.
2. Change the tags: [admin console > Machines](https://login.tailscale.com/admin/machines)
   > the device > Edit ACL tags. [`modules/tailscale`](https://github.com/SpechtLabs/homelab/blob/main/modules/tailscale/module.yaml)
   never touches tags, so Buckle won't undo it.
3. Buckle keeps the facts (tags included) a host reported at enrolment
   until its agent restarts. If anything in `buckle.yaml` should see the new
   tags, restart the agent on the host:

   ```sh
   ssh <user>@<host> "bash -c 'sudo systemctl restart buckle-agent'"
   ```

   The roles that matter most (`buckle-server`, `o11y-collector`, `tsidp`,
   `nut-server`) select by host id for exactly this reason.
4. Update `appliesTo` on the tag entities in `tags.yaml` so Backstage shows
   the right carriers.

## A Kubernetes proxy

The Tailscale operator applies a proxy's tags only when it creates the proxy.
This covers egress proxies (`tailscale.com/tailnet-fqdn`, for example
`k3s-idp-egress` in [`apps/tailscale/cluster/labk3s/ts-egress-idp.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/tailscale/cluster/labk3s/ts-egress-idp.yaml)).

1. Change `tailscale.com/tags` on the Kubernetes Service in
   SpechtLabs/k8s-deployment and push.
2. Delete the Kubernetes Service and let Argo CD re-create it:

   ```sh
   KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s -n tailscale delete svc k3s-idp-egress
   ```

   The operator removes the old device; the new one has the same name, the
   new tags and a new address.

!!! danger "Not for ProxyGroup Services"
    Never do this to a Service or Ingress with `tailscale.com/proxy-group`:
    there `tailscale.com/tags` tags the Tailscale Service, and deleting it
    deletes the Service and its VIP ([Expose a Kubernetes service](expose-a-kubernetes-service-on-the-tailnet.md)).
    The ProxyGroup replicas' own tag is fixed when a replica first joins.

## A Home Assistant box

The Home Assistant Tailscale add-on (`a0d7b954_tailscale`) advertises the
box's tags from its `advertise_tags` option; hass-elbschloss has
`[tag:smarthome, tag:hass-server]`. Change the tags in the admin console as
for a host, then set `advertise_tags` to the same list in the Tailscale
add-on's Configuration tab in Home Assistant, so the add-on doesn't ask for
the old ones at its next start. The option takes effect at that next start;
with the console already changed there's no need to restart it now, and a
restart drops `svc:hass` until the add-on is back, because the add-on
serves the Service too.

To read the current options without the UI, Tailscale SSH to the box as
root lands in the SSH add-on, where:

```sh
ha apps info a0d7b954_tailscale --raw-json | jq '.data.options.advertise_tags'
```

## tsidp

tsidp advertises its tag itself (`tsidp_advertise_tags: "tag:tsidp"` in
[`modules/tsidp/module.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/tsidp/module.yaml)).
Don't rename or re-create its device `idp`: the OIDC issuer and every
email claim derive from the name ([tsidp's design](../explanation/tsidp-design.md)).

## Check it worked

```sh
tailscale whois <device-ip>
```

shows the new `Tags:` line. Preview access in Backstage "from" the new tags
lists what you expected, and the device's own clients (SSO, Buckle, NUT,
LGTM pushes) still work.

## If it didn't

Put the old tags back in the admin console (hosts) or revert the annotation
and delete the Service again (proxies). After a host retag, check the Buckle
UI that the agent is connected.
