# Reach the labk3s Argo CD

Use this when you want to see sync status, diffs or logs of the apps on labk3s, or when Backstage's Argo CD cards for labk3s are empty.

**Before you start:** you're on the tailnet as a member of `group:admins` or `group:sre`. Both get the UI; only admins get write access.

## The UI

1. Open <https://lab-argocd.sphinx-map.ts.net>.
2. Click **Log in via Tailscale**. Dex sends you to tsidp (`idp.sphinx-map.ts.net`), which signs you in by your tailnet identity.
   You should land on the Applications list with `1-meta-labk3s` and its children.

Who gets what comes from the RBAC patch in [`apps/argocd/cluster/labk3s/kustomization.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/argocd/cluster/labk3s/kustomization.yaml): `cedi` (in its three spellings) is `role:org-admin`, everyone else falls back to `policy.default: role:readonly` from the base values. The UI's web terminal works because the `argocd-server` Role gets `pods/exec`.

The UI is the Tailscale Service `svc:lab-argocd`, served by the Ingress `argocd-server` (class `tailscale`) on the `tailnet-ingress` ProxyGroup. Tailscale terminates TLS with a Let's Encrypt certificate for `lab-argocd.sphinx-map.ts.net`.

## The API (what Backstage uses)

Backstage on specht-labs reads the labk3s Argo CD through `svc:labk3s-argocd-api` (`https://labk3s-argocd-api.sphinx-map.ts.net`, tcp:443), the LoadBalancer Service `argocd-server-tailnet-svc` on the same ProxyGroup. Here `argocd-server` terminates TLS itself with a self-signed certificate, so Backstage's `/argocd/labk3s` proxy runs with `secure: false`. The path: Backstage's egress proxy `backstage-lab-argocd` (`tag:backstage`) on specht-labs, then the Service, using the read-only `backstage` account's token (`ARGOCD_LABK3S_TOKEN`, k8s-deployment `apps/backstage/cluster/specht-labs/argocd.secret.yaml`).

Only `tag:backstage` has a grant to `svc:labk3s-argocd-api`. Admins reach it too, through their `*` grant.

## Check it worked

```sh
curl -s -o /dev/null -w '%{http_code}\n' https://lab-argocd.sphinx-map.ts.net/
```

You should see `200`.

## If it didn't

- **Name doesn't resolve or times out:** check the ProxyGroup with `kubectl --context labk3s get proxygroup` (should be `ProxyGroupReady`) and its pods in namespace `tailscale` (`tailnet-ingress-0`, `-1`).
- **Login loops or "failed to get token":** Dex can't reach tsidp. labk3s reaches `idp` through the egress Service `k3s-idp-egress` (namespace `tailscale`, `tag:tsidp-client`). Dex used to give up for good when tsidp was down at its start; it now has startup and liveness probes on `/healthz/live`, so kubelet restarts it. If it's still stuck, delete the Dex pod in `argocd` (a pod delete isn't drift; Argo CD doesn't revert it).
- **Port-forward as a last resort:** `kubectl --context labk3s -n argocd port-forward service/argocd-server 8080:443`, then <https://localhost:8080> (self-signed). The `admin` user's first password is in the Secret `argocd-initial-admin-secret`, which still exists on labk3s.

!!! warning "Don't re-create these"
    Never delete, rename or move the Ingress `argocd-server` or the Service `argocd-server-tailnet-svc` to another ProxyGroup, and don't change their `tailscale.com/hostname` or TLS host. The operator deletes the Tailscale Service with them and a new one gets a new VIP. Re-creating `lab-argocd` also costs a Let's Encrypt certificate: the limit is 5 per week for the same name, and it used 2 on 2026-11-25/26.
