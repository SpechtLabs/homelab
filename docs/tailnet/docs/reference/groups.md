# Groups

The policy's groups are Backstage Groups in the private
[SpechtLabs/backstage_resources `catalog/org.yaml`](https://github.com/SpechtLabs/backstage_resources/blob/main/catalog/org.yaml).
A Group's `specht-labs.de/tailnet-group` annotation is its name in the
policy; a member User's `specht-labs.de/tailnet-login` is the login that
appears in it. Membership lives only there; see
[Add or remove a person](../how-to/add-or-remove-a-person.md).

| Policy group | Backstage Group | What it gets |
|---|---|---|
| `group:admins` | `tailnet-admins` | everything (`grant-admins-everything`); SSH everywhere Buckle reaches, root on the Pi clusters and Home Assistant, root in check mode elsewhere; cluster-admin through TKA; tsidp admin UI and client registration; `buckle-admins` and `grafana-admins` claims; the smart-home devices' web UI |
| `group:sre` | `tailnet-sre` | SSH to the Ceph hosts, compute blades and labk3s nodes (root in check mode); `svc:buckle` UI; `svc:lab-argocd`; Argo CD sign-in through tsidp |
| `group:vpn` | `tailnet-vpn` | the exit nodes (`autogroup:internet`) and the Mullvad exit nodes (node attribute `mullvad`) |
| `group:synology-users` | `tailnet-synology-users` | `svc:nas` (443, 5001, 6690), `svc:stream`; Synology sign-in through tsidp |
| `group:hass-users` | `tailnet-hass-users` | `svc:hass` (443, 8123) |

Every member also gets what `autogroup:member` gets: tsidp sign-in
(`tag:tsidp` tcp:443), Tailscale SSH to their own devices (root in check
mode) and their own devices' web UI on 5252.

Members today: `cedi@github` is in all five. Two more people's logins are
in `group:vpn` and `group:synology-users`, one of them also in
`group:hass-users`; see `org.yaml` or the Groups section of Backstage's
Tailscale page for names.

The policy's tests name Users as `user:<name>` (`user:cedi`, `user:moritz`):
renaming a User breaks them.
