# Why some destinations stay devices

The [model](abac-model.md) wants every destination to be a Service. Eight
aren't, and each has its own reason; Backstage's plugin knows the categories
and warns about any device destination outside them.

## Peer meshes: Ceph and labk3s

Ceph speaks only on the tailnet (`public_network` is 100.64.0.0/10 in
`modules/ceph`). A client asks a monitor for the cluster map and then talks
to every OSD at the OSD's own address. A Service in front would hide exactly
the addresses the protocol hands out. So the grants name `tag:ceph`: the
hosts among themselves on cephadm's sshd (2222), the mons (3300, 6789) and
the OSD and mgr range, and `tag:ceph-client` (the labk3s nodes, for
ceph-csi) on the same without 2222. The OSD range runs to 7568
(`ms_bind_port_max`) but skips 7480, RGW's port, which has no consumer; a
policy test caught it inside the range on 2026-11-26.

labk3s has run over the tailnet since 2026-11-26: node IPs, the server's
advertise address and flannel on `tailscale0`. Flannel's VXLAN (udp:8472),
the kubelet API (10250) and ceph-csi's metrics (8681) go node to node among
`tag:k3s-node`, and every node is a peer. The API itself isn't device
traffic any more: the server advertises `svc:labk3s`'s address, so the
`kubernetes` endpoint, the agents' load balancers and pods calling
`kubernetes.default` all use the Service, and no grant names the server.

A mesh has a sharp edge. A node half on the LAN and half on the tailnet can't
exchange VXLAN with the others, so a change to how the nodes connect has to
reach all of them within minutes, not one drain at a time. After such a
change, the hostNetwork pods that bind to `POD_IP` (ceph-csi's node plugin)
keep listening on the old address until their containers restart, and the
scrape fails ("Ceph CSI — node plugin missing").

## Capability targets: tsidp and TKA

tsidp and TKA authorize by reading capability grants that Tailscale matches
on the connection to their own address. tsidp also needs Funnel, so that
clients off the tailnet (specht-labs' Argo CD, Backstage, Grafana) can reach
it, and Funnel doesn't work on Services; tsidp can't serve a Service anyway.
TKA would need Service support in its tsnet code. Both stay devices, with
their grants narrowed to the one port each listens on (tcp:443 for tsidp,
tcp:8123 for TKA). The tailscaled web UI on 5252 is a capability target too:
it's per device by nature.

## Autogroups and everything

`autogroup:self` (members' own devices, for SSH and the web UI) and
`autogroup:internet` (exit nodes, for `group:vpn`) are about devices by
definition. `*` is the admins' break-glass grant. Backstage still renders a
separate catalog grant for a flow only `*` allows, so that the policy
doesn't quietly depend on break-glass.

## Metrics, which need no destination at all

Each host's own Alloy reads its exporters and tailscaled's metrics at
`http://100.100.100.100/metrics`, which only the host itself can reach, so
none of that needs a grant. The collector on isa scrapes only what can't run
Alloy, through a Service (`svc:node-exporter` on the NAS), and a test makes
sure it reaches no device's exporter port.

## The NAS, which is a device even through a Service

Not a destination class, but the same lesson: on the NAS's Tailscale (1.98.4,
DSM's package) a Service address passes every port through to the device,
served or not (`nas.<tailnet>:8096` reached Jellyfin in a test on
2026-11-26). isa, clusterpi-leader and hass-elbschloss on 1.104.x don't. So
grants to `svc:nas` and `svc:stream` list their ports, and anyone relying on
`*` meaning "what the Service offers" there should test again after a package
update.
