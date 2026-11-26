# Capability grants and node attributes

Grants with an `app` block carry capabilities that an application reads off
the connection: tsidp, TKA and tailscaled's web UI match them against their
own address. They live in
[`tailscale/policy/grants.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/grants.yaml)
with the other grants annotations can't express.

## Capability grants

| Entity | Source | Destination, port | Capability | Effect |
|---|---|---|---|---|
| `grant-tsidp-admins` | `group:admins` | `tag:tsidp` tcp:443 | `tailscale.com/cap/tsidp`: `allow_admin_ui`, `allow_dcr`, `extraClaims.groups: [buckle-admins]`, `includeInUserInfo` | admins use tsidp's admin UI and `/register`; Buckle's `user_acl` and `admin_acl` check `buckle-admins` |
| `grant-tsidp-grafana-admins` | `group:admins` | `tag:tsidp` tcp:443 | `extraClaims.groups: [grafana-admins]`, `includeInUserInfo` | Grafana maps it to its Admin role |
| `grant-tsidp-synology` | `group:synology-users` | `tag:tsidp` tcp:443 | `users: [group:synology-users]`, `resources: [synology]` | Synology users sign in to DSM through tsidp |
| `grant-tsidp-argocd-sre` | `group:sre` | `tag:tsidp` tcp:443 | `users: [group:sre]`, `resources: [argocd]` | SREs sign in to Argo CD through tsidp |
| `grant-tka-admins` | `group:admins` | `tag:tka` tcp:8123 | `specht-labs.de/cap/tka`: `role: cluster-admin`, `period: 1h` | cluster-admin on both clusters (`tka`, `lab-tka`) for an hour at a time |
| `grant-webui-admins` | `group:admins` | `tag:smarthome` 5252 | `tailscale.com/cap/webui`: `canEdit: ['*']` | edit everything in the Home Assistant boxes' tailscaled web UI |
| `grant-webui-self` | `autogroup:member` | `autogroup:self` 5252 | `canEdit: [account, ssh, exitNodes]` | members manage their own devices' web UI, not subnet routers |

tsidp unions list claims across grants: an admin's token carries
`groups: ["buckle-admins", "grafana-admins"]`.

## Plain grants kept in `grants.yaml`

| Entity | Source | Destination | Ports |
|---|---|---|---|
| `grant-admins-everything` | `group:admins` | `*` | `*` |
| `grant-vpn-exit-nodes` | `group:vpn` | `autogroup:internet` | `*` |

## Node attributes

From [`tailscale/policy/node-attrs.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/node-attrs.yaml):

| Entity | Nodes | Attribute |
|---|---|---|
| `attr-operators-funnel` | `tag:k8s-operator`, `tag:k3s-operator` | `funnel` |
| `attr-tsidp-funnel` | `tag:tsidp` | `funnel` |
| `attr-vpn-mullvad` | `group:vpn` | `mullvad` (the Mullvad exit nodes) |
