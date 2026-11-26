# Buckle settings

Everything here is in [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml) and the two k3s modules.

## The cluster

```yaml
clusters:
  labk3s:
    kind: kubernetes
    nodes:     'host.groups contains "k3s-server" || host.groups contains "k3s-agent"'
    executors: 'host.groups contains "k3s-server"'
    identity: local
    labels: { site: home }
    maintenance: { drain: disruptive, deadline: 10m }
```

| Setting | Means |
|---|---|
| `executors` | the k3s server applies labk3s's workloads (`workloads/argocd-root`) |
| `identity: local` | with its own admin kubeconfig, `/etc/rancher/k3s/k3s.yaml` |
| `drain: disruptive` | a rollout cordons and drains a node before a run that disrupts it, and uncordons it once the host is healthy |
| `deadline: 10m` | how long the pods get to move before the drain counts as failed |

A run disrupts the node when it reboots the host or changes a module marked `disrupts: node`. Both `k3s-server` and `k3s-agent` are. A drain holds the host's slot in its phase until the node is back. Buckle 2.22 evicts once and doesn't wait for the evicted pods; SierraSoftworks/buckle#908 (open) makes it wait.

Single-host actions from the host page run outside a rollout and don't drain.

## Groups

| Group | Selector |
|---|---|
| `k3s-server` | `host.id == "clusterpi-leader"` |
| `k3s-agent` | `host.id like "clusterpi-worker*"` |

## Module ordering and limits

| Module | `needs` | `parallel` | `disrupts` |
|---|---|---|---|
| `k3s-server` | `base` | (phase limit) | `node` |
| `k3s-agent` | `base`, `group:k3s-server` | 1 | `node` |
| `argocd-seed` | `k3s-server` | | |
| workload `argocd-root` | `module:argocd-seed` | | `removal: keep` |

A module's `parallel` counts every host that runs it while that host's plan changes anything, whichever module changes it. So `k3s-agent: parallel: 1` means one worker at a time for any change, a `base` reboot included.

## Phases

The k3s nodes are in the last phase, `fleet` (`select: 'true'`, `parallel: 4`, `approval: auto`). The limits above leave room for one k3s node, one Ceph host and meet at once. Before that come `canary` (the four blades) and `core` (nuc, isa, timepi, jumphost).

| Rollout setting | Value |
|---|---|
| `trigger` | `auto`: every revision on `main` |
| `on_failure` | `pause` |
| `settle` | `2m` (a failing check may keep failing that long while a service restarts) |
| `health.bake` | `0s` |

## Schedules that touch the nodes

| Schedule | When (Europe/Berlin) | Action |
|---|---|---|
| [`nightly-upgrades.yaml`](https://github.com/SpechtLabs/homelab/blob/main/schedules/nightly-upgrades.yaml) | 03:00, window 2 h | `base: upgrade` |
| [`nightly-kernel-reboots.yaml`](https://github.com/SpechtLabs/homelab/blob/main/schedules/nightly-kernel-reboots.yaml) | 05:30, window 2 h | `base: reboot-if-required` |

Both run through the phases, so the k3s nodes go one at a time, drained around a reboot.

## Secrets

| Secret | Used by |
|---|---|
| `K3S_TOKEN` | both k3s config templates |
| `ARGOCD_AGE_KEY` | `argocd-seed`, to decrypt k8s-deployment's SOPS secrets on a cluster without Argo CD |

Both are files under `/etc/buckle/secrets/` on the Buckle server (isa).
