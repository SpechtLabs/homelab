# Retire a host

Use this when a machine leaves the fleet for good. Retiring removes it from Buckle; it doesn't
undo what Buckle installed on it.

**Before you start:** SSH to the host, the API or UI, and a checkout of the repo.

1. Skip it in any rollout it's part of, or wait for that rollout to finish
   ([Fix a paused rollout](fix-a-paused-rollout.md) has the skip call).
2. Remove the host from the repo: its `host.id` selectors and vars overlays in `buckle.yaml`,
   `vars/host-<name>.yaml`, and `fixtures/facts/<name>.json`. Find them with
   `git grep -n '<name>'`. `mise run validate`, PR, merge.
3. Stop the agent so it can't register again:

    ```sh
    ssh <user>@<name> "bash -c 'sudo systemctl disable --now buckle-agent'"
    ```

4. Forget it in Buckle: **Forget…** on its host page. That removes its facts, state, runs and
   health history from the server.
5. Remove it from the tailnet (admin console) and from the Backstage catalog
   (`catalog/hardware.yaml`) if it's listed there.

## Check it worked

The host is gone from **Hosts** and from the next rollout's target count (`hosts_total`).

## If it didn't

- It reappears on the Hosts page: its agent is still running and still carries
  `tag:buckle-agent`. Repeat step 3, or remove the tag.
