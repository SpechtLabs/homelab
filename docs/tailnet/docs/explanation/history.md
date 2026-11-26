# History

How the policy got to its present shape. Times are CET (UTC+1); commit
hashes are in SpechtLabs/homelab unless noted.

**2026-11-17.** The policy moves into this repo as `tailscale/policy.hujson`,
tested on pull requests and applied on `main` by `.github/workflows/tailscale.yaml`
(d341129). From then on, edits in the admin console get overwritten.

**2026-11-18.** tsidp tokens for `group:admins` carry `groups: ["buckle-admins"]`
(001d565): Buckle's admin rights come from the policy.

**2026-11-23.** isa replaces the NUC as Buckle server, tsidp host, NUT proxy and
o11y collector. The Buckle server moves behind `svc:buckle` in about two
minutes without the agents noticing.

**2026-11-25.** The move to attribute sources and Service destinations
starts. Devices are renamed (`hass` to `hass-elbschloss`, `nas` to
`nas-elbschloss`) so Services can take the short names, and `svc:nas`,
`svc:hass`, `svc:nut` and `svc:labk3s` appear. `tag:core-services` (927a2f1)
and `tag:core-infra` (db8c8eb) leave every grant. The same day DSM's sign-in
broke: the NAS had reached tsidp as `tag:core-infra`, and the fix was giving
it `tag:tsidp-client`.

**2026-11-26, after midnight.** The Ceph OSD range splits around RGW's 7480
after a policy test failed on it (11b8f61, 00:27). labk3s moves onto the
tailnet: node IPs, flannel and the server's advertise address on
`tailscale0` (760a24a, 00:59). `tag:homelab` (884df1e) and
`tag:o11y-endpoint` (5f84797) are retired. The specht-labs
`k8s-load-balancer` device gives way to the `tailnet-ingress` ProxyGroup
serving `svc:lgtm`, `svc:argocd` and `svc:backstage` (k8s-deployment
6c494a7d, 01:33); on labk3s a ProxyGroup serves `svc:labk3s-argocd-api`
and `svc:lab-argocd`, and `tag:lab-argocd` goes (bb2c00b, 02:08).

**2026-11-26, afternoon.** The k3s server advertises `svc:labk3s`'s VIP
(3ad28d7, 15:21) and the grant to `tag:k3s-server` goes (cb3b742).

**2026-11-26, evening.** The policy becomes Backstage entities (43be037,
20:59) and grants start coming from the services' annotations (aafd1ed,
21:31). The NAS gets `svc:node-exporter` and `svc:nfs` (7e34b90); the
collector's grant to every device's exporters goes, since every host's own
Alloy now scrapes its tailscaled (8fe174e). tsidp becomes reachable only by
members and relying parties, on tcp:443 (9780246). Backstage publishes the file as a pull
request (2d087d1, 22:44), and TKA's capability grant narrows to tcp:8123
(004d883). The first rendered policy, pull request #20 (28 grants, 7 SSH
rules, 21 tests), merges at 23:00.

**2026-11-27.** `svc:hass` gets a host tag of its own, `tag:hass-server` on
hass-elbschloss, so hass-schiltach (also `tag:smarthome`) can't serve it.
hass-elbschloss drops `tag:o11y-agent`, which only duplicated what
`tag:smarthome` already gets, and the unused `tag:opencode` (carried over
from the admin console's policy on 2026-11-17, never on a device or in a
rule) leaves the policy. clusterpi-leader (`tag:k3s-server`) joins isa as a
source for `svc:nfs`: both back up to the NAS through `modules/nas-backup`.

## Retired tags

| Tag | Retired | Notes |
|---|---|---|
| `tag:core-services` | 2026-11-25 | its tagOwners entry stayed until Home Assistant's add-on stopped advertising it |
| `tag:core-infra` | 2026-11-25 | tagOwners stayed while `k8s-load-balancer` carried it (its address was the A record of `*.k8s.specht-labs.de`) |
| `tag:homelab` | 2026-11-26 | had become only an SSH target; SSH rules now name attribute tags |
| `tag:o11y-endpoint` | 2026-11-26 | no device carried it |
| `tag:lab-argocd` | 2026-11-26 | Backstage reaches the labk3s Argo CD API only through `svc:labk3s-argocd-api` |
| `tag:opencode` | 2026-11-27 | for an OpenCode web UI; no device ever carried it here and no rule named it |
