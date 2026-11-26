# Destinations that stay devices

Grants whose destination is a tag, an autogroup or `*` rather than a
Tailscale Service, and the reason for each. Backstage's tailnet plugin sorts
every destination into a class; `yarn tailscale:diff` prints the same list.
Why these can't be Services: [Why some destinations stay devices](../explanation/why-some-destinations-stay-devices.md).

| Destination | Class | Who reaches it | Ports | Reason |
|---|---|---|---|---|
| `tag:ceph` | peer mesh | `tag:ceph` (2222, 3300, 6789, 6800-7479, 7481-7568); `tag:ceph-client` (the same without 2222) | tcp | clients reach every OSD at its own address; 2222 is cephadm's sshd; 7480 (RGW) left out |
| `tag:k3s-node` | peer mesh | `tag:k3s-node` | udp:8472 (flannel VXLAN), tcp:10250 (kubelet), tcp:8681 (ceph-csi metrics) | every labk3s node is a peer |
| `tag:tsidp` | capability target | `autogroup:member`, `tag:tsidp-client`; capability grants for admins, SREs, Synology users | tcp:443 | tsidp reads capabilities matched on its own address and needs Funnel |
| `tag:tka` | capability target | `group:admins` | tcp:8123 | TKA reads its capability off the connection to its own address |
| `tag:smarthome` | capability target | `group:admins` | 5252 | tailscaled's web UI on each device |
| `autogroup:self` | autogroup | `autogroup:member` | 5252 | each member's own devices' web UI |
| `autogroup:internet` | autogroup | `group:vpn` | `*` | exit nodes |
| `*` | everything | `group:admins` | `*` | break-glass |

SSH rules always name devices (tags); they're listed in [SSH rules](ssh-rules.md).

The k3s API isn't on this list: the server advertises `svc:labk3s`'s address
as its `advertise-address`, so the `kubernetes` endpoint, the agents' load
balancers and pods calling `kubernetes.default` all go through the Service,
and no grant names `tag:k3s-server`.
