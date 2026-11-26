# Review and merge the policy pull request

Use this when Backstage has opened or updated its pull request against
SpechtLabs/homelab from the branch `backstage/tailnet-policy`, usually within
the hour after a catalog change.

**Before you start:** merging applies the policy to the whole tailnet within
a minute. A grant you remove stops traffic right away.

1. Find the pull request.

   ```sh
   gh pr list --repo SpechtLabs/homelab --head backstage/tailnet-policy
   ```

   Its title reads like `feat(tailscale): render sphinx-map.ts.net (28 grants, 7 SSH rules, 21 tests)`.
2. Read the body.

   ```sh
   gh pr view <number> --repo SpechtLabs/homelab
   ```

   It counts the entries per section and, if there are any, lists
   **Problems**: errors and warnings with links to the entities. Backstage
   publishes even with errors, so an error here is yours to fix in the
   catalog before merging.
3. Read the diff.

   ```sh
   gh pr diff <number> --repo SpechtLabs/homelab
   ```

   Only `tailscale/policy.hujson` changes. Each rule carries the title of
   the entity it comes from; catalog grants say `From the catalog: <api>`
   and which Components consume it. Check that every change is one you (or
   the commit you're shipping) meant. A grant you didn't expect usually
   means a new `consumesApis` somewhere: see the explanation of
   [how the catalog becomes the policy](../explanation/how-the-catalog-becomes-the-policy.md).
4. Wait for the test.

   ```sh
   gh pr checks <number> --repo SpechtLabs/homelab
   ```

   The `tailscale policy` workflow's "Test policy" step sends the file to
   Tailscale, which parses it and runs its `tests` and `sshTests`. Don't merge
   a red run: the apply would fail the same way.
5. Merge it.

   ```sh
   gh pr merge <number> --repo SpechtLabs/homelab --squash
   ```

6. Watch the apply.

   ```sh
   gh run list --repo SpechtLabs/homelab --workflow tailscale.yaml --limit 2
   ```

   The newest run (event `push`, branch `main`) should be `success`. If
   Tailscale rejects the policy, the previous one stays live.

## Check it worked

The admin console's [Access controls](https://login.tailscale.com/admin/acls/file)
show the new file. For the change you made, run the check from its how-to
(Preview access in Backstage, or a connection from a client). On Backstage's
next hourly run the policy on `main` equals the rendered one and no new pull
request opens.

## If it didn't

- Don't push to `backstage/tailnet-policy` or edit the pull request:
  Backstage force-pushes the branch to one commit on top of `main` whenever
  the rendered file changes.
- A conflict on `policy.hujson` means someone changed the file on `main` by
  hand. Revert that commit; the next run sees the difference and the pull
  request becomes mergeable.
- To undo a merged change, revert the catalog change that caused it (not
  the merge commit) and merge the next pull request. Reverting the merge
  commit works as an emergency stop, but Backstage opens a pull request that
  re-applies the change until the catalog says otherwise.
- The test fails: open the run's log (`gh run view <run-id> --repo SpechtLabs/homelab --log-failed`)
  for the failing test, then [check the change locally](check-a-policy-change-locally.md).
