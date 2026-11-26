# Policy pipeline files

Everything that takes part in getting a policy onto the tailnet.

## SpechtLabs/homelab

| File | What |
|---|---|
| [`tailscale/policy.hujson`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy.hujson) | the rendered policy. Generated; a hand edit is overwritten by the next pull request |
| [`tailscale/policy/policy.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/policy.yaml) | the policy entity `tailscale:sphinx-map`: `catalogGrants: true`, `spec.publish` (repo, path, `flow: pullRequest`, `pullRequestBranch: backstage/tailnet-policy`), `spec.hosts` |
| [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml) | one entity per tag (`type: tag`): `tag`, `owners`, `appliesTo` |
| [`tailscale/policy/auto-approvers.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/auto-approvers.yaml) | which tag may advertise which Service (`type: autoApprovers`) |
| [`tailscale/policy/grants.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/grants.yaml) | grants the annotations can't say (`type: grant`) |
| [`tailscale/policy/ssh.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/ssh.yaml) | SSH rules (`type: ssh`) |
| [`tailscale/policy/node-attrs.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/node-attrs.yaml) | node attributes (`type: nodeAttr`) |
| [`tailscale/policy/tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tests.yaml), [`ssh-tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/ssh-tests.yaml) | tests (`type: test`, `tests` / `sshTests`) |
| [`tailscale/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/catalog-info.yaml) | the Resource `tailnet` |
| [`.github/workflows/tailscale.yaml`](https://github.com/SpechtLabs/homelab/blob/main/.github/workflows/tailscale.yaml) | `tailscale/gitops-acl-action`: `test` on pull requests, `apply` on pushes to `main`, both only when `policy.hujson` or the workflow changes. Secrets `TS_OAUTH_ID`, `TS_OAUTH_SECRET`, `TS_TAILNET`; one run at a time (`concurrency: tailscale-policy`) |
| every `catalog-info.yaml` with `specht-labs.de/tailnet-*` | the annotations ([Catalog annotations](annotations.md)) |

All entities in `tailscale/policy/` are `apiVersion: specht-labs.de/v1alpha1`,
`kind: Tailscale`, with `target: tailscale:sphinx-map`, `owner` and
`system: tailnet`. The repo-root `catalog-info.yaml` Location must not list
this directory.

## SpechtLabs/k8s-deployment

| File | What |
|---|---|
| [`apps/backstage/cluster/specht-labs/app-config.cluster.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/backstage/cluster/specht-labs/app-config.cluster.yaml) | catalog locations: `SpechtLabs/homelab/.../tailscale/policy/*.yaml` (the only one allowed kind `Tailscale`) and `SpechtLabs/backstage_resources/.../catalog/org.yaml` (the only one allowed `User` and `Group`); `tailscale.allowedRepos: [SpechtLabs/homelab]` |
| `apps/tailscale/` | the Tailscale operator (Helm chart, pinned in `base/kustomization.yaml`) and per cluster the `tailnet-ingress` ProxyGroup, auth secrets, and on labk3s the `k3s-idp-egress` egress and `PROXY_TAGS: tag:k3s` |

## SpechtLabs/backstage_resources (private)

| File | What |
|---|---|
| [`catalog/org.yaml`](https://github.com/SpechtLabs/backstage_resources/blob/main/catalog/org.yaml) | Users (`specht-labs.de/tailnet-login`) and Groups (`specht-labs.de/tailnet-group`) |

## The plugin: SpechtLabs/backstage-plugin-tailscale

Since 2026-11-27 the plugin is its own repository,
[SpechtLabs/backstage-plugin-tailscale](https://github.com/SpechtLabs/backstage-plugin-tailscale),
published to npm as `@spechtlabs/backstage-plugin-tailscale` (frontend),
`-tailscale-backend`, `-tailscale-common` and
`-catalog-backend-module-tailscale` (the catalog processor for kind
Tailscale). SpechtLabs/backstage installs them from npm. Backend files, under
[`plugins/tailscale-backend/src/`](https://github.com/SpechtLabs/backstage-plugin-tailscale/tree/main/plugins/tailscale-backend/src);
the entity model and annotation names are in
[`plugins/tailscale-common/src/model.ts`](https://github.com/SpechtLabs/backstage-plugin-tailscale/blob/main/plugins/tailscale-common/src/model.ts):

| File | What |
|---|---|
| `plugin.ts` | reads the catalog (kind Tailscale, Group, User, Component, API, `kubernetes-cluster` Resources), serves `/api/tailscale/overview`, `/policies/:namespace/:name/file`, `/access?entity=<ref>`; scheduled task `tailscale-publish` every 60 minutes (first run 3 minutes after start) |
| `graph.ts` | turns the tailnet annotations into edges |
| `compile.ts` | resolves groups, users and tags, merges catalog grants, checks ports and destinations, renders the file |
| `publish.ts` | the pull request (or push) to GitHub |
| `report.ts` | the pull request's title and body |
| `cli.ts` | the `backstage-tailscale-diff` command; SpechtLabs/backstage runs it as `yarn tailscale:diff` |

## Timing

| Step | When |
|---|---|
| Catalog sees a change | Backstage's catalog refresh, a few minutes |
| Backstage renders and publishes | hourly; it re-reads the catalog at each run |
| Pull request tested | on every push to `backstage/tailnet-policy` (about 45 s) |
| Policy applied | on merge to `main` (about 40 s) |
