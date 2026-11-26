# How-to guides

- [Get kubectl access](get-kubectl-access.md): the admin kubeconfig or a TKA session, and the `KUBECONFIG` trap inside k8s-deployment.
- [Deploy or change an app](deploy-or-change-an-app.md): through k8s-deployment, because Argo CD reverts live edits.
- [Reach the labk3s Argo CD](reach-the-labk3s-argo-cd.md): the UI at `lab-argocd` and the API Backstage uses.
- [Respond to a labk3s alert](respond-to-a-labk3s-alert.md): the API availability SLO and the Ceph CSI rules.
- [Upgrade k3s](upgrade-k3s.md): merge the renovate bump; server first, then one drained worker at a time.
- [Drain and reboot a node](drain-and-reboot-a-node.md): by hand, or let a Buckle rollout do it.
- [Restart pods after the nodes change address](restart-pods-after-the-nodes-change-address.md): the ceph-csi node plugin keeps listening on the old IP.
- [Expose an app on the tailnet](expose-an-app-on-the-tailnet.md): a Tailscale Service on the `tailnet-ingress` ProxyGroup.
- [Add a worker](add-a-worker.md): a new `clusterpi-worker*` Pi.
- [Replace or re-create the server](replace-or-re-create-the-server.md): what the repo covers and what it doesn't.
- [Reset k3s](reset-k3s.md): by hand, deliberately not a Buckle removal hook.
