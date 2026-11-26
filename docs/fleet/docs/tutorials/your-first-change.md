# Your first change

You'll make jumphost ship apt's history log (`/var/log/apt/history.log`) to Loki, and follow the
change all the way: edit, local validation, pull request, CI, merge, the rollout through
`canary`, `core` and `fleet`, and a check on jumphost itself. The change touches one host and only
reloads Alloy there, so it's a safe one to learn on. Keep it afterwards or revert it the same way.

You need: a checkout of [SpechtLabs/homelab](https://github.com/SpechtLabs/homelab), `mise`, the
`gh` CLI, and a tailnet login in `group:admins` (for the Buckle UI and SSH).

## 1. Find where the value lives

Alloy reads its log files from the var `o11y_log_paths`. The default, in
[`vars/defaults.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/defaults.yaml), is
`["/var/log/*.log"]`, which doesn't reach into `/var/log/apt/`.

Vars stack broad to narrow, as listed under `vars:` in
[`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml); the later entry
wins. jumphost has no vars file of its own, only an inline entry near the end:

```yaml
  - when: 'host.id == "jumphost"'
    values: { dotfiles_preset: core }
```

A list replaces the one before it rather than adding to it, so the override has to repeat the
default glob.

## 2. Make the change

```sh
cd ~/src/gh/cedi/homelab
git switch -c jumphost-apt-history
```

Edit that entry in `buckle.yaml`:

```yaml
  - when: 'host.id == "jumphost"'
    values:
      dotfiles_preset: core
      o11y_log_paths: ["/var/log/*.log", "/var/log/apt/history.log"]
```

## 3. Validate locally

```sh
mise install          # once: the buckle CLI pinned in mise.toml
mise run validate
```

`buckle validate` dry-plans every host in `fixtures/facts/` and prints one line per host with its
groups and selected modules. The last lines should read:

```text
ok: no problems found
24 modules in .: 0 errors, 0 warnings
```

It can't show you the rendered Alloy config: a full plan needs apt and systemd, which macOS
doesn't have. The live plan in the rollout shows the diff.

## 4. Open a pull request

```sh
git commit -am "feat(alloy): jumphost ships apt's history log"
git push -u origin jumphost-apt-history
gh pr create --fill
```

The `validate` workflow runs on the PR: `buckle validate` again, the same validate under an
emulated x86-64-v2 CPU (the NUC's), and the docs build. Wait for green:

```sh
gh pr checks --watch
```

## 5. Merge and watch the rollout

```sh
gh pr merge --squash --delete-branch
```

Within 30 s the server sees the new commit on `main`, validates it and starts a rollout. Open
<https://buckle.sphinx-map.ts.net>, then **Rollouts**: the top row is your commit, with a
three-word name such as `wet.left.talk`.

On the rollout page, watch the phases:

1. **canary**: the four blades plan and apply at once. Their plans change nothing, so they turn
   healthy in seconds.
2. **core**: isa, the NUC, timepi and jumphost, two at a time. jumphost is the one host with a
   change: its plan lists `alloy` with a diff of `/etc/alloy/config.alloy` and a `reload` handler.
   It applies, then its Alloy checks (`alloy/ready`, `alloy/unit`) have to pass before it counts
   as healthy.
3. **fleet**: the k3s nodes, the Ceph hosts, meet and the `labk3s` cluster. Nothing to change.

The whole rollout of a one-host change takes about two minutes. It ends `completed` with every
host healthy, and the commit becomes the stable revision.

## 6. Verify on the host

```sh
ssh pi@jumphost "bash -c 'sudo grep -n apt/history /etc/alloy/config.alloy; sudo buckle status | head -5'"
```

You should see the new path in the config and `buckle status` naming your commit as the applied
revision:

```text
    {"__path__" = "/var/log/apt/history.log"},
agent     jumphost · 2.22.0 · connected to http://buckle.sphinx-map.ts.net:7700 (active)
revision  applied <your commit> · stable <your commit>
```

Alloy tails files from their end, so lines show up in Loki once apt writes again (at the latest
after the 03:00 nightly upgrade). In Grafana Explore on the homelab Loki:

```logql
{hostname="jumphost", filename="/var/log/apt/history.log"}
```

## What you did

Every change follows this path: a commit on `main` is a deploy, CI is the only review gate, and
the blades go first because a failure there pauses the rollout before it reaches anything that
matters. [How a revision becomes a rollout](../explanation/how-a-revision-becomes-a-rollout.md)
explains the gates. When a rollout doesn't finish, go to
[Fix a paused rollout](../how-to/fix-a-paused-rollout.md).
