# Deploy or change an app

Use this when you want something new on labk3s, or want to change a value, image or manifest of something already there.

**Before you start:** a checkout of [SpechtLabs/k8s-deployment](https://github.com/SpechtLabs/k8s-deployment) at `~/src/gh/SpechtLabs/k8s-deployment` with its tools (`mise install`). Every Application on labk3s syncs from `main` with `prune: true` and `selfHeal: true`, so a `kubectl edit`, `patch` or `rollout restart` gets reverted within minutes. Change git instead.

## Change an existing app

1. Find its overlay: `apps/<app>/cluster/labk3s/` (shared values in `apps/<app>/base/`). The Application that syncs it is `argo-apps/labk3s/<app>.yaml`.
2. Edit the overlay. Secrets are SOPS files (`*.secret.yaml`); edit them with `sops <file>`, never by decrypting the tree ([`docs/age-secrets.md`](https://github.com/SpechtLabs/k8s-deployment/blob/main/docs/age-secrets.md)).
3. Render it without the age key to catch mistakes:

   ```sh
   cd ~/src/gh/SpechtLabs/k8s-deployment
   KUSTOMIZE_PLUGIN_HOME=$PWD/hack/ksops-stub mise exec -- kustomize build --enable-alpha-plugins --enable-exec --enable-helm apps/<app>/cluster/labk3s
   ```

   You should see the rendered manifests, secrets still encrypted. `mise run check` runs every gate CI runs (lint, kubeconform over each overlay).
4. Commit and push to `main`. The "Bypassed rule violations ... pull request" notice is expected; the owner pushes to `main` directly. Run `git pull --rebase` first and stage only your files: there's often untracked work in progress in that checkout.

## Add a new app

1. Create `apps/<app>/cluster/labk3s/kustomization.yaml` (copy the shape of a neighbour such as [`apps/coredns/cluster/labk3s`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/coredns/cluster/labk3s) for plain manifests, or [`apps/ceph-csi-rbd/cluster/labk3s`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/ceph-csi-rbd/cluster/labk3s) for a Helm chart).
2. Add `argo-apps/labk3s/<app>.yaml`, an Application in namespace `argocd` with `source.path: apps/<app>/cluster/labk3s`, `targetRevision: main` and the same `syncPolicy` as the others ([`ceph-csi-rbd.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/argo-apps/labk3s/ceph-csi-rbd.yaml) is a good template). The root `1-meta-labk3s` picks up every file in that directory.
3. Add a `catalog-info.yaml` next to the overlay (`system: labk3s`, `dependsOn: [resource:labk3s]`, name with a `-labk3s` suffix) so it shows up in Backstage; see any neighbour.
4. Render, commit and push as above.

For persistent volumes, set `storageClassName: ceph-rbd`. The cluster's default class is still `local-path`, which pins the data to one node's disk.

## Check it worked

```sh
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s -n argocd get applications
```

Run it from outside the k8s-deployment checkout ([why](get-kubectl-access.md#the-kubeconfig-trap)). Your app should reach `Synced` and `Healthy` within a few minutes. The Argo CD UI at <https://lab-argocd.sphinx-map.ts.net> shows the diff and sync errors.

## If it didn't

- `OutOfSync` that never settles: a controller rewrites a field Argo CD owns. The existing apps solve this with `ignoreDifferences` (the Tailscale egress Services' `/spec/externalName`, for example).
- Sync fails on a CRD that doesn't exist yet: add `SkipDryRunOnMissingResource=true` to `syncOptions`, as `grafana-k8s-monitoring` does.
- Roll back with `git revert` and push. Argo CD follows `main`.
