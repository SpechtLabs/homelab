# Run an action on a host

Use this when one host needs something now: patch its packages, reboot it, reboot it only if a new
kernel waits. Actions are declared by modules (`actions:` in `module.yaml`) and run on demand,
never as part of a revision's rollout.

**Before you start:** the UI or the API ([Call the Buckle API](call-the-buckle-api.md)). The
host must be online, not paused, not applying in a rollout and not running another action, or the
server refuses.

!!! warning "k3s nodes and Ceph hosts"
    An action run on one host goes straight to it: no phase limits, no node drain. For
    `clusterpi-*` and `storagepi-ceph*` use
    [Reboot a k3s or Ceph host](reboot-a-k3s-or-ceph-host.md) instead, which runs the action as a
    rollout that drains the node and waits for Ceph.

## The actions

| Module | Action id | Name in the UI | Confirm | What it does |
|---|---|---|---|---|
| `base` | `upgrade` | Upgrade packages | no | `apt upgrade` with autoremove; reboots afterwards only if a newer kernel is installed or `/run/reboot-required` exists |
| `base` | `reboot` | Reboot | yes | Reboots in 5 s, waits up to 10 min for the agent to come back |
| `base` | `reboot-if-required` | Reboot for a pending kernel | no | Reboots only if a newer kernel of the running flavour is installed (or `/run/reboot-required` exists) |
| `k3s-agent` | `reboot` | Reboot node | yes | Reboots a k3s worker, no drain |
| `ceph` | `bootstrap` | Bootstrap the Ceph cluster | yes | Creates the Ceph cluster, once (skipped if `/etc/ceph/ceph.conf` exists) |
| `ceph-disk` | `shrink-root` | Split the NVMe for Ceph | yes | Shrinks root and adds the OSD partition on the next boot; reboots now |

The last two are one-off setup steps for the Ceph hosts; the
[ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/) say when to use them.

## From the UI

1. Open the host's page (**Hosts**, then the host).
2. Pick the action from its actions, write a note (required for the confirm ones; it goes into
   the audit log) and start it.
3. The run appears on the host's page and on the Rollouts timeline. Wait for `succeeded`.

## From the API

1. Start it (here: patch jumphost):

    ```sh
    bpost hosts/jumphost/actions/base/upgrade '{"note":"patch now"}'
    ```

    You get `{"run_id":"..."}` back (HTTP 202).
2. Follow the run:

    ```sh
    curl -s -b "$J" "$B/api/v1/hosts/jumphost/runs/<run_id>" | python3 -c '
    import json, sys
    r = json.loads(sys.stdin.read(), strict=False)
    print(r["state"], r.get("outcome"), "changes", r.get("changes"))'
    ```

    Repeat until the state is final (`succeeded` or a failure). A reboot shows the host offline
    for a minute or two in between.

## Check it worked

The run's outcome is `succeeded`. For an upgrade, on the host:

```sh
ssh pi@jumphost "bash -c 'apt list --upgradable 2>/dev/null | tail -n +2 | wc -l; uname -r'"
```

shows 0 upgradable packages, and after a reboot the newest installed kernel.

## If it didn't

- `The action '...' asks for confirmation: send a note for the audit log.`: add a non-empty
  `note`.
- Refused because the host is applying in a rollout: wait for the rollout, or run the action
  later. A paused host refuses too ([Pause a host for manual work](pause-a-host-for-manual-work.md)).
- An upgrade failed mid-way with dpkg half-configured: the next rollout or upgrade runs `base`'s
  `dpkg-repair` step (`dpkg --configure -a`) first. Run `base: upgrade` again.
- To run an action on many hosts at once through the phases, start an action rollout:
  **Run action…** on the Hosts page, or `bpost rollouts '{"module":"base","action":"upgrade","note":"..."}'`.
