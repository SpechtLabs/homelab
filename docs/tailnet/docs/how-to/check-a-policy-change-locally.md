# Check a policy change locally

Use this before pushing a catalog change that touches the tailnet (an
annotation, a `tailscale/policy/*.yaml` entity, a group membership), to see
what Backstage will render without waiting an hour for its pull request.

**Before you start:** clones of SpechtLabs/homelab, SpechtLabs/k8s-deployment,
SpechtLabs/backstage and SpechtLabs/backstage_resources under `~/src/gh/`,
with `yarn install` done in the backstage clone (its `mise.toml` pins node
and yarn). The tool reads your working copies, uncommitted edits included.

1. Update the clones you didn't change, so you compare against what
   Backstage sees:

   ```sh
   for r in cedi/homelab SpechtLabs/k8s-deployment SpechtLabs/backstage_resources; do git -C ~/src/gh/$r pull --ff-only; done
   ```

   (Skip the repo you're editing if `pull` would get in the way.)
2. Save the policy that's live on `main`:

   ```sh
   git -C ~/src/gh/cedi/homelab show origin/main:tailscale/policy.hujson > /tmp/policy-main.hujson
   ```

3. Render and compare:

   ```sh
   cd ~/src/gh/SpechtLabs/backstage
   yarn tailscale:diff --out /tmp/policy-rendered.hujson /tmp/policy-main.hujson \
     ~/src/gh/cedi/homelab ~/src/gh/SpechtLabs/k8s-deployment ~/src/gh/SpechtLabs/backstage_resources
   ```

   You'll see a summary (`Homelab tailnet: 229 entities, 63 parts, 661 lines`),
   the destinations by class, any `error:` or `warning:` lines, and then every
   difference per section:

   ```text
   grants:
     - group:admins -> tag:tka * app {...}   (only in policy-main.hujson)
     + group:admins -> tag:tka tcp:8123 app {...}   (only rendered)
   ```

   `-` lines are what your change takes away, `+` lines what it adds. The
   comparison is by meaning (who reaches what), so reordering or new comments
   don't count. With no change it ends with
   `No differences: the rendered policy allows what policy-main.hujson allows.`
4. Read `/tmp/policy-rendered.hujson` if you want the file exactly as the
   pull request will carry it.

## Check it worked

The differences are exactly the ones you meant and there's no `error:` line.
The command exits 0 with no differences and no errors, 1 otherwise, 2 on bad
arguments.

## If it didn't

- A consumer that should get a grant doesn't: add `--json /tmp/overview.json`
  and look at `jq '.policies[0].catalog | {invalid, missingSource, local}' /tmp/overview.json`.
  `invalid` lists malformed annotations, `missingSource` consumers without
  `specht-labs.de/tailnet-src`, `local` consumption inside one cluster (no
  grant needed).
- The local render can't run Tailscale's own tests; those run on the pull
  request ([Review and merge it](review-and-merge-the-policy-pull-request.md)).
