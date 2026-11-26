# Synology NAS

Compose projects for the Synology, deployed through DSM's Container Manager (not Buckle):
`media` (Jellyfin), `o11y` (exporters), `obsidian` (CouchDB for Obsidian LiveSync) and
`backup` (github-backup). Their secrets stay on the NAS and out of git (`.gitignore`):
`obsidian/.env` and `backup/github-backup/config.yaml`; the `*.example` files next to them
show the shape.
How to run and change the NAS is in the elbschloss docs ([Backstage](https://backstage.k8s.specht-labs.de/docs/default/system/elbschloss/),
[source](../docs/elbschloss/docs/index.md)):

- [Deploy a NAS compose project](../docs/elbschloss/docs/how-to/deploy-a-nas-compose-project.md)
- [Re-create the NAS's Tailscale serve config](../docs/elbschloss/docs/how-to/recreate-the-nas-tailscale-serve-config.md)
- [Give a new client NFS access](../docs/elbschloss/docs/how-to/give-a-new-client-nfs-access.md)
- [Fix DSM sign-in](../docs/elbschloss/docs/how-to/fix-dsm-sign-in.md)
- [Reference: the NAS](../docs/elbschloss/docs/reference/nas.md)
