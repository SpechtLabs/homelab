# Repo layout

[SpechtLabs/homelab](https://github.com/SpechtLabs/homelab), branch `main`. The Buckle server reads
`buckle.yaml`, `modules/`, `vars/`, `schedules/` and `workloads/`; everything else is for people,
CI or Backstage.

| Path | What |
|---|---|
| `buckle.yaml` | Groups (from facts), the `labk3s` cluster, vars layering, secret references, rollout phases |
| `vars/` | Shared values, broad to narrow: `defaults`, `versions` (Renovate), `hw-*`, `group-*`, `host-*` ([Vars](vars.md)) |
| `modules/<name>/` | One concern each: `module.yaml`, `files/`, and a `catalog-info.yaml` for Backstage where it runs something ([Modules](modules.md)) |
| `workloads/argocd-root/` | The root Argo CD Application Buckle applies to `labk3s` |
| `schedules/` | Actions on a cron schedule ([Schedules](schedules.md)) |
| `fixtures/facts/` | One trimmed facts file per host; CI dry-plans each host against its file |
| `bootstrap/` | The server's config and units, installed by hand on isa; first-time setup notes |
| `nas/` | Compose projects for the Synology, deployed through DSM, not Buckle |
| `tailscale/` | The tailnet policy and its tests ([tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)) |
| `catalog-info.yaml`, `catalog/` | Backstage: the `homelab` Domain, its Systems, hosts as Resources; Buckle ignores them |
| `docs/` | TechDocs, one site per System (`mise run docs` checks them) |
| `mise.toml` | Pinned CLIs (buckle, bladectl, yq, mkdocs) and tasks `validate`, `docs`, `bladectl-config` |
| `renovate.json`, `.github/workflows/` | Dependency updates and CI ([CI and Renovate](ci-and-renovate.md)) |
