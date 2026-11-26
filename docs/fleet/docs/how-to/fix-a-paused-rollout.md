# Fix a paused rollout

Use this when a rollout shows `paused`, or when new commits sit at `detected` and don't roll out.
`rollout.on_failure: pause` stops a rollout at the first host that fails to plan or apply, or whose
required health check stays red past `settle` (2 min). Nothing else starts while it's paused,
including the next commit's rollout and that night's scheduled run (it waits up to its 2 h
`window`, then skips).

**Before you start:** the UI, or the API with the `bpost` helper from
[Call the Buckle API](call-the-buckle-api.md). SSH to the failed host.

1. Find the paused rollout and the failed host:

    ```sh
    curl -s -b "$J" "$B/api/v1/rollouts" | python3 -c '
    import json, sys
    for r in json.loads(sys.stdin.read(), strict=False)["items"][:20]:
        if r["state"] in ("paused", "detected", "rolling", "baking"):
            print(r["name"], r["state"], r["current_phase"], r["triggered_by"])'
    ```

    In the UI, open the rollout: the failed host is red. Expand its row under **Targets** for the
    error, the check or task that failed, and the run report.

2. Look at the host itself:

    ```sh
    ssh pi@storagepi-ceph2 "bash -c 'sudo buckle status | grep -v \"no change\"; sudo buckle health'"
    ```

    `buckle status` lists every step of the last run with its error; `buckle health` runs the
    applied modules' checks now. A module that failed was rolled back on the host to the stable
    revision already; the rollout waits for your decision.

3. Decide, then act. Each row has the UI control and its API call (`<rollout>` is the name or
   id, `<host>` the host id):

    | Situation | UI | API |
    |---|---|---|
    | You fixed the cause (pushed a fix, repaired the host, waited for Ceph to recover) | **Retry** in the rollout's split button: re-plans and re-applies every failed host | `bpost rollouts/<rollout>/retry '{"note":"..."}'` |
    | Only one host should go again | **Retry** on the host's row | `bpost rollouts/<rollout>/hosts/<host>/retry '{"note":"..."}'` |
    | The check is wrong or flaky, not the change | **Continue with checks waived…** on the host's row | `bpost rollouts/<rollout>/hosts/<host>/continue '{"waive_checks":["ceph/cluster"],"note":"..."}'` |
    | A host is broken for unrelated reasons | **Skip…** on the host's row: it converges later as a straggler | `bpost rollouts/<rollout>/hosts/<host>/skip '{"note":"..."}'` |
    | A host is `held` (unhealthy before its wave) and must go ahead | **Force apply…** | `bpost rollouts/<rollout>/hosts/<host>/force '{"note":"..."}'` |
    | Nothing failed, you paused it yourself | **Resume** | `bpost rollouts/<rollout>/resume '{"note":"..."}'` |
    | The revision is wrong | **Roll back…** (applies the stable revision to every host this rollout updated) or push a revert | `bpost rollouts/<rollout>/rollback '{"note":"..."}'` |
    | Give up on this rollout | **Abort…**: stops it where it is; hosts already updated keep the new revision | `bpost rollouts/<rollout>/abort '{"note":"..."}'` |

    The UI asks you to type the rollout's name for roll back and abort. For a paused nightly
    schedule, aborting is usually right: the next night runs it again on every host.

4. If you aborted or rolled back, push the fix as a new commit. A revert is preferred over a
   fleet rollback: it goes through the same phases and Git stays the record.

## Check it worked

The rollout leaves `paused` (`rolling`, then `completed`), or shows `aborted`. Any commit that was
waiting at `detected` starts within seconds:

```sh
curl -s -b "$J" "$B/api/v1/rollouts" | python3 -c '
import json, sys
for r in json.loads(sys.stdin.read(), strict=False)["items"][:3]:
    print(r["name"], r["state"])'
```

## If it didn't

- The same host fails again on retry: read `sudo journalctl -u buckle-agent -e` on it. Common
  causes from this fleet's history: an apt lock held by PackageKit (now masked by `base`), a
  dist-upgrade killed by Buckle's 30-minute apt timeout (`base`'s `dpkg-repair` step fixes it on
  the next run), a `file.absent` on a non-empty directory without `recursive: true`.
- `ceph/cluster` fails after a reboot: Ceph is still recovering. Wait for `HEALTH_OK` and retry;
  see the [ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/).
- A host shows **needs attention**: its own rollback failed too and it's on a mix of revisions.
  Fix it by hand, then **Retry**.
- How pauses and rollbacks work: [How a revision becomes a rollout](../explanation/how-a-revision-becomes-a-rollout.md).
