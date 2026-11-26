# isa, and why so much runs on it

isa is an HP EliteDesk 800 G6 Mini (i5-10500) on Ubuntu 26.04, the only always-on x86 box at
home besides the NUC. Since 2026-11-23 it runs four things the rest of the homelab depends on:
the Buckle server, tsidp, the NUT proxy and the o11y collector.

## How it got there

The NUC did all of this before. It's a Celeron (x86-64-v2, no AVX) on Ubuntu 24.10, which is
end of life, and Buckle 2.14.0's amd64 build crashed on it with `SIGILL`. That crash is why
`validate.yml` still runs `buckle validate` on an emulated Nehalem CPU: the NUC still runs a
Buckle agent. The move to isa happened without downtime for the hosts. The Buckle server's
part took about two minutes without a control plane
([bootstrap/README.md](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/README.md),
"Moving the server"). The NUC kept its agent, `nut-client` and its unmanaged Incus.

isa took over the NUC's roles one for one, with nothing spread out on the way, so one box
carries a lot.

## What it serves, and what happens when it's gone

| Role | Who uses it | If isa is down |
|---|---|---|
| Buckle server (`svc:buckle`) | every agent, you in the UI | No rollouts, no actions, no UI. Hosts keep running what they last applied. |
| tsidp (the `idp` node) | Buckle's sign-in, DSM's SSO, Grafana, Argo CD and Backstage on specht-labs (over Funnel), labk3s's Argo CD | Nobody signs in to anything that uses tsidp. Dex on both clusters gives up if idp is unreachable at its start, until kubelet restarts it. |
| NUT proxy (`svc:nut`) | upsmon on 14 Pis and the NUC, Home Assistant | Clients lose the UPS. On line power that's a warning after 300 s (`NOCOMMWARNTIME`). During a power cut nothing tells the early hosts to go, though a client whose UPS vanishes while it's on battery counts it as critical after `DEADTIME` and shuts down anyway. |
| o11y collector | the labk3s cluster's OTLP, the NAS's metrics, all six availability probes | The NAS goes dark in Grafana, and the Buckle, tsidp, labk3s API, NAS, Jellyfin and Home Assistant SLOs lose their data at once. |

The Buckle groups `buckle-server`, `tsidp`, `nut-server` and `o11y-collector` all select
`host.id == "isa"`, not a tag. Buckle keeps a host's enrolment-time facts (tags too)
until the agent restarts, so a tag-derived role couldn't move in one rollout.

## What softens it

The Services. Agents dial `buckle.sphinx-map.ts.net` and NUT clients dial
`nut.sphinx-map.ts.net`, not isa, so a replacement host takes over by serving the same Service;
no client changes. tsidp is the exception: it can't be a Service (it needs Funnel, and its
capability grants match on its own address), so it stays the `idp` node, and its state in
`/data` (node key, `oidc-key.json`, `oidc-funnel-clients.json`) has to move with it.

Buckle's database is backed up nightly at 01:30, 3 days on isa and 14 on the NAS. Grafana
alerts when the NAS copy is older than 26 h. A break-glass server
(`buckle-server-breakglass`) gets you into Buckle without tsidp
([bootstrap/README.md](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/README.md)).

## What doesn't

Two pieces exist only on isa as far as the repo says:

- the Buckle server's secrets in `/etc/buckle/secrets/` (K3S token, NUT passwords, the Argo CD
  age key, Jitsi secrets). The bootstrap README says everything else can be rebuilt "from git
  and the secrets", but not where a second copy of the secrets lives.
- tsidp's `/data`. Nothing in the repo backs it up; the NUC still has an old
  `/var/backups/tsidp` from the move.

Losing the disk without those means re-registering every OIDC client and re-creating the
secrets by hand, which is the real cost of having one isa. The modules, the units and the
server config come back from git.
