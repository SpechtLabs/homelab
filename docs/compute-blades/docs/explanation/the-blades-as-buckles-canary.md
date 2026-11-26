# The blades as Buckle's canary

Every Buckle rollout, whatever it changes, runs on the four blades first. That's the first phase in [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml):

```yaml
phases:
  - name: canary
    select: 'host.groups contains "blades"'
    parallel: 4
    approval: auto
  - name: core      # nuc, isa, timepi, jumphost; two at a time
  - name: fleet     # everything else, labk3s included; four at a time
```

A host belongs to the first phase that selects it, so the blades are always in `canary`. With `on_failure: pause`, a required health check failing on any blade stops the rollout before a single other host has changed.

## Why the blades

They carry nothing the rest of the homelab depends on. The k3s nodes, the Ceph hosts, timepi, isa (the Buckle server itself, tsidp, the NUT proxy, the o11y collector) all have something leaning on them; the blades don't. A bad revision that breaks a blade costs nothing but the blade.

They're also representative. A CM4 on Debian 12 runs the same base modules as the other Pis (`base`, `pi-firmware`, `tailscale`, `alloy`, `time-sync` with PTP, the Buckle agent), so a broken package source, a config.txt change or a new Buckle agent version fails there first. All four go at once (`parallel: 4`), because there's no reason to protect them from each other.

There's no approval and no bake time (`bake: 0s`): the health checks are the gate. Before `core` starts, Buckle checks every host it already updated again, so a blade that went unhealthy after its apply still stops the rollout.

## What a pause in canary means

The revision broke something on at least one blade; nothing outside the blades has it yet. Look at the failing host's run in the Buckle UI: which module, which step, which health check. The blade-specific checks are the agent's (`agent`, `packaged-binary`, `metrics`, `api-certificate`, see [Ports, files and health checks](../reference/ports-files-and-health-checks.md#health-checks)); the rest come from the other modules on the blade, and the fix belongs to whichever module failed. Revert or fix in the repo, and the next revision supersedes the paused one (`supersede: latest`).

Renovate automerges patch and minor updates, and a merge to main is a rollout, so the canary is also what stands between an upstream release and the whole fleet.

## Keep the blades up

A canary that's down can't prove anything. If you take a blade off for longer, expect rollouts to treat it as a missing host.

!!! warning "Unverified"
    How a rollout treats an offline canary host hasn't been checked here; `buckle.yaml` has `stragglers: { parallel: 1, approval: auto }`, which handles hosts that miss their phase. See the [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/) and the Buckle UI before leaving a blade off during a rollout.
