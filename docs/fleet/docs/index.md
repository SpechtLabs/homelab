# Fleet management (Buckle)

[Buckle](https://buckle.sierrasoftworks.com) configures every Debian host in the homelab from
[SpechtLabs/homelab](https://github.com/SpechtLabs/homelab). The server runs on **isa** and polls
`main` every 30 s; each new commit becomes a revision that rolls out through three phases
(`canary`, `core`, `fleet`), host by host, gated on health checks. Agents dial the server over the
tailnet and are identified by their Tailscale node name, so there's no SSH and no inventory.

UI and API: <https://buckle.sphinx-map.ts.net> (sign-in through tsidp, `group:admins` only).

## The parts

| Part | Where | What it does |
|---|---|---|
| Buckle server | isa, `buckle-server.service` | Watches the repo, plans and rolls out revisions, runs schedules and actions, serves the UI/API, applies the `labk3s` workloads |
| Buckle agents | all 17 hosts, `buckle-agent.service` | Report facts, apply their host's plan, run actions, correct drift every 15 min |
| The repo | `buckle.yaml`, `modules/`, `vars/`, `schedules/`, `workloads/` | The fleet's desired state; every commit on `main` is a deploy |
| `svc:buckle` | Tailscale Service served by isa | `tcp:443` for the UI/API, `tcp:7700` for agents (PROXY v2) |
| Nightly backup | isa, `buckle-backup.timer` | `sqlite3 .backup` of the database, kept on isa and on the NAS |

## Where to start

- Something is wrong with a rollout: [Fix a paused rollout](how-to/fix-a-paused-rollout.md).
- A host needs a reboot or a patch: [Run an action on a host](how-to/run-an-action-on-a-host.md),
  or for a k3s or Ceph host [Reboot a k3s or Ceph host](how-to/reboot-a-k3s-or-ceph-host.md).
- A new machine: [Enrol a new host](how-to/enrol-a-new-host.md).
- Can't sign in to the UI: [Sign in when tsidp is down](how-to/sign-in-when-tsidp-is-down.md).
- First time changing the repo: [Your first change](tutorials/your-first-change.md).

The four sections:

- [Tutorials](tutorials/index.md): one guided change, edit to verified.
- [How-to guides](how-to/index.md): task recipes for day-to-day work.
- [Reference](reference/index.md): hosts, modules, groups, phases, vars, checks, API, CI.
- [Explanation](explanation/index.md): how rollouts work, why things are built this way, history.

## Related systems

Buckle rolls out the modules that build other Systems; their own docs cover what runs there.

- [tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/): the policy,
  tags and Tailscale Services Buckle depends on.
- [ceph](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/) and
  [labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/): the clusters
  Buckle brings up and reboots one host at a time.
- [timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/),
  [compute-blades](https://backstage.k8s.specht-labs.de/docs/default/system/compute-blades/),
  [jitsi](https://backstage.k8s.specht-labs.de/docs/default/system/jitsi/),
  [elbschloss](https://backstage.k8s.specht-labs.de/docs/default/system/elbschloss/).
