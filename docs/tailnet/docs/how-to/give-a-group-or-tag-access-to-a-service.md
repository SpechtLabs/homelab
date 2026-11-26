# Give a group or tag access to a Service

Use this when people (a group) or machines (a tag, a Component) need to reach
an API on the tailnet that they can't reach today.

**Before you start:** find the API entity. Every API reachable over the
tailnet has `specht-labs.de/tailnet-dst` and `specht-labs.de/tailnet-ports`
annotations; they live in `catalog-info.yaml` files in SpechtLabs/homelab and
SpechtLabs/k8s-deployment:

```sh
cd ~/src/gh/cedi/homelab && git grep -n 'tailnet-dst'
cd ~/src/gh/SpechtLabs/k8s-deployment && git grep -n 'tailnet-dst'
```

If the thing has no API entity with these annotations yet, it isn't on the
tailnet as a Service: start with [Add a Tailscale Service on a host](add-a-tailscale-service-on-a-host.md)
or [Expose a Kubernetes service on the tailnet](expose-a-kubernetes-service-on-the-tailnet.md).

## People: add the group to `tailnet-allow`

1. On the API, add the group to `specht-labs.de/tailnet-allow` (comma
   separated). From [`modules/buckle-server/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/buckle-server/catalog-info.yaml):

   ```yaml
   specht-labs.de/tailnet-dst: svc:buckle
   specht-labs.de/tailnet-ports: tcp:443
   specht-labs.de/tailnet-allow: group:admins, group:sre
   ```

   `tailnet-allow` takes `group:`, `user:`, `autogroup:` and `tag:` entries.
   A `group:<name>` must be a Backstage Group with
   `specht-labs.de/tailnet-group: group:<name>` ([Groups](../reference/groups.md)).
2. If the people need different ports than the machines that use the same
   API, give them their own API entity with only their ports. The NAS does
   this: `synology-dsm-web` (443), `synology-dsm-https` (5001) and
   `synology-drive` (6690) in [`nas/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/nas/catalog-info.yaml)
   all point at `svc:nas`.
3. [Check the change locally](check-a-policy-change-locally.md), then commit
   and push.

## A machine: make its Component consume the API

1. On the consuming Component, list the API under `spec.consumesApis` and say
   which tag its traffic comes from:

   ```yaml
   metadata:
     annotations:
       specht-labs.de/tailnet-src: tag:buckle-agent
   spec:
     consumesApis:
       - api:nut
   ```

   (That's [`modules/nut-client/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/nut-client/catalog-info.yaml).)
   `tailnet-src` takes `tag:` entries only. For a Kubernetes workload it's
   the tag of its egress proxy, for a host module the host's tag.
2. Only consumption across the tailnet renders a grant. When consumer and
   provider run in the same cluster, Backstage counts it as pod-network
   traffic and renders nothing. When the traffic goes over the LAN (Home
   Assistant to NUT), use `dependsOn`, not `consumesApis`, or Backstage renders
   a grant nobody uses.
3. A tag that has no Component of its own (a device, a proxy) goes into the
   API's `tailnet-allow` instead, like a group.
4. [Check the change locally](check-a-policy-change-locally.md), then commit
   and push.

## Apply it

1. Backstage picks up catalog changes within minutes and publishes the
   policy once an hour. The pull request from `backstage/tailnet-policy`
   then contains your grant:

   ```sh
   gh pr list --repo SpechtLabs/homelab --head backstage/tailnet-policy
   ```

2. [Review and merge it](review-and-merge-the-policy-pull-request.md).

## Check it worked

In Backstage, **Tailscale > Preview access**, "from" the group or tag: the
Service and port are listed. Then try it from a client in that group or with
that tag (`nc -vz <name>.sphinx-map.ts.net <port>`, or the steps in
[Debug "I can't reach X"](debug-cant-reach-a-service.md)).

## If it didn't

- The grant isn't in the pull request: a malformed annotation (a `*` port,
  a `tailnet-dst` that isn't `tag:` or `svc:`) and a consumer without
  `tailnet-src` are skipped, and neither shows up in the PR body's
  "Problems" section. Render locally with `--json` and look at them:

  ```sh
  cd ~/src/gh/SpechtLabs/backstage
  yarn tailscale:diff --json /tmp/overview.json ~/src/gh/cedi/homelab/tailscale/policy.hujson \
    ~/src/gh/cedi/homelab ~/src/gh/SpechtLabs/k8s-deployment ~/src/gh/SpechtLabs/backstage_resources
  jq '.policies[0].catalog | {invalid, missingSource}' /tmp/overview.json
  ```

- Roll back by reverting your catalog commit; the next hourly run updates the
  pull request (or opens a new one) without the grant.
- Annotations can't carry capabilities (`app`), break-glass grants or exit
  node access: [Change a grant annotations can't express](change-a-grant-annotations-cant-express.md).
