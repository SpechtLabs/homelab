# How the catalog becomes the policy

`policy.hujson` used to be a hand-written file, applied by the workflow since
2026-11-17. On 2026-11-26 its content moved into Backstage's catalog, and the
file became output. The reason is the catalog already knew most of it: which
Component consumes which API, which host runs what, who's in which group.
Writing the same facts again as grants meant two places to keep in step.

What follows is what Backstage's tailnet plugin
([`compile.ts`](https://github.com/SpechtLabs/backstage-plugin-tailscale/blob/main/plugins/tailscale-backend/src/compile.ts),
[`graph.ts`](https://github.com/SpechtLabs/backstage-plugin-tailscale/blob/main/plugins/tailscale-backend/src/graph.ts))
does with it.

## The inputs

The plugin reads five kinds of entity:

- `kind: Tailscale` entities from `tailscale/policy/*.yaml`, the only
  location allowed to define that kind. One is the policy (`type: policy`,
  `tailscale:sphinx-map`); every other names it in `spec.target` and is one
  tag, grant, SSH rule, node attribute, auto approver set or test bundle.
- Users and Groups from SpechtLabs/backstage_resources. A Group with
  `specht-labs.de/tailnet-group` becomes a policy group; its members' logins
  come from `specht-labs.de/tailnet-login`.
- APIs and Components with the tailnet annotations, from both catalog repos.
- Resources of type `kubernetes-cluster`, to tell which Components share a
  cluster.

## From annotations to grants

The policy entity has `catalogGrants: true`, which turns this on.

For every API with `tailnet-dst`, the plugin reads the destination and ports.
Each entry in its `tailnet-allow` becomes a flow straight away: those are
people, or devices without a Component of their own.

Then for every Component that consumes such an API, it asks whether the
traffic crosses the tailnet at all. If the consumer and every provider
`dependsOn` the same `kubernetes-cluster` Resource, it's pod-network traffic
and renders nothing. Otherwise the flow's source is the API's
`tailnet-client-tag` if it has one, else the consumer's `tailnet-src`. A
consumer without either is listed as "missing source" and gets no grant.

`tailnet-client-tag` exists because `tailnet-src` belongs to a Component, not
to one of the APIs it consumes. isa is `tag:buckle-server` when the Buckle
server backs up to `svc:nfs`, but `tag:tsidp-client` when it signs people in
through tsidp. Using tsidp makes a device a relying party, so the tag goes
on the API.

Next the plugin drops flows a hand-written grant in `grants.yaml` already
allows by name. A flow only the admins' `*` grant allows keeps its own
grant, so nothing depends on break-glass. The rest are merged twice: flows to
the same destination and ports share one grant with all their sources, and
grants with the same sources and destination then share one grant with all
their ports. Each ends up with a comment naming its APIs and consumers
("From the catalog: nut / Consumed by nut-client").

## Checks

Some mistakes are errors: a tag no tag entity declares, a `group:` no Group
carries, a `user:` that isn't a User or has no login. Others are warnings: a
capability grant or a grant to a Service on every port (name the port), and
a device destination that's neither a peer mesh nor a capability target nor
explained by `specht-labs.de/tailnet-device-reason` on its tag. Both kinds
appear in the pull request's "Problems" section and on the Tailscale page.
None of them stops publishing, so reading that section before merging is the
safeguard. Malformed annotations and missing sources don't appear there;
they're only in the plugin's `/api/tailscale/overview` output (and
`yarn tailscale:diff --json`).

## Publishing

Once an hour the plugin renders the file and compares it with `main`. If
they differ, it builds one commit on top of `main` with the new file and
points `backstage/tailnet-policy` at it in a single ref update (resetting the
branch first would leave the pull request empty for a moment, and GitHub
closes such a pull request for good). It then opens or updates the pull
request. When `main` already has the rendered file, it closes any open pull
request. `spec.publish.flow: push` would commit straight to `main` instead;
the homelab uses `pullRequest` so a person reads every change and the
workflow tests it against the real tailnet first. Backstage may write only
to repositories listed in `tailscale.allowedRepos` in its app config.

From there it's the workflow: `test` on the pull request, `apply` on the
merge. Tailscale runs the policy's tests on every save and refuses a policy
that fails one, so the previous policy stays live.

## What's still hand-written

Capability grants (`app` blocks), the break-glass and exit node grants, SSH
rules, node attributes, tags, auto approvers and tests are entities rather
than annotations, because their values don't fit an annotation or they're
about the tailnet rather than a service. The Service definitions (name and
ports) live only in the admin console.
