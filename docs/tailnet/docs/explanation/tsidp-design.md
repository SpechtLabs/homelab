# tsidp's design

tsidp is the tailnet's OpenID Connect provider. Identity is the Tailscale
login: whoever's device makes the request is who signs in, with no password
anywhere. Buckle, DSM, both Argo CDs (through Dex), Backstage and Grafana
use it.

## Its own node

tsidp runs on isa but joins the tailnet as its own node, `idp`, with its own
state in `/data` (which still holds the node key from the Ansible days;
[`modules/tsidp`](https://github.com/SpechtLabs/homelab/blob/main/modules/tsidp/module.yaml)
never removes it). It advertises `tag:tsidp` itself and listens on tcp:443.

The name matters more than usual. The issuer is
`https://idp.sphinx-map.ts.net`, and every `email` claim is the login with
that host appended (`cedi@github.idp.sphinx-map.ts.net`). Relying parties
check the issuer, and Backstage's sign-in matches the `email` claim to a
User's `profile.email` exactly. Renaming or re-creating the device would
change both at once, so `idp` stays as it is.

## Funnel

The specht-labs cluster runs at Hetzner, off the tailnet, and its Argo CD,
Backstage and Grafana still sign people in through tsidp. Funnel makes `idp`
reachable from the internet for them (`-funnel`, and the node attribute
`attr-tsidp-funnel`). Those requests never touch the policy. Relying parties
on the tailnet (isa for Buckle, the NAS for DSM, labk3s's Argo CD through
`k3s-idp-egress`) reach it directly and need `tag:tsidp-client`.

## Why it's a device and not a Service

Funnel doesn't work on Tailscale Services, and tsidp can't serve one. tsidp
also reads its capability grants (`tailscale.com/cap/tsidp`) from the
connection to its own address. So `tag:tsidp` is a destination, reachable by
`autogroup:member` and `tag:tsidp-client` on tcp:443 and nothing else. The
four capability grants are all tcp:443 too; they add claims and admin rights,
not reach.

## Authorization lives in the policy

tsidp puts extra claims into tokens from capability grants. `group:admins`
get `groups: ["buckle-admins"]`, which Buckle's `user_acl` and `admin_acl`
check, and `groups: ["grafana-admins"]`, which Grafana maps to its Admin
role. tsidp unions list claims across grants, so an admin's token carries
both. Who administers the fleet is therefore decided by `group:admins` in
backstage_resources, not in Buckle's config. If tsidp is down, Buckle has a
break-glass path (`bootstrap/README.md`, "Sign-in and break-glass").

Admins also get `allow_admin_ui` and `allow_dcr`: the admin UI at the root
URL, where clients and their redirect URIs are registered, and dynamic
registration at `/register`.

## Running it

[`modules/tsidp`](https://github.com/SpechtLabs/homelab/blob/main/modules/tsidp/module.yaml)
installs the release binary (version `tsidp_version` in
[`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml),
bumped by Renovate) and runs it as `tsidp.service` with `-funnel` and
`-enable-sts`, and `TAILSCALE_USE_WIP_CODE=1` in `/etc/default/tsidp`. Its
health checks are the unit and the discovery document. The o11y collector
probes the same discovery URL for tsidp's availability SLO; isa carries
`tag:tsidp-client`, so the probe needs no grant of its own.

One failure mode to know: Dex (both Argo CDs) gave up for good when it
couldn't reach idp at startup and stopped serving without crashing. Since
k8s-deployment `abc2dc6c` it has probes on `/healthz/live`, so kubelet
restarts it.
