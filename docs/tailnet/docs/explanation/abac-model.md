# The ABAC model

Every grant in the policy answers two questions: who is asking, and what are
they asking for. Since 2026-11-25 the answers have a fixed shape. The source
is an attribute, a group of people or a tag that says what a device is or
does (`tag:buckle-agent`: runs a Buckle agent; `tag:tsidp-client`: signs in
against tsidp; `tag:ceph-client`: maps Ceph volumes). The destination is a
Tailscale Service, `svc:<name>`, wherever the traffic allows one.

Before that, tags did both jobs. `tag:core-infra` meant "a core host" as a
source and "something that serves core things" as a destination, so a grant
to it reached every device that carried it, Kubernetes proxies included.
Moving a service to a new host meant retagging, editing grants and touching
clients in one go.

## Why Services as destinations

A Service maps its ports to whichever host serves it, and its VIP and name
stay put when the host changes. That's what made the move of the Buckle
server (`svc:buckle`) from the NUC to isa on 2026-11-23 a two-minute job
with no agent changes,
and it's why a second host could join a Service without a grant changing.
Clients name `nut.sphinx-map.ts.net`; the policy names `svc:nut`; neither
mentions isa.

It also tightens what a grant means. On most hosts a Service address offers
only the ports the host serves, so a grant to a Service can't reach anything
else on that host. The NAS is the exception (its Tailscale 1.98.4 passes every
port through), which is why its grants list ports and why Backstage warns
about a Service grant on `*`.

## One host tag per Service

Something has to decide which devices may serve a Service. The policy's
`autoApprovers` do, and each Service has exactly one approving tag: a tag
only that host carries, owned by `group:admins` alone (`tag:nas`,
`tag:nut-server`, `tag:k3s-server`, `tag:buckle-server`). The ownership is
the point: a tag the Kubernetes operators may hand out could end up on a
proxy, and that proxy could then advertise the Service and receive its
traffic. The two ingress tags (`tag:specht-labs-ingress`,
`tag:labk3s-ingress`) are owned by their operator as well, because it mints
the ProxyGroup replicas' keys; nothing else carries them. `svc:hass` is still
approved for `tag:smarthome`, which both Home Assistant boxes carry.

## Tags are identity

A tag says what a device is, so changing one is a deliberate act in the
admin console. [`modules/tailscale`](https://github.com/SpechtLabs/homelab/blob/main/modules/tailscale/module.yaml)
never touches tags; hosts get theirs at enrolment. Buckle's own roles that
decide where the server, tsidp or the collector run select by host id, not
by tag, because Buckle only sees a new tag after the agent restarts and a
tag-derived role couldn't move in one rollout.

## Changing a path in two pushes

Switching clients from a device to a Service happens in two steps: first the
Service, its approver and its grant, with the host serving and the clients
moved over; then, once that works, a second change removes the old device
grant and adds a test that denies the device's own address. At no point is
there a policy in which neither path works. `test-nut`, `test-buckle` and
`test-labk3s` are what's left of three such switches.

## What doesn't fit

Some traffic can't go through a Service at all: Ceph and the labk3s node
mesh, where every peer is reached at its own address; tsidp and TKA, which
read capabilities off connections to their own address; per-device things
like the web UI and exit nodes. Those stay device destinations, and
[Why some destinations stay devices](why-some-destinations-stay-devices.md)
goes through each.
