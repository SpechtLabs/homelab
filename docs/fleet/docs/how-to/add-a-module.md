# Add a module

Use this when the fleet should run something new, or an existing concern grows big enough to
stand on its own. A module is one directory under `modules/` with a `module.yaml` and its files;
Buckle loads every module in the repo and each decides by its `when` which hosts it applies to.

**Before you start:** the repo, `mise`, and one host to plan against. Read one existing module
that does something similar: [`modules/rpi-exporter`](https://github.com/SpechtLabs/homelab/tree/main/modules/rpi-exporter)
(binary from a GitHub release, a unit, a health check) and
[`modules/buckle-server`](https://github.com/SpechtLabs/homelab/tree/main/modules/buckle-server)
(templates, a timer, an informational check) are short and cover the usual shapes. Buckle's own
module reference: <https://buckle.sierrasoftworks.com>.

1. Decide who gets it. Select on a group in `buckle.yaml`, and derive that group from a fact
   (`host.facts.hardware...`, or a script fact like `pi-facts`), not from host names
   ([Facts over hostnames](../explanation/facts-over-hostnames.md)). Add the group if it's new.
2. Create `modules/<name>/module.yaml`:

    ```yaml
    name: my-exporter
    description: One line: what it runs, where, on which port.
    when: 'host.groups contains "pi"'
    needs: [base]            # modules (or 'group:<g>') that must apply first
    tags: [o11y]
    vars:
      my_exporter_port: 9999 # defaults; vars/ files override them
    tasks:
      - file.template:
          src: my-exporter.service.j2      # from modules/my-exporter/files/
          dest: /etc/systemd/system/my-exporter.service
          mode: "0644"
        notify: [restart]
      - systemd.unit: { name: my-exporter, enabled: true, active: true, daemon_reload: true }
    handlers:
      restart: { command.run: { run: [sh, -c, 'systemctl daemon-reload && systemctl restart my-exporter'] } }
    health:
      - name: metrics
        http: { url: 'http://127.0.0.1:{{ vars.my_exporter_port }}/metrics' }
    ```

    Put templates and files in `modules/<name>/files/`. Start generated files with
    `{{ buckle_managed }}` as the others do.
3. Shared values go in `vars/`, versions in `vars/versions.yaml` with a `# renovate:` comment
   ([Bump a pinned version](bump-a-pinned-version.md)), secrets in `buckle.yaml`
   ([Add or change a secret](add-or-change-a-secret.md)).
4. If it runs something other Systems use, add a `modules/<name>/catalog-info.yaml` for Backstage
   (copy `modules/rpi-exporter/catalog-info.yaml`).
5. Validate, then plan on a real host with your working tree, because the Mac can't plan apt or
   systemd tasks:

    ```sh
    mise run validate
    ssh pi@blade-pi1 "bash -c 'rm -rf /tmp/homelab && mkdir /tmp/homelab'"
    scp -rq buckle.yaml modules vars schedules workloads pi@blade-pi1:/tmp/homelab/
    ssh pi@blade-pi1 "bash -c 'sudo buckle plan --config /tmp/homelab'"
    ```

    `buckle plan` changes nothing. It resolves secrets itself from `/etc/buckle/secrets`, which
    exists only on isa, so a module that uses secrets can't be planned on another host this way.

6. PR, merge. The blades go first; pick a `when` that includes them if you want the canary to
   prove the module, or watch the first host that runs it closely.

!!! warning "Unverified"
    Step 5's copy-and-plan commands haven't been run while writing this page. The README
    describes the check ("`buckle plan` on meet with the working tree") but not how to copy it.

## Gotchas this fleet already paid for

- **A changed unit file needs a reload.** `systemd.unit`'s `daemon_reload: true` does nothing when
  the unit stays enabled and active, and a `systemd.restart` handler doesn't reload: the service
  keeps the old `ExecStart`. Restart through `systemctl daemon-reload && systemctl restart`, and add
  a `command.run` guarded by `NeedDaemonReload` (see `rpi-exporter`).
- **Handlers don't fire if the run stops mid-module.** Make restarts self-correcting (a
  `command.run` keyed on the actual running state) instead of trusting a handler alone.
- **Removing a task deletes what it made** (`removal: cleanup` is the default). Use
  `removal: leave` for anything you mean to keep, such as someone's home-directory checkout.
- **Lists can't come from a template.** `lines: '{{ vars.x }}'` is a type error; Buckle coerces
  rendered strings to scalars only. Use literal lists, or one task per item.
- **`unless` and `only_if` run at plan time**, before templates write files: pair a template
  change with a `notify` handler rather than a guard that reads the new file.
- **`command.run` with a `remove:` needs an explicit `id`**, or editing the command runs the old
  `remove:`. Never attach destructive removal hooks (there's no k3s uninstall for this reason).
- **`file.absent` on a non-empty directory needs `recursive: true`**, or the step blocks and the
  canary pauses.
- **`github.release` spends a GitHub API call per host per plan** while a host isn't on the pin.
  Prefer `file.download` of the release asset with `checksum:` its `checksums.txt`.
- **Health check regexes are Rust regexes**: `$` doesn't match before `systemctl`'s trailing
  newline without `(?m)`.
- **`when: 'x in map'` doesn't test map keys**; it's always false.
- Health checks are required by default and gate the rollout; mark one `required: false` when a
  failure shouldn't hold a rollout (as `buckle-server/backup-recent`).
