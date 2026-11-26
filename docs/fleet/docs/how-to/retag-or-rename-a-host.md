# Retag or rename a host

Use this when a host's Tailscale tags change, or when it gets a new name. Both touch the two things
Buckle identifies a host by: its tailnet node name (the host id) and the tags whois reports for it.

## Retag a host

Tags are set in the tailnet, never by Buckle (the `tailscale` module leaves them alone). What
Buckle cares about:

- **`tag:buckle-agent` must stay.** The server checks it every time the agent connects
  (`agents.tailscale.allowed_tags` in `bootstrap/server.yaml`). Without it the agent is refused
  with `The tailnet node '<name>' is not trusted as an agent` and the host drops out of the fleet
  until the tag is back.
- **Facts lag.** Buckle keeps the tags it saw at enrolment in `host.facts.tailscale.tags` until the
  agent restarts. No group in `buckle.yaml` reads tags today, for this reason.

1. Change the tags in the admin console (Machines, the host, Edit ACL tags), keeping
   `tag:buckle-agent`.
2. Restart the agent so it reports the new tags:

    ```sh
    ssh <user>@<host> "bash -c 'sudo systemctl restart buckle-agent'"
    ```

3. If the host's fixture lists tags, refresh it: [Update a host's fixture](update-a-host-fixture.md).

### Check it worked

```sh
curl -s -b "$J" "$B/api/v1/hosts/<host>/facts" | jq '.tailscale.tags'
```

lists the new tags, and the host is `active` on its page.

## Rename a host

!!! warning "Unverified"
    Nobody has renamed a Buckle host in this homelab yet. The steps follow from how Buckle
    identifies agents (the host id is whatever tailnet whois says the node is called) and from
    the facts-switch-over rule in [Facts over hostnames](../explanation/facts-over-hostnames.md).
    Check each plan before it applies.

A new node name is a new host to Buckle. The danger is the moment in between: if the new id
matches none of the old id's `host.id` selectors, its first plan treats everything those roles
installed as orphans and removes it (`removal: cleanup` is the default).

1. List every place the old id appears:

    ```sh
    git grep -n '<old>' -- buckle.yaml vars/ modules/ schedules/ fixtures/
    ```

    Typical hits: groups and vars overlays in `buckle.yaml`, the `core` phase's `select`,
    `vars/host-<old>.yaml`, `ceph_hosts` and `ceph_admin_host` in `vars/group-ceph.yaml`.
    A Ceph host's rename is a Ceph change too (mon addresses); read the
    [ceph docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/) first.
2. First push: make each selector match both names, e.g. `host.id in ["<old>", "<new>"]`, copy
   the fixture to `fixtures/facts/<new>.json`, `mise run validate`, merge. Nothing changes on any
   host.
3. Rename the node in the tailnet (admin console, Machines, the host, Edit machine name). If
   `/etc/buckle/agent.yaml` on the host sets `host_id`, set it to `null`. Restart the agent:

    ```sh
    ssh <user>@<old> "bash -c 'sudo systemctl restart buckle-agent'"
    ```

    The host registers under the new id. `base` sets the system hostname to it in the next
    rollout.
4. Converge it (**Re-apply…** on the stable revision, or the next commit) and read its plan: it
   should change the hostname and little else.
5. Second push: drop the old name from the selectors and delete `fixtures/facts/<old>.json`.
6. Forget the old entry, which now sits offline: **Forget…** on its host page, or
   `curl -s -b "$J" -H "x-csrf-token: $(curl -s -c "$J" -b "$J" "$B/api/v1/csrf" | jq -r .token)" -X DELETE "$B/api/v1/hosts/<old>"`.

### Check it worked

`sudo buckle status` on the host shows `agent  <new> · ... (active)` and the stable revision
applied; `hostnamectl` prints the new name; the old id is gone from the Hosts page.
