# How-to guides

Task recipes. Each one says what you need first, the commands, and how to tell it worked.

**When something's wrong**

- [Respond to an availability alert](respond-to-an-availability-alert.md): the NAS, Jellyfin or Home Assistant SLO is burning.
- [Respond to a UPS alert](respond-to-a-ups-alert.md): on battery, runtime or battery low, FSD, stale metrics, replace battery.
- [Respond to a power cut](respond-to-a-power-cut.md): what to watch while it's out, what to check once it's back.
- [Fix DSM sign-in](fix-dsm-sign-in.md): SSO through tsidp fails.
- [Re-create the NAS's Tailscale serve config](recreate-the-nas-tailscale-serve-config.md): after a package reinstall, or when a NAS Service is gone.

**Checks**

- [Check the UPS and the NUT chain](check-the-ups-and-the-nut-chain.md): UPS state, and every link from the UPS to the clients.
- [Test the power-loss shutdown](test-the-power-loss-shutdown.md): prove the chain works without turning anything off.
- [Check Home Assistant's backups](check-home-assistant-backups.md): last night's backup on the NAS.

**Changes**

- [Give a new client NFS access](give-a-new-client-nfs-access.md): grant, export rule, mount.
- [Deploy a NAS compose project](deploy-a-nas-compose-project.md): copy from `nas/` and rebuild in Container Manager.
- [Reach Home Assistant](reach-home-assistant.md): web UI, API, LAN and tailnet.
- [Replace or rebuild isa](replace-or-rebuild-isa.md): move its four roles to a new box.
- [Get the NUC off its end-of-life Ubuntu](get-the-nuc-off-its-eol-ubuntu.md): reinstall or retire it.
