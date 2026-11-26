# Tailnet policy

`policy.hujson` is generated: Backstage renders it from the catalog (`policy/` here and the
services' `specht-labs.de/tailnet-*` annotations) and keeps a pull request open from the
branch `backstage/tailnet-policy`. Change the catalog, not this file; merging the pull request
applies the policy (`.github/workflows/tailscale.yaml`).

Everything else is in the tailnet docs ([Backstage](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/), [source](../docs/tailnet/docs/index.md)):

- [The model: attributes to Services](../docs/tailnet/docs/explanation/abac-model.md)
- [How the catalog becomes the policy](../docs/tailnet/docs/explanation/how-the-catalog-becomes-the-policy.md)
- [Review and merge the policy pull request](../docs/tailnet/docs/how-to/review-and-merge-the-policy-pull-request.md)
- [Add a Tailscale Service on a host](../docs/tailnet/docs/how-to/add-a-tailscale-service-on-a-host.md)
- [Why some destinations stay devices](../docs/tailnet/docs/explanation/why-some-destinations-stay-devices.md)
