# How-to guides

When something's wrong:

- [Debug "I can't reach X"](debug-cant-reach-a-service.md): from a failing connection to the missing grant, tag or serve entry.

Access for people and machines:

- [Give a group or tag access to a Service](give-a-group-or-tag-access-to-a-service.md): `tailnet-allow` for people, `consumesApis` + `tailnet-src` for Components.
- [Add or remove a person](add-or-remove-a-person.md): Users and group membership in SpechtLabs/backstage_resources.
- [Add a tsidp relying party](add-a-tsidp-relying-party.md): register the client, give the backend `tag:tsidp-client`, add claims.
- [Retag a device](retag-a-device.md): hosts in the admin console, Kubernetes proxies by re-creating them, and what breaks if you forget.

Shipping a policy change:

- [Check a policy change locally](check-a-policy-change-locally.md): `yarn tailscale:diff` renders the policy from your clones.
- [Review and merge the policy pull request](review-and-merge-the-policy-pull-request.md): Backstage's PR from `backstage/tailnet-policy`.
- [Change a grant annotations can't express](change-a-grant-annotations-cant-express.md): capability grants, exit nodes, break-glass in `grants.yaml`.
- [Add a policy test](add-a-policy-test.md): `tests.yaml` and `ssh-tests.yaml`.

Publishing services:

- [Add a Tailscale Service on a host](add-a-tailscale-service-on-a-host.md): definition, host tag, auto approver, serve every port, move clients.
- [Move a Tailscale Service to another host](move-a-tailscale-service-to-another-host.md): drain, serve on the new host, no client changes.
- [Expose a Kubernetes service on the tailnet](expose-a-kubernetes-service-on-the-tailnet.md): through a cluster's `tailnet-ingress` ProxyGroup.
