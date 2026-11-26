# Add or remove a person

Use this when someone should join or leave a tailnet group (`group:vpn`,
`group:synology-users`, `group:hass-users`, `group:sre`, `group:admins`), or
leave the policy altogether.

**Before you start:** write access to the private
[SpechtLabs/backstage_resources](https://github.com/SpechtLabs/backstage_resources).
People and groups live only in its `catalog/org.yaml`; Backstage renders the
policy's `groups` from it. Nobody's added to a group in the admin console or
in `policy.hujson`.

1. Find the person's Tailscale login. On a device of theirs, or on any host
   they connect to, `tailscale whois <their-tailnet-ip>` prints it under
   `User: Name:` (for example `cedi@github`).
2. Edit [`catalog/org.yaml`](https://github.com/SpechtLabs/backstage_resources/blob/main/catalog/org.yaml).
   A new person is a User with their login and their groups:

   ```yaml
   apiVersion: backstage.io/v1alpha1
   kind: User
   metadata:
     name: <backstage-name>
     annotations:
       specht-labs.de/tailnet-login: <login>
   spec:
     profile:
       displayName: <name>
     memberOf: [tailnet-vpn, tailnet-synology-users]
   ```

   The Group names are `tailnet-admins`, `tailnet-sre`, `tailnet-vpn`,
   `tailnet-synology-users` and `tailnet-hass-users` ([Groups](../reference/groups.md)).
   To change membership, edit `memberOf`. To take someone out of the policy,
   drop the groups from `memberOf` or delete the User.
3. Leave `spec.profile.email` out unless they should sign in to Backstage:
   Backstage maps the tsidp token's `email` claim to it, and tailnet
   membership alone doesn't grant Backstage access.
4. Removing or renaming a User? Policy tests name some Users as
   `user:<name>`:

   ```sh
   cd ~/src/gh/cedi/homelab && git grep -n 'user:' tailscale/policy/
   ```

   Change those tests in the same go, or the rendered policy has an error
   ("is not a User in the catalog").
5. Commit and push to backstage_resources. The catalog picks it up within a
   few minutes; Backstage's hourly run then updates the pull request from
   `backstage/tailnet-policy` in SpechtLabs/homelab.
6. [Review and merge the pull request](review-and-merge-the-policy-pull-request.md).
   The diff should touch only the `groups` section (and tests you changed).

## Check it worked

```sh
cd ~/src/gh/cedi/homelab && git pull && grep -n -A30 '"groups"' tailscale/policy.hujson
```

The login appears under exactly the groups you meant. In Backstage the
User's page shows their tailnet access; **Tailscale > Preview access**
"from" their login lists what they now reach.

## If it didn't

- A member without `specht-labs.de/tailnet-login` is an error in the PR body
  ("is in group:... but has no specht-labs.de/tailnet-login annotation").
- Roll back by reverting the commit in backstage_resources; the next run
  updates the pull request.

!!! warning "Unverified"
    How a new person joins the tailnet itself (an invitation in the admin
    console), and how a departed person's devices are removed, isn't written
    down in any of the repos. The steps above only change what the policy
    lets a login reach.
