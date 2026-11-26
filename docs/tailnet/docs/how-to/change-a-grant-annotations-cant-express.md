# Change a grant annotations can't express

Use this for a grant that no API annotation can say: one that carries
application capabilities (`app`, as tsidp's claims, TKA's role or the web UI's
`canEdit`), exit node access, the admins' break-glass grant, or a destination
that isn't a Service or tag. These live as entities in
[`tailscale/policy/grants.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/grants.yaml).
SSH rules and node attributes work the same way, in `ssh.yaml` and
`node-attrs.yaml`.

**Before you start:** check annotations really can't do it. Ports and who
may reach an API belong on the API ([Give a group or tag access](give-a-group-or-tag-access-to-a-service.md));
a grant here for the same flow makes the catalog grant disappear, and the
two then drift apart.

1. Add or edit an entity in `grants.yaml`. One grant per entity:

   ```yaml
   apiVersion: specht-labs.de/v1alpha1
   kind: Tailscale
   metadata:
     name: grant-tsidp-grafana-admins
     title: Admins are Grafana admins
     description: >-
       group:admins get groups ["grafana-admins"] in their tsidp tokens.
   spec:
     type: grant
     target: tailscale:sphinx-map
     owner: group:spechtlabs
     system: tailnet
     appliesTo: [component:tsidp]
     src: [group:admins]
     dst: [tag:tsidp]
     ip: ['tcp:443']
     app:
       tailscale.com/cap/tsidp:
         - extraClaims:
             groups: [grafana-admins]
           includeInUserInfo: true
   ```

   `title` and `description` become the comment above the grant in
   `policy.hujson`. `appliesTo` puts the grant on those entities' pages in
   Backstage. Name a real port in `ip`: a capability grant on `*` gets a
   warning ("name the port the app listens on"), and so does a grant to a
   Service on every port.
2. Sources can be `group:` (a Backstage Group's tailnet name), `user:<backstage-name>`,
   `tag:` (declared in `tags.yaml`), `autogroup:` or `*`. An undeclared tag
   or unknown group is an error.
3. A grant to a tag that's neither a peer mesh nor a capability target gets
   a warning ("reached as a device, not a Service"). Move the traffic to a
   Service, or say why on the tag entity with the annotation
   `specht-labs.de/tailnet-device-reason`.
4. [Check it locally](check-a-policy-change-locally.md): your grant shows up
   as a `+` line under `grants:`. Add a test if the grant protects or opens
   something that matters ([Add a policy test](add-a-policy-test.md)).
5. Push, then [merge Backstage's pull request](review-and-merge-the-policy-pull-request.md).

## Check it worked

In Backstage, the grant's own entity page shows the rule and the lines it
renders to. For capability grants, check the app: a fresh tsidp token carries
the claim, TKA hands out the role, the web UI lets you edit.

## If it didn't

- tsidp unions list claims across grants: two grants that give
  `group:admins` `groups` claims produce one token with both lists
  (`["buckle-admins", "grafana-admins"]` today). Remove a claim from every
  grant that adds it.
- Revert the entity change and merge the next pull request.
