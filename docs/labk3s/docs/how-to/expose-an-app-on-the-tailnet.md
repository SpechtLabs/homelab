# Expose an app on the tailnet

Use this when an app on labk3s should be reachable from the tailnet, at `https://<name>.sphinx-map.ts.net`.

**Before you start:** the app is deployed through k8s-deployment ([Deploy or change an app](deploy-or-change-an-app.md)). labk3s has no public ingress; tailnet endpoints are Tailscale Services served by the ProxyGroup `tailnet-ingress` ([`tailnet-ingress.proxygroup.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/tailscale/cluster/labk3s/tailnet-ingress.proxygroup.yaml)): two proxy replicas tagged `tag:labk3s-ingress`, spread across nodes. A Service's VIP belongs to the Tailscale Service, so proxies can come and go without the address changing. Pick the name carefully; you can't rename it later without a new VIP.

There are two shapes, and the labk3s Argo CD uses both:

| Shape | Who terminates TLS | Example |
|---|---|---|
| Ingress, `ingressClassName: tailscale` (L7) | Tailscale, with a Let's Encrypt certificate for the name | `svc:lab-argocd`, the Argo CD UI |
| Service `type: LoadBalancer`, `loadBalancerClass: tailscale` (L3) | The app itself | `svc:labk3s-argocd-api`, Argo CD's API for Backstage |

## 1. Let the ProxyGroup serve the name (homelab repo)

The tailnet policy auto-approves a Service only for the host tag named in its autoApprovers entry. Add your Service to `approve-labk3s-ingress` in [`tailscale/policy/auto-approvers.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/auto-approvers.yaml):

```yaml
  services:
    svc:labk3s-argocd-api: [tag:labk3s-ingress]
    svc:lab-argocd: [tag:labk3s-ingress]
    svc:<name>: [tag:labk3s-ingress]
```

Push it. Backstage renders the policy and opens (or updates) a pull request against this repo from the branch `backstage/tailnet-policy`; the tailscale workflow tests it there. Merge it before the next step. Don't edit `policy.hujson` by hand; the next pull request overwrites it. The [tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) have the full model.

## 2. Say who may reach it (k8s-deployment catalog)

Grants come from the API entity in the app's `catalog-info.yaml`, next to its overlay. Copy `argocd-labk3s-web` in [`apps/argocd/cluster/labk3s/catalog-info.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/argocd/cluster/labk3s/catalog-info.yaml):

```yaml
  annotations:
    specht-labs.de/tailnet-dst: svc:<name>
    specht-labs.de/tailnet-ports: tcp:443
    specht-labs.de/tailnet-allow: group:admins, group:sre
```

A consumer that's another Component gets its grant from its own `specht-labs.de/tailnet-src` tag plus `consumesApis`. Backstage's next policy pull request carries the grant; merge it too.

## 3. Add the Ingress or Service (k8s-deployment)

For an L3 Service, follow [`argocd-api-tailnet.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/argocd/cluster/labk3s/argocd-api-tailnet.yaml):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: <app>-tailnet-svc
  annotations:
    tailscale.com/proxy-group: tailnet-ingress
    tailscale.com/hostname: <name>
    tailscale.com/tags: tag:k3s
spec:
  type: LoadBalancer
  loadBalancerClass: tailscale
  allocateLoadBalancerNodePorts: false
  selector: { ... your pods ... }
  ports:
    - { name: https, port: 443, targetPort: <container port>, protocol: TCP }
```

For an Ingress, use `ingressClassName: tailscale`, the annotation `tailscale.com/proxy-group: tailnet-ingress`, the bare name as `spec.tls[0].hosts[0]`, and no `cert-manager.io/cluster-issuer` annotation (cert-manager would keep requesting a certificate for the bare name, which can never be issued). The `argocd-server` patch in [`apps/argocd/cluster/labk3s/kustomization.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/argocd/cluster/labk3s/kustomization.yaml) is a worked example.

On a ProxyGroup, `tailscale.com/tags` tags the Tailscale Service, not the proxies. `tag:k3s` is the labk3s operator's default and in no grant; access goes by the Service's name. The operator creates the Tailscale Service through the API itself.

## Check it worked

```sh
dig +short <name>.sphinx-map.ts.net
curl -s -o /dev/null -w '%{http_code}\n' https://<name>.sphinx-map.ts.net/
```

A `100.x` address and your app's status code. In the cluster, `kubectl --context labk3s get svc,ingress -A` shows the tailnet name as the external address.

## If it didn't

- **No address:** the policy PR isn't merged yet, or the Service isn't in `approve-labk3s-ingress`. The operator's logs (`deployment/operator` in namespace `tailscale`) say what the API refused.
- **"Required ports are missing"** in the admin console: every replica must serve every port of the Service.

!!! warning "Once it's live"
    Don't delete or rename the Service or Ingress, and don't change `tailscale.com/hostname`, `tailscale.com/proxy-group` or the TLS host: the operator deletes the Tailscale Service with them and the re-created one gets a new VIP. Reusing an existing device's name for a Service costs about 2 minutes of downtime, and Let's Encrypt allows 5 certificates per week for the same name.
