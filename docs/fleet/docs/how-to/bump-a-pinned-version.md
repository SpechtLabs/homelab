# Bump a pinned version

Use this when software the fleet runs needs a newer (or older) version: k3s, Alloy, rpi_exporter,
tsidp, compute-blade-agent, the dotfiles commit, the Argo CD seed's tools, Ceph. Every pin lives in
[`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml), and
a merged bump is a fleet rollout like any other commit.

Most of the time Renovate does this for you: a line with a `# renovate:` comment above it is
watched, and Renovate opens the PR and merges it itself once CI is green. Its rules are in
[CI and Renovate](../reference/ci-and-renovate.md#renovate). Do it by hand when you can't wait,
need to go back, or the pin isn't Renovate-managed.

1. Edit the value in `vars/versions.yaml`. Keep the `# renovate:` comment line directly above it;
   Renovate's regex needs the two lines together.
    - `k3s_version`: one minor at a time. CI's `k3s-one-minor` job fails a PR that moves more.
    - `ceph_version`: bump `ceph_cephadm_sha256` with it (cephadm has no published checksum; take
      the sha256 of `download.ceph.com/rpm-<version>/el9/noarch/cephadm`). This only sets what
      cephadm bootstraps with: a running cluster upgrades through `ceph orch upgrade`, see the
      [ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/).
    - `compute_blade_agent_version`: bump `"github:compute-blade-community/compute-blade-agent"`
      in `mise.toml` too (that's `bladectl` on your Mac).
    - `argocd_seed_*`: keep them in step with SpechtLabs/k8s-deployment's `.mise.toml`.
    - `buckle_version`: see [Upgrade Buckle](upgrade-buckle.md).
    - Jitsi's packages are pinned in `vars/host-meet.yaml`, with an upgrade procedure of their own
      ([jitsi docs](https://backstage.k8s.specht-labs.de/docs/default/system/jitsi/)).
2. Validate and open a PR:

    ```sh
    mise run validate
    git commit -am "chore(deps): k3s <new version>"
    gh pr create --fill && gh pr checks --watch
    ```

3. Merge and [watch the rollout](watch-a-rollout.md). How the bump travels depends on the module:
    - k3s: the server first (`k3s-agent` needs `group:k3s-server`), then one worker at a time
      (`parallel: 1`), each node drained before k3s restarts and uncordoned once its kubelet is
      healthy.
    - Alloy, rpi_exporter, tsidp: per phase, gated on their checks (`alloy/ready`,
      `rpi-exporter/metrics`, `tsidp/discovery`).
    - dotfiles: a new commit re-runs the installer on every host's admin account.

## Check it worked

On a host that runs it:

```sh
ssh pi@clusterpi-worker1 "bash -c 'k3s --version | head -1'"
ssh pi@blade-pi1 "bash -c 'alloy --version | head -1'"
```

shows the new version, and the rollout ended `completed`.

## If it didn't

- The rollout paused on a check: [Fix a paused rollout](fix-a-paused-rollout.md). Going back is a
  revert of the bump, through the same phases.
- Many hosts fetching from GitHub at once (`k3s` uses `github.release`, Buckle uses
  `buckle update`) can hit the anonymous API limit of 60 calls an hour shared by every host at
  home. The phases spread it out; a failed fetch retries on **Retry**.
