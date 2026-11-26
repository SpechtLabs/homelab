# Expose a Kubernetes service on the tailnet

Use this when a workload on specht-labs or labk3s should be reachable on the
tailnet as a Tailscale Service. Both clusters run a `tailnet-ingress`
ProxyGroup (two replicas) that serves such Services; nothing gets its own
standalone proxy device any more.

**Before you start:** push access to SpechtLabs/k8s-deployment, and a
kubeconfig for the cluster (`KUBECONFIG=~/.kube/configs/specht-labs`, or
`KUBECONFIG=~/.kube/configs/labk3s` with `--context labk3s`).

| Cluster | ProxyGroup host tag | Tag for the Service | Examples |
|---|---|---|---|
| specht-labs | `tag:specht-labs-ingress` | `tag:k8s` | `svc:lgtm`, `svc:argocd`, `svc:backstage` in [`apps/envoy-gateway/cluster/specht-labs/tailnet-services.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/envoy-gateway/cluster/specht-labs/tailnet-services.yaml) |
| labk3s | `tag:labk3s-ingress` | `tag:k3s` | `svc:labk3s-argocd-api` in [`apps/argocd/cluster/labk3s/argocd-api-tailnet.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/argocd/cluster/labk3s/argocd-api-tailnet.yaml), `svc:lab-argocd` (an Ingress) |

!!! danger "Never re-create these Services"
    Don't delete or rename a Kubernetes Service or Ingress that carries
    `tailscale.com/proxy-group`, and don't change its `tailscale.com/hostname`
    or `tailscale.com/proxy-group`. The operator deletes the Tailscale Service
    with it, and the re-created one gets a new VIP. DNS records pin the VIPs
    (`*.k8s.specht-labs.de` points at `svc:lgtm`'s 100.102.186.94). An
    Ingress also costs a Let's Encrypt certificate each time, and the limit is
    5 a week per name.

1. Policy first. In SpechtLabs/homelab, add the Service to the cluster's
   auto approver entity in [`tailscale/policy/auto-approvers.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/auto-approvers.yaml)
   (`approve-specht-labs-ingress` or `approve-labk3s-ingress`):

   ```yaml
   services:
     svc:<name>: [tag:specht-labs-ingress]
   ```

   Put `specht-labs.de/tailnet-dst: svc:<name>` and `-ports` on the API
   entity in the app's `catalog-info.yaml` in k8s-deployment, plus
   `tailnet-allow` for the people who use it
   ([Give a group or tag access](give-a-group-or-tag-access-to-a-service.md)).
   Push both, then [merge Backstage's pull request](review-and-merge-the-policy-pull-request.md).
2. Add the Kubernetes Service in k8s-deployment, next to the app:

   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: <app>-tailnet
     annotations:
       tailscale.com/proxy-group: tailnet-ingress
       tailscale.com/hostname: <name>          # becomes svc:<name>
       tailscale.com/tags: tag:k8s             # tag:k3s on labk3s
   spec:
     type: LoadBalancer
     loadBalancerClass: tailscale
     allocateLoadBalancerNodePorts: false
     selector: { ... the app's pod labels ... }
     ports:
       - name: https
         port: 443
         targetPort: 8080
         protocol: TCP
   ```

   One Kubernetes Service per Tailscale Service: the proxies DNAT the VIP to
   one ClusterIP and kube-proxy forwards only the listed ports, so the VIP
   offers just those. `tailscale.com/tags` tags the Tailscale Service, not the
   proxies (they carry the ProxyGroup's tag); it's in no grant. Behind Envoy
   Gateway on specht-labs, target Envoy's container ports, which are the
   listener port plus 10000 for ports below 1024 (80 -> 10080, 443 -> 10443).
3. For a public DNS name, add `external-dns.kubernetes.io/hostname` and
   `external-dns.kubernetes.io/target: "<VIP>"` once the VIP exists, as
   `tailnet-argocd` does. external-dns v0.24 reads only the
   `external-dns.kubernetes.io/` prefix and ignores `.alpha.` silently. It
   runs upsert-only, so a stale record goes by hand in Cloudflare.
4. Push to k8s-deployment's `main` and let Argo CD sync.

## Check it worked

```sh
KUBECONFIG=~/.kube/configs/specht-labs kubectl -n <namespace> get svc <app>-tailnet
dig +short <name>.sphinx-map.ts.net
```

`EXTERNAL-IP` and the DNS answer are the same 100.x VIP. `tailscale ping <name>.sphinx-map.ts.net`
answers from a `specht-labs-ingress-*` (or `labk3s-ingress-*`) device, and
the port connects from a client the policy allows. Add the row to
[Tailscale Services](../reference/services.md).

## If it didn't

- No VIP, or nothing answers: check that the auto approver is in the live
  policy and names the ProxyGroup's tag, that
  `kubectl -n tailscale get proxygroup tailnet-ingress` shows
  `ProxyGroupReady`, and the admin console's Services page for the Service.
  The operator's OAuth client needs General/Services write to create
  Tailscale Services (comment in the ProxyGroup files).
- An egress proxy (`tailscale.com/tailnet-fqdn`, the other direction) with
  the wrong tag: the operator applies tags only when it creates the proxy.
  See [Retag a device](retag-a-device.md).
- Changing an egress `tailscale.com/tailnet-fqdn` in place is safe; it keeps
  the device and its tags.
