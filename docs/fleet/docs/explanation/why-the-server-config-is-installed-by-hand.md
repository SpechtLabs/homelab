# Why the server's config is installed by hand

Buckle manages everything on isa except the one thing that runs Buckle. `server.yaml`,
`server-breakglass.yaml`, `server.env`, the secrets and the two systemd units sit in
`/etc/buckle` and `/etc/systemd/system` because someone put them there with `install`, and the
copies in [`bootstrap/`](https://github.com/SpechtLabs/homelab/tree/main/bootstrap) are a record,
not a source. The header of `server.yaml` says why in one line: the server shouldn't be able to
break its own config.

Suppose the server's config were a module. A revision with a bad `server.yaml` (a wrong listen
address, a typo in `allowed_tags`, a broken OIDC block) would roll out to isa in `core`, restart
the server into it, and the server that comes up couldn't serve the agents, the UI, or the
rollout that would fix it. The fix would have to go in by hand anyway, at the worst moment.
Keeping it out of the fleet means a bad commit can break hosts, but never the thing that rolls
back hosts.

Secrets are the other reason. They live as files under `/etc/buckle/secrets/` on the server and
nowhere in git; a module that installed them would need them from somewhere else first.

What Buckle does manage on isa:

- the binary, through the `buckle` module like on every host, so the server upgrades in `core`
  right after the canary;
- the nightly database backup (`buckle-server` module);
- the agent's `server:` line in `agent.yaml`, so agents follow `svc:buckle` wherever it's served.

## The cost: drift nobody sees

A hand-installed file doesn't drift-correct, and nothing compares it with the repo. When this page
was written (2026-11-26), `server.yaml` on isa matched `bootstrap/server.yaml`, but
`server-breakglass.yaml` was still the NUC-era version: old repo URL, retired `allowed_tags`, the
NUC as join URL. The break-glass server is only started when tsidp is down, so the drift had gone
unnoticed for days; started as it was, it would have refused every agent. The how-to now diffs it
before use ([Sign in when tsidp is down](../how-to/sign-in-when-tsidp-is-down.md)).

The rule that keeps this manageable: every change to the server's config goes into `bootstrap/`
in a commit first, then onto isa with `install`, and the two config files stay identical apart
from `web` and `listen.http`. Old live versions are kept next to them as
`server.yaml.bak-pre-<change>` on isa.
