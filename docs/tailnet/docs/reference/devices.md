# Devices

The tagged devices the homelab runs on the tailnet, from
`tailscale status --json` on 2026-11-26. Addresses can change when a device
is re-created (Kubernetes proxies are, on a retag); check with
`dig +short <name>.sphinx-map.ts.net`. People's own devices are untagged and
not listed here.

| Device | Address | Tags | What |
|---|---|---|---|
| isa | 100.70.89.41 | buckle-agent, buckle-server, nut-server, o11y-collector, tsidp-client | Buckle server, NUT proxy, o11y collector; hosts tsidp's process |
| idp | 100.77.112.23 | tsidp | tsidp, its own tailnet node on isa; Funnel |
| nuc | 100.122.149.90 | buckle-agent | the core host until isa replaced it on 2026-11-23; still a Buckle host |
| jumphost | 100.83.246.57 | buckle-agent, jumphost | Pi 5; may open Tailscale SSH to the rest |
| timepi | 100.76.183.25 | buckle-agent | GPS/PPS time server |
| meet | 100.85.86.18 | buckle-agent, o11y-agent | Jitsi |
| clusterpi-leader | 100.92.89.43 | buckle-agent, ceph-client, k3s-node, k3s-server | labk3s server, serves `svc:labk3s` |
| clusterpi-worker1..4 | 100.94.152.81, 100.123.236.103, 100.126.248.78, 100.103.254.83 | buckle-agent, ceph-client, k3s-node | labk3s agents |
| storagepi-ceph1..3 | 100.105.212.35, 100.107.71.68, 100.118.224.54 | buckle-agent, ceph | Ceph |
| blade-pi1..4 | 100.127.89.27, 100.105.166.24, 100.123.23.104, 100.97.100.127 | buckle-agent, compute-blade | compute blades |
| nas-elbschloss | 100.71.201.45 | nas, tsidp-client | the Synology; serves four Services; offers itself as an exit node |
| hass-elbschloss | 100.75.135.70 | hass-server, smarthome | Home Assistant at home, serves `svc:hass`; tags from the add-on's `advertise_tags` |
| hass-schiltach | 100.89.41.43 | smarthome | Home Assistant in Schiltach |
| tka | 100.82.255.26 | tka | TKA on specht-labs |
| lab-tka | 100.119.91.34 | tka | TKA on labk3s |
| tailscale-operator-1 | 100.78.81.102 | k8s-operator | the specht-labs operator |
| lab-tailscale-operator | 100.90.219.50 | k3s-operator | the labk3s operator |
| specht-labs-ingress-0, -1 | 100.112.226.15, 100.68.69.67 | specht-labs-ingress | specht-labs `tailnet-ingress` ProxyGroup |
| labk3s-ingress-0, -1 | 100.104.47.26, 100.101.54.99 | labk3s-ingress | labk3s `tailnet-ingress` ProxyGroup |
| backstage-lab-argocd | 100.122.178.57 | backstage | Backstage's egress to `svc:labk3s-argocd-api` |
| monitoring-lab-lgtm-egress | 100.64.181.8 | o11y-agent | labk3s's egress to `svc:lgtm` |
| tailscale-k3s-idp-egress | 100.105.71.45 | tsidp-client | labk3s's egress to idp (labk3s Argo CD's OIDC) |

## Exit nodes

- The Mullvad exit nodes, for `group:vpn` only (node attribute `mullvad`).
- nas-elbschloss is an exit node: its tailscaled (DSM's Tailscale package)
  advertises `0.0.0.0/0` and `::/0`, set in the package, not by any repo.
  `tailscale status` lists it as "offers exit node". Traffic through it
  leaves from the home LAN. Who uses it isn't visible in the NAS's
  `tailscale status` or prefs; clients choose an exit node on their side. Check
  with
  `sudo /var/packages/Tailscale/target/bin/tailscale --socket /var/packages/Tailscale/var/tailscaled.sock debug prefs | grep -A3 AdvertiseRoutes`
  on the NAS.
- `modules/tailscale` can make a Buckle host an exit node
  (`tailscale_exit_node: true`); no host sets it today.

`group:vpn` may use exit nodes through the grant `grant-vpn-exit-nodes`
(`autogroup:internet`).

## Host aliases in the policy

`spec.hosts` in [`tailscale/policy/policy.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/policy.yaml)
names six devices for the tests: nas-elbschloss, clusterpi-leader,
hass-elbschloss, nuc, idp, hass-schiltach. Keep their addresses there in
step with the devices.
