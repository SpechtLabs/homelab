# Add or change a secret

Use this when a module needs a password, token or key that must not be in the public repo, or
when an existing one rotates. Values live in one file each under `/etc/buckle/secrets/` on isa;
`buckle.yaml` holds only references. The server sends a secret only to the hosts whose modules use
it, and plans and the UI show it as `«secret:NAME@fingerprint»`.

**Before you start:** SSH to isa as `cedi` with sudo, the repo, and your password manager (the
database backup doesn't contain the secrets: the password manager is their only other copy).

## Add a secret

1. Write the value on isa, root-owned, mode 0600, with no trailing newline (the file provider trims
   one, but not more):

    ```sh
    ssh cedi@isa
    read -rs VALUE && printf '%s' "$VALUE" | sudo install -m 0600 /dev/stdin /etc/buckle/secrets/MY_SECRET; unset VALUE
    ```

    (isa's login shell is fish: run `bash` first.) Store the same value in the password manager.
2. Declare it in [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml)
   under `secrets:`, next to the others:

    ```yaml
    secrets:
      MY_SECRET: { file: /etc/buckle/secrets/MY_SECRET }
    ```

3. Use it in the module, only where Buckle writes it straight into a file or a process: a
   `file.template` body (`password = {{ secrets.MY_SECRET }}`), `command.run` `env`, `file.download`
   or `http` check `headers`. In a `vars` value or a displayed field it's a plan-time error.
4. `mise run validate` (it doesn't need the value), PR, merge. The first rollout delivers it.

## Change a value

1. Overwrite the file on isa as in step 1 above, and update the password manager.
2. Hosts get the new value with the next rollout that plans them; the plan shows the changed
   fingerprint on exactly the lines that use it. To push it now: **Rollouts**, **Re-apply…** on
   the stable revision's row. Only hosts whose rendered files change will apply.
3. If both ends of a credential are in the fleet (the NUT passwords: `nut-server` on isa and
   `nut-client` on the Pis), they change in the same rollout. Between isa's apply in `core` and a
   Pi's apply in `fleet`, that Pi's upsmon can't log in.

## Check it worked

```sh
ssh cedi@isa "bash -c 'sudo ls -l /etc/buckle/secrets/'"
```

lists the file as `-rw------- root root`. In the rollout, the host's plan shows the
`«secret:MY_SECRET@...»` token in the diff, and the module's health checks pass afterwards.

## If it didn't

- `validate` or the server rejects the revision with an undeclared secret: the name in the
  template and in `secrets:` differ (they're case-sensitive).
- The plan fails on the host naming the secret: the file is missing or unreadable on isa.
- The secrets in use today and what they're for: [Server and agents](../reference/server-and-agents.md#secrets).
