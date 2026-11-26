# How power-loss shutdown is ordered

Everything at home hangs off one Ubiquiti UPS Tower with roughly 19 minutes of battery at
today's load. The NUT setup spends that battery on the few hosts that matter during and right
after an outage, and turns the rest off early. Exact values are in
[UPS and NUT](../reference/ups-and-nut.md).

## The sequence

```text
t = 0      mains gone; UPS Tower reports OB
t ~ 2-7 s  isa's dummy-ups copies the status (2 s poll); clients see OB (5 s poll)
           -> ONBATT on every client; early hosts start a 60 s upssched timer
t ~ 65 s   early hosts power off: labk3s, Ceph, the blades, the NUC
           (power back before then: ONLINE cancels the timer, nothing happens)
...        isa, jumphost, timepi and the NAS stay up on battery
LB         the UPS reports battery low (OB LB)
LB + 15 s  no primary has set FSD (HOSTSYNC), so each secondary upsmon declares
           the UPS critical itself
LB + 195 s isa, jumphost and timepi run SHUTDOWNCMD after FINALDELAY 180 s
```

The NAS follows its own DSM settings; it talks to the UPS Tower directly.

## Why early and late

The early group is the big one: five labk3s Pis, three Ceph Pis, four blades and the NUC. None
of them is needed to get through an outage or to recover from one, and each drew battery for
nothing, so they go after a minute. A minute rides out a flicker without taking the cluster
down. How Ceph and labk3s come back afterwards is in their own docs.

The late hosts are the ones you want last: the jumphost is the way in, timepi is the LAN's
time source, and isa is the NUT proxy everyone else reads the UPS through plus the Buckle
server. isa has to stay up at least as long as its clients. If it went first, the clients would lose the UPS, and
upsmon treats a UPS that disappears while on battery as critical after `DEADTIME` (30 s), so
the failure is at least safe: the clients go down rather than run blind.

isa reads the UPS Tower directly, not its own proxy, so its shutdown doesn't depend on its own
upsd. The NAS does the same through DSM. Home Assistant only reads the status.

## Why a proxy at all

The catalog's reason is that the fifteen clients shouldn't all poll the UPS. The proxy also
gives them one name, `svc:nut`, that can move to another host without touching a client.
Home Assistant stays on the LAN because `tag:smarthome` has no grant to `svc:nut`.

## Gaps

!!! warning "Unverified: no full power cut has happened under this config"
    The NUT journals on isa (10 days) and a Pi (30 days) show no power event. The
    sequence above is what the config and NUT's documented upsmon behaviour say, not something
    anyone has watched.

- **Nobody is primary.** isa's upsd has an `admin` user with `upsmon primary`, but no upsmon
  logs in with it, and isa is a secondary of the UPS Tower. So nothing sets `FSD` for the fleet
  and nothing tells the UPS to cut its output once the hosts are down
  (`driver.flag.allow_killpower: 0` on the proxy). If mains returns while the battery still
  holds, hosts that already powered off may stay off until their power is cycled. That's the
  usual NUT power race; it hasn't been tested here.
- **`FSD` on a late host doesn't wait.** The late hosts' upssched runs `delayed_shutdown` on
  `FSD`, and that script powers off at once. The 180 s only applies when upsmon itself decides
  the UPS is critical.
- **No alerting.** Grafana has no rule on the UPS or NUT. Buckle's `ups-reachable` and
  `proxied-ups` checks fail when the chain breaks, but only show on Buckle's host pages and
  during rollouts.
- The low-battery threshold is the UPS Tower's own setting; the repo doesn't record it.
