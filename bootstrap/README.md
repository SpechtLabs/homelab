# Buckle server bootstrap

`server.yaml` is the Buckle server's config, installed by hand on isa as
`/etc/buckle/server.yaml`; `server-breakglass.yaml` and `buckle-server-breakglass.service` are
the break-glass server for when tsidp is down. How to install, move and rescue the server is
in the fleet docs ([Backstage](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/), [source](../docs/fleet/docs/index.md)):

- [Why the server's config is installed by hand](../docs/fleet/docs/explanation/why-the-server-config-is-installed-by-hand.md)
- [Move the server to another host](../docs/fleet/docs/how-to/move-the-server-to-another-host.md)
- [Sign in when tsidp is down (break-glass)](../docs/fleet/docs/how-to/sign-in-when-tsidp-is-down.md)
- [Add or change a secret](../docs/fleet/docs/how-to/add-or-change-a-secret.md)
- [Enrol a new host](../docs/fleet/docs/how-to/enrol-a-new-host.md)
- [Restore the server database](../docs/fleet/docs/how-to/restore-the-server-database.md)
