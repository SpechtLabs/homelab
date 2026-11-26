# Trace a grant from the catalog to the tailnet

Every Pi watches the UPS through `svc:nut`, the NUT server on isa. This walk
follows that one grant from where it's declared to the connection it allows.
Nothing here changes state, so it's safe to do on a quiet afternoon. Expect
about 20 minutes.

You'll need a clone of SpechtLabs/homelab, SpechtLabs/k8s-deployment,
SpechtLabs/backstage and SpechtLabs/backstage_resources side by side under
`~/src/gh/`, a Backstage login, and Tailscale SSH to a compute blade (any
admin or SRE has it).

## 1. Find who provides the API

The NUT server's catalog entry declares where tailnet clients reach it:

```sh
cd ~/src/gh/cedi/homelab
git grep -n -A2 'tailnet-dst: svc:nut'
```

You'll see `modules/nut-server/catalog-info.yaml`, the API `nut`, with
`specht-labs.de/tailnet-dst: svc:nut` and `specht-labs.de/tailnet-ports: tcp:3493`.
That pair says "this API is reached at the Tailscale Service `svc:nut`, on TCP
3493". It says nothing about who may reach it.

## 2. Find who consumes it

```sh
git grep -n 'api:nut' -- '*catalog-info.yaml'
```

`modules/nut-client/catalog-info.yaml` lists `api:nut` under `consumesApis`,
and its `specht-labs.de/tailnet-src: tag:buckle-agent` says the traffic comes
from devices tagged `tag:buckle-agent` (every Buckle host). Backstage joins
the two: consumer's source, provider's destination and ports.

## 3. See the rendered grant

Open the rendered file on `main`:

```sh
grep -n -B3 -A4 '"svc:nut"' tailscale/policy.hujson
```

Two hits. One is the auto approver (`"svc:nut": ["tag:nut-server"]`), which
lets isa advertise the Service. The other is the grant:

```hujson
// From the catalog: nut
// Consumed by nut-client.
{
 "src": ["tag:buckle-agent"],
 "dst": ["svc:nut"],
 "ip":  ["tcp:3493"],
},
```

The comment names the API and its consumer: that's how you get from any
catalog grant back to its source. Grants without "From the catalog" come
from `tailscale/policy/grants.yaml`.

## 4. Look at it in Backstage

Open the **Tailscale** page in Backstage's sidebar and pick **Grants**. The
same grant is there with links to `api:nut` and `component:nut-client`. Now
open **Preview access** and pick `tag:buckle-agent`: `svc:nut` on tcp:3493 is
among what it reaches. The API page for `nut` carries the same view on its
tailnet card.

## 5. Render it yourself

Backstage's tailnet plugin has a CLI that renders the policy from local
clones and compares the result with a file. Point it at `main`'s file:

```sh
cd ~/src/gh/SpechtLabs/backstage
yarn tailscale:diff ~/src/gh/cedi/homelab/tailscale/policy.hujson \
  ~/src/gh/cedi/homelab ~/src/gh/SpechtLabs/k8s-deployment ~/src/gh/SpechtLabs/backstage_resources
```

With your clones up to date it ends with
`No differences: the rendered policy allows what policy.hujson allows.` The
lines above that list every destination by class: `svc:nut` is under
"Services", `tag:ceph` and `tag:k3s-node` under "peer meshes", `tag:tsidp`
and `tag:tka` under "capability targets". This is the command you'll use
before pushing a real change ([Check a policy change locally](../how-to/check-a-policy-change-locally.md)).

## 6. Watch the grant work

From a compute blade, the Service answers and isa's own address doesn't:

```sh
ssh pi@blade-pi1 "bash -c 'upsc ups@nut.sphinx-map.ts.net ups.status'"
```

You should see `OL` (on line). Then try both addresses on the raw port (the
Pis have no `nc`, so this uses bash's `/dev/tcp`):

```sh
ssh pi@blade-pi1 "bash -c 'timeout 3 bash -c \"</dev/tcp/nut.sphinx-map.ts.net/3493\" && echo svc-open; timeout 3 bash -c \"</dev/tcp/isa.sphinx-map.ts.net/3493\" && echo isa-open || echo isa-closed'"
```

Expected: `svc-open`, then `isa-closed`. The second one is the policy test
`test-nut` in [`tailscale/policy/tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tests.yaml)
holding: clients reach NUT through the Service only, so the server could move
to another host and no client would notice.

## 7. See who serves it

```sh
ssh cedi@isa "bash -c 'tailscale serve status'"
```

Among the entries:

```text
tcp://nut.sphinx-map.ts.net:3493 (tailnet only) (svc:nut)
|--> tcp://localhost:3493
```

`modules/nut-server` keeps that serve entry in place.

## Where to go next

You've seen the whole chain: annotations, the rendered grant, Backstage's
views, the local render, the serving host and a client. The
[explanation of how the catalog becomes the policy](../explanation/how-the-catalog-becomes-the-policy.md)
covers the rules Backstage applies on the way, and
[Give a group or tag access to a Service](../how-to/give-a-group-or-tag-access-to-a-service.md)
is the first real change most people make.
