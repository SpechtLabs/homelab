# Rollout policy

`rollout:` in [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml). Action
rollouts and schedules use the same phases and limits.

## Settings

| Key | Value | Meaning |
|---|---|---|
| `trigger` | `auto` | Every valid revision on `main` starts a rollout |
| `supersede` | `latest` | Finish the current rollout, then roll the newest revision; queued ones in between are skipped |
| `on_failure` | `pause` | A failed host pauses the rollout; nothing new starts |
| `settle` | `2m` | How long a required check may keep failing after an apply (a service restarting) before it counts |
| `health.bake` | `0s` | No bake window (Buckle's default is 5m); before each phase, every host the rollout already updated is checked again |
| `health.baseline` | `hold` | A host unhealthy before its wave is held until an operator forces or skips it |
| `stragglers.parallel` | `1` | Hosts that missed their phase converge one at a time after promotion |
| `stragglers.approval` | `auto` | |

## Phases

A host belongs to the first phase whose `select` matches. Every phase has `approval: auto`; the
health checks are the only gate.

| Phase | `select` | `parallel` | Hosts |
|---|---|---|---|
| `canary` | `host.groups contains "blades"` | 4 | blade-pi1..4 |
| `core` | `host.id in ["nuc", "isa", "timepi", "jumphost"]` | 2 | isa, nuc, timepi, jumphost |
| `fleet` | `true` | 4 | clusterpi-leader, clusterpi-worker1..4, storagepi-ceph1..3, meet, `labk3s` |
| `stragglers` | (virtual) | 1 | whoever missed their phase |

Inside `fleet`, module limits decide order and concurrency:

- A module's `parallel` counts every host that runs the module while that host's plan changes
  anything, whichever module changes it. `ceph` (`parallel: 1`) therefore means one Ceph host at a
  time and `k3s-agent` (`parallel: 1`) one worker at a time, reboots included.
- `k3s-agent` needs `group:k3s-server`: workers wait for the k3s server.
- A drain holds the host's slot until the node is back.
- With those limits, 4 leaves room for the k3s server or one worker, one Ceph host and meet at once.

## States

Rollout: `detected`, `planning`, `awaiting_approval`, `rolling`, `baking`, `paused`,
`rolling_back`, `rolled_back`, `completed`, `aborted`, `skipped` (superseded while queued).

Phase: `pending`, `awaiting_approval`, `running`, `baking`, `done`, `paused`, `skipped`.

Host row:

| State | Meaning |
|---|---|
| `pending`, `plan_pending`, `planned` | Waiting; plan not yet sent by the agent, or sent |
| `held` | Unhealthy before its wave (`baseline: hold`); waits for force or skip |
| `applying` | Applying the plan |
| `rebooting` | The run asked for a reboot; waiting for the agent to come back from a new boot |
| `baking` | Applied; checks running |
| `healthy` | Done |
| `failed` | Plan, apply or required checks failed; the module was rolled back on the host |
| `rolled_back` | Back on the stable revision |
| `skipped` | Excluded by an operator; converges later |

The API spells them in snake case as above (`GET /api/v1/rollouts/<id>`, `phases[].hosts[].state`).
