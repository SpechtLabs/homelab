# homelab

Fleet configuration for the homelab, applied by [Buckle](https://buckle.sierrasoftworks.com).
The Buckle server runs on isa and watches this repository; every commit on `main` becomes a
revision that rolls out through the phases in `buckle.yaml`, gated on health checks. Agents
connect over the tailnet and are identified by their Tailscale node, so there is no SSH and no
inventory.

## Docs

How to run, change and fix each part lives in its System's TechDocs (tutorials, how-to guides,
reference, explanation). Read them in Backstage; the Markdown is in `docs/<system>/`, which
also renders on GitHub when Backstage is down.

| System | What | Backstage | Source |
|---|---|---|---|
| fleet | Buckle: rollouts, actions, hosts, modules, upgrades, the server | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/) | [docs/fleet](https://github.com/SpechtLabs/homelab/tree/main/docs/fleet/docs) |
| tailnet | The tailnet policy (rendered from the catalog), Services, tags, tsidp | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) | [docs/tailnet](https://github.com/SpechtLabs/homelab/tree/main/docs/tailnet/docs) |
| labk3s | The k3s cluster on the clusterpis, over the tailnet | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/) | [docs/labk3s](https://github.com/SpechtLabs/homelab/tree/main/docs/labk3s/docs) |
| ceph | Ceph on the storage Pis, ceph-csi, alerts | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/) | [docs/ceph](https://github.com/SpechtLabs/homelab/tree/main/docs/ceph/docs) |
| elbschloss | The house: isa, the NAS, the UPS and NUT, Home Assistant | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/elbschloss/) | [docs/elbschloss](https://github.com/SpechtLabs/homelab/tree/main/docs/elbschloss/docs) |
| timekeeping | timepi (GPS, PPS, PTP) and every host's chrony | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/) | [docs/timekeeping](https://github.com/SpechtLabs/homelab/tree/main/docs/timekeeping/docs) |
| compute-blades | The blades, compute-blade-agent, bladectl | [docs](https://backstage.k8s.specht-labs.de/docs/default/system/compute-blades/) | [docs/compute-blades](https://github.com/SpechtLabs/homelab/tree/main/docs/compute-blades/docs) |

## Checks

Everything CI runs is a mise task; run the same before pushing:

```sh
mise install            # pinned tools (mise.toml)
mise run validate       # buckle validate: config + a dry plan of every host in fixtures/facts
mise run docs           # markdownlint, link check, strict mkdocs build of every docs site
```

## Jitsi

meet's Jitsi Meet has no docs site yet; the two things to know:

- **Change Jitsi** (meet): edit `modules/jitsi/files/`. They are the quick-install's own files,
  adopted as they were, so each change is visible in the plan's diff. Secrets
  (`JITSI_JVB_PASSWORD`, `JITSI_FOCUS_PASSWORD`, `JITSI_TURN_SECRET`) are in the server's secret
  store; the first two must match the `jvb` and `focus` accounts in Prosody.
- **Upgrade Jitsi**: bump every version in `vars/host-meet.yaml`'s `jitsi_packages` together; one
  apt transaction installs the set (an apt pin keeps the nightly upgrade off them). Before that,
  check what the new packages want from the configs Buckle owns, because their postinsts edit
  configs on upgrade and Buckle would write the old ones back:
  1. `apt-get download` the new versions on meet; compare the templates they ship
     (`/usr/share/jitsi-meet-prosody/prosody.cfg.lua-jvb.example`,
     `/usr/share/jitsi-meet-web-config/jitsi-meet.example`) with `modules/jitsi/files/`.
     Prosody's site config and the nginx site are those templates filled in for meet (domain,
     `focus`, TURN secret; `"polls"` commented out and the colibri websocket proxy enabled, as
     the postinsts do).
  2. Upgrade an `ubuntu:24.04` amd64 container from the old to the new versions over the rendered
     templates (dummy secrets) and diff the configs afterwards; start Prosody there and check
     its log for module errors, and `nginx -t`.
  3. `buckle plan` on meet with the working tree, then merge.
  The `bridge-available` check fails if jicofo can't see the videobridge afterwards.
