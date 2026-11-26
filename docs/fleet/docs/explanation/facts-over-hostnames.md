# Facts over hostnames

`buckle.yaml` has no host list. Groups come from what the agents report: the Raspberry Pi
generation, whether it's a Compute Module, whether a GPS PPS line is wired to a GPIO, whether
timepi is on the host's LAN and the NIC can timestamp PTP in hardware. Where Buckle's built-in
facts can't tell, a module adds a script fact (`pi-facts` for `host.facts.script.rpi`, `ptp-facts`
for `host.facts.script.ptp`) and the group selects on that.

The reason is what goes wrong otherwise. On 2026-11-24 isa didn't get PTP: `ptp-client` was a
hand-written list of hardware, and isa had been slotted into the NUC's id-based spot when it took
over. Nothing failed; isa just quietly synced by NTP. A hostname says what someone once decided a
machine was for. A fact says what the machine is, and it's still true after a replacement, a
reinstall or a new host nobody remembered to add.

## Where ids remain

Some roles have no hardware fact: which host is the Buckle server, the k3s leader, the Jitsi box,
the two hosts that shut down last on power loss. Those groups select by `host.id`
([Groups](../reference/groups.md#roles-by-host-id)).

Tailscale tags look like the obvious alternative, and they still decide network access in the
tailnet policy. They make poor Buckle groups, though: an agent reports the tags it had when it
started, so a retag reaches Buckle only after the agent restarts. A role derived from a tag can't
move between hosts within one rollout, and the new host might not get it at all until someone
restarts its agent.

## Switching a group from ids to a fact takes two pushes

A fact nobody reports yet reads as false. If one commit adds the script fact and switches the
selector to it, the selector is false on every host until the new module has applied there, and
`removal: cleanup` removes what the group's modules installed in the meantime.

So:

1. Push the fact provider (the module that writes `/var/lib/buckle/facts.d/...`) and leave the
   selector alone. Wait until every host reports the fact (`GET /api/v1/hosts/<id>/facts`), and
   refresh the fixtures.
2. Push the selector change. `mise run validate` shows each host's groups before and after; they
   should match.

The same two-step rule applies to renaming a host
([Retag or rename a host](../how-to/retag-or-rename-a-host.md)).
