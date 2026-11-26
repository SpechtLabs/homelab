# Buckle and Argo CD

Two GitOps tools touch labk3s, and the split between them is strict: Buckle owns the machines and exactly one Kubernetes object; Argo CD owns everything else in the cluster, itself included. If both managed the same object, each would keep reverting the other.

## Why Buckle owns the root Application

Argo CD can't create its own root on a fresh cluster: there's no Argo CD yet to sync it. k8s-deployment's [first-deployment guide](https://github.com/SpechtLabs/k8s-deployment/blob/main/docs/first-deployment.md) solves that by hand (install CRDs, `kustomize build | kubectl apply`, apply the meta app). For labk3s, Buckle does those steps:

1. `k3s-server` and `k3s-agent` bring up the cluster.
2. `argocd-seed` renders `apps/argocd/cluster/labk3s` with kustomize, helm and ksops, decrypts its SOPS secrets with `ARGOCD_AGE_KEY`, and applies the result server-side. Rendered secrets go straight into the API, never to disk.
3. The workload `argocd-root` applies `1-meta-labk3s`, which points at `argo-apps/labk3s`.

From then on Argo CD's own `argocd` Application manages Argo CD. That's why `argo-apps/labk3s/` doesn't contain the meta app, unlike the specht-labs cluster.

On fresh Pis this is the whole bootstrap: enrol them, and one rollout installs k3s, seeds Argo CD and creates the root app. The only secret involved besides the k3s token is the age key on the Buckle server.

## Why the seed is so careful

The seed applies a checkout of k8s-deployment frozen at its first clone (`update: false`), with `--force-conflicts`. Run against a live Argo CD, it would roll Argo CD back to that old revision. So it runs only when the API answers, within 30 s, that `argocd/argocd-server` doesn't exist. A timeout, a k3s restart or any other failed query counts as "leave it alone". The trade-off: if Argo CD is half-installed (namespace there, Deployment gone), the seed runs again, which is what you want; if the API is down, it never runs, which is also what you want.

## Why the root survives everything

`1-meta-labk3s` has `argocd.argoproj.io/sync-options: Prune=false`, so Argo CD never prunes it, even if k8s-deployment still listed it somewhere. The workload has `removal: keep`, so taking `argocd-root` out of Buckle leaves the Application in place. Deleting the root would cascade into every app on the cluster.

## Self-heal and live edits

Every Application has `selfHeal: true`. A `kubectl edit`, `patch`, `scale` or `rollout restart` is drift, and Argo CD reverts it within minutes. That's deliberate: the cluster's state is what's in `main`, and a fix that exists only in the cluster disappears on the next sync. Deleting a pod is fine (it's not part of the desired state); changing a Deployment isn't.

## Buckle's own view of the cluster

Buckle treats labk3s as a target of kind `kubernetes`, executed by the server with its own admin kubeconfig. It uses that for two things: applying `argocd-root`, and cordoning and draining nodes around disruptive runs (`maintenance`). It doesn't deploy apps, and it doesn't look at Argo CD's health beyond the non-required `argocd-server` check.
