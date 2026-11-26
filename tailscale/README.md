# Tailnet policy

`policy.hujson` is the whole tailnet policy. `.github/workflows/tailscale.yaml`
tests it on pull requests and applies it on `main`. Tailscale runs the policy's
`tests` on every save, so a failing test rejects the push and the previous
policy stays live. Edits in the admin console get overwritten.

## The model

A grant says *who* (an attribute) may reach *what* (a Service):

- **Sources are attributes.** A group (`group:hass-users`) or a tag that says
  what a device *is* or *does*: `tag:buckle-agent` (runs a Buckle agent),
  `tag:o11y-collector`, `tag:tsidp-client` (signs in against tsidp),
  `tag:ceph-client` (maps Ceph volumes).
- **Destinations are Tailscale Services** (`svc:<name>`), not devices. The
  Service maps its ports to whichever host serves it, so the host can move
  or be joined by a second one without touching a client or a grant.
- **Each Service has one host tag as its only autoApprover**, owned by
  admins only: `tag:nas` may serve `svc:nas` and `svc:stream`,
  `tag:nut-server` `svc:nut`, `tag:k3s-server` `svc:labk3s`,
  `tag:buckle-server` `svc:buckle`. `tag:specht-labs-ingress` is also
  owned by `tag:k8s-operator`, which mints its proxies' keys. Never approve a
  Service for a broad tag: the k8s operators' proxies carry such tags too.

| Service | Host | Ports | Who |
|---|---|---|---|
| `svc:buckle` | isa | 443, 7700 | admins and SREs (UI), `tag:buckle-agent` (agents) |
| `svc:nut` | isa | 3493 | `tag:buckle-agent` |
| `svc:nas` | nas-elbschloss | 443, 5001, 6690 | `group:synology-users`, the collector (443) |
| `svc:stream` | nas-elbschloss | 443 | `group:synology-users`, the collector |
| `svc:hass` | hass-elbschloss (HA add-on `services:`) | 443, 8123 | `group:hass-users`, the collector |
| `svc:labk3s` | clusterpi-leader | 6443 | admins, the collector |
| `svc:lgtm`, `svc:argocd`, `svc:backstage` | the specht-labs `tailnet-ingress` ProxyGroup | 80 / 443 | LGTM push and query / admins |

## What stays on devices

Some traffic belongs to one machine by nature, so its grant names a tag or a
device:

- SSH (the `ssh` rules: `tag:homelab` and `tag:buckle-agent` as targets).
- Scraping exporters (`tag:o11y-collector` -> `*` on the exporter ports).
- Exit nodes, `autogroup:self`, the tailscaled web UI on 5252.
- tsidp and tka: they read capability grants matched on their own address,
  and tsidp needs Funnel, which Services don't support. tsidp (`idp`) stays a
  device; don't rename it, because the OIDC issuer and the email claims are
  derived from its name.
- NFS v3 to the NAS (portmapper and mountd on dynamic ports): only the Buckle
  server's backup, to `nas-elbschloss`.
- Ceph: clients reach every OSD at its own address. `tag:ceph` hosts among
  themselves, `tag:ceph-client` (the labk3s nodes) to them, on the mon and OSD
  ports. The OSD range skips 7480, RGW's port.
- labk3s: k3s runs over the tailnet (node-ip, the server's advertise-address
  and flannel on `tailscale0`). Agents join through `svc:labk3s`, then use the
  server's own tailnet address that Kubernetes advertises; flannel's VXLAN
  (udp 8472), the kubelet API (10250) and ceph-csi's metrics (8681) run node
  to node among `tag:k3s-node`. A node half on the LAN and half on the
  tailnet can't exchange VXLAN with the others, so a change to how the nodes
  connect has to reach all of them within minutes, not one drain at a time.

## Adding a Service

1. Define it in the admin console (Services): name and ports. The definition
   is the one piece that doesn't live here.
2. Add an admin-owned host tag to `tagOwners`, the Service to
   `autoApprovers.services` with that tag, and the grants. Push.
3. Tag the host in the console, then serve every port of the definition on
   it (`tailscale serve --service=svc:<name> ...`, or a module task like
   `modules/nut-server`). A host that misses a port drops out of the Service
   ("required ports are missing").
4. Move the clients to `<name>.sphinx-map.ts.net`, check, then remove the old
   device grant in a separate push.
5. Keep the catalog in step: an API's `specht-labs.de/tailnet-dst` names the
   Service, a consumer's `tailnet-src` its attribute tag.

## Gotchas

- A Service name can't be taken while a device holds the same MagicDNS name:
  that's why the devices are `hass-elbschloss` and `nas-elbschloss`.
- On most hosts a Service address offers only the served ports, so `"*"` in a
  grant means "what the Service offers". **Not on the NAS** (Tailscale 1.98.4
  in DSM's package): its Service addresses pass every port through to the
  device (`nas.<tailnet>:8096` reaches Jellyfin), so grants to `svc:nas` and
  `svc:stream` list their ports. Test again after updating the package.
- The k8s operator applies a proxy's tags only when it creates the proxy. To
  retag, change the annotation, then delete the k8s Service and let Argo CD
  re-create it: the operator removes the old device, and the new one gets the
  same name but a new address.
- The Buckle server refuses an agent whose device carries none of its
  `agents.tailscale.allowed_tags` (`bootstrap/server.yaml`), even when it is
  already registered. Widen `allowed_tags` (server restart) before retagging.
- Before retagging a host, check what it is a client of. DSM signs in through
  tsidp, so the NAS needs `tag:tsidp-client`: every `consumesApis:
  api:tsidp-oidc` in the catalogs is a relying party.
