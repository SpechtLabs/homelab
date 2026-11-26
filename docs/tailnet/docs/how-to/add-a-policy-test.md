# Add a policy test

Use this when a grant must keep allowing something, or must keep something
closed (a device's own address once its Service is live, a group that must
not reach the NAS). Tailscale runs the policy's tests on every save; a failing
test rejects the whole policy and the previous one stays live.

**Before you start:** tests live in
[`tailscale/policy/tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tests.yaml)
(network) and [`ssh-tests.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/ssh-tests.yaml)
(SSH), one entity per concern.

1. Pick the source: a Backstage User (`user:cedi`), a group
   (`group:synology-users`), a tag (`tag:buckle-agent`) or a host alias
   (`clusterpi-leader`).
2. Pick the destinations as `<device-or-tag>:<port>`. Tests name devices,
   not Services: `nas-elbschloss:443`, `tag:ceph:6789`. A device needs an
   alias in `spec.hosts` of
   [`tailscale/policy/policy.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/policy.yaml)
   with its tailnet address (`dig +short <device>.sphinx-map.ts.net`).
3. Add the test to the entity for that concern, or a new entity. From
   `test-nut`:

   ```yaml
   apiVersion: specht-labs.de/v1alpha1
   kind: Tailscale
   metadata:
     name: test-nut
     title: NUT goes through svc:nut
     description: The server's own address is closed to the clients.
   spec:
     type: test
     target: tailscale:sphinx-map
     owner: group:spechtlabs
     system: tailnet
     appliesTo: [component:nut-server]
     tests:
       src: clusterpi-leader
       proto: tcp
       deny: ['tag:nut-server:3493']
   ```

   `tests` takes one test or a list; each has `src`, `proto`, and `accept`
   and/or `deny`. An SSH test (`sshTests`) has `src`, `dst` (devices),
   `accept` (users let in directly) and `check` (users that need check mode),
   as in `test-ssh-nuc`.
4. [Check it locally](check-a-policy-change-locally.md). The local render
   catches an unknown user or alias, not a failing test.
5. Push. The pull request's "Test policy" step runs every test against the
   tailnet ([Review and merge it](review-and-merge-the-policy-pull-request.md)).

## Check it worked

The pull request's `tailscale policy` check is green, and the rendered
`policy.hujson` has your test under `"tests"` (or `"sshTests"`).

## If it didn't

- The check fails on your test: either the test is wrong or the policy
  really allows (or denies) it. Preview access in Backstage, "from" the
  test's source, shows what the policy allows.
- A test with `accept` passes for admins no matter what: `group:admins`
  reaches everything (`grant-admins-everything`). Test from a narrower source.
