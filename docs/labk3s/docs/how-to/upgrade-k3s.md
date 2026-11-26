# Upgrade k3s

Use this when a new k3s release is out, or when Renovate opened a `k3s-io/k3s` PR against this repo.

**Before you start:** the version lives in one place, `k3s_version` in [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml). Both `k3s-server` and `k3s-agent` install `/usr/local/bin/k3s` from that GitHub release, so a bump is the whole upgrade. Expect each node's k3s to restart once.

## What Renovate does on its own

The rules in [`renovate.json`](https://github.com/SpechtLabs/homelab/blob/main/renovate.json):

| Update | What happens |
|---|---|
| Patch or `+k3sN` rebuild | Automerges once the release is 3 days old |
| Minor | Automerges, but only before 6am on Mondays, one minor per PR |
| Major | Automerges once the release is 7 days old |

The CI job `k3s-one-minor` in [`validate.yml`](https://github.com/SpechtLabs/homelab/blob/main/.github/workflows/validate.yml) fails any PR that moves `k3s_version` more than one minor from `main`. Kubernetes can't skip a minor; the next minor's PR passes once Renovate rebases it after the previous merge. A merge on `main` starts a Buckle rollout, so the Monday schedule gives each minor a week to settle.

## Upgrade by hand

1. Before a minor, check that the apps in k8s-deployment don't use APIs the new Kubernetes minor removes (the k3s release notes link the upstream changelog). Nothing here checks this for you.
2. Change `k3s_version` in `vars/versions.yaml`, for example `v1.37.2+k3s1` to the next release. Keep the `v` and the `+k3sN` suffix.
3. Validate:

   ```sh
   cd ~/src/gh/cedi/homelab
   mise run validate
   ```

4. Open a PR (CI dry-plans every host) or push to `main`. The merge starts the rollout.

## What the rollout does

The k3s nodes are in the `fleet` phase. `k3s-agent` `needs: group:k3s-server`, so `clusterpi-leader` goes first. Then the workers follow one at a time (`k3s-agent` has `parallel: 1`). Before each node's run, labk3s cordons and drains it (`maintenance: { drain: disruptive, deadline: 10m }`, both modules are `disrupts: node`), and uncordons it once the host's health checks pass. Details: [Buckle settings](../reference/buckle-settings.md).

## Check it worked

```sh
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s get nodes
```

All five nodes `Ready`, none `SchedulingDisabled`, and the `VERSION` column shows the new version. In the Buckle UI the rollout ends `completed`.

## If it didn't

- **The rollout paused** (`on_failure: pause`): the failed host's page shows which check failed. `unit`, `kubelet` and `apiserver` are required on the server; `unit` and `kubelet` on the agents.
- **A node stays cordoned:** a host that fails after its apply keeps its node drained until a retry is healthy. Uncordon by hand with `kubectl --context labk3s uncordon <node>` once you've fixed it.
- **Roll back:** revert the bump. Going back a minor isn't something Kubernetes supports; for a patch it's the same rollout in reverse.
- **`github.release` failed with a rate limit:** each plan that isn't on the pinned version costs one anonymous GitHub API call, 60 per hour shared by the whole home IP. Wait an hour and retry the host.
