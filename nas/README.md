# Synology NAS

The NAS runs DSM, which Buckle can't manage (no apt, and Buckle only pulls
container images, it doesn't run them). These compose projects are versioned
here and deployed through DSM's Container Manager, one Project per directory:

| Project | Directory on the NAS | Containers |
|---|---|---|
| media | `/volume1/docker/media` | nginx-proxy-manager, jellyfin |
| o11y | `/volume1/docker/o11y` | node-exporter, snmp-exporter, cadvisor |

To update: copy the directory to the NAS (`rsync -a nas/o11y/ nas:/volume1/docker/o11y/`)
and rebuild the project in Container Manager. The NUC's Alloy scrapes the o11y
exporters (`vars/group-o11y-collector.yaml`).

The SNMP exporter config comes from
[wozniakpawel/synology-grafana-prometheus-overly-comprehensive-dashboard](https://github.com/wozniakpawel/synology-grafana-prometheus-overly-comprehensive-dashboard).

## Tailscale

The NAS runs DSM's Tailscale package, tagged `tag:core-infra` and `tag:nas`
(the only tag allowed to serve `svc:nas` and `svc:stream`). What each group
may reach on it is in `tailscale/policy.hujson`, with tests.

The device is `nas-elbschloss` on the tailnet. Two Tailscale Services, which
it hosts, put DSM and Jellyfin on tailnet names with Tailscale certificates:

| URL | Backend | Service |
|---|---|---|
| `https://nas.sphinx-map.ts.net` | DSM, `https+insecure://localhost:5001` | `svc:nas` (also tcp:5001 DSM for the mobile apps, tcp:6690 Drive, tcp:445 SMB) |
| `https://stream.sphinx-map.ts.net` | Jellyfin, `http://localhost:8096` | `svc:stream` |

NFS can't go through a Service (NFS v3's portmapper and mountd), so NFS
clients mount from the device's own name, `nas-elbschloss.sphinx-map.ts.net`.

tailscaled keeps the serve config in its state file, so it survives reboots
and package updates. Uninstalling the Tailscale package loses it; to set it up
again, on the NAS:

```sh
sudo tailscale serve --service=svc:nas --https=443 https+insecure://localhost:5001
sudo tailscale serve --service=svc:nas --tcp=5001 tcp://localhost:5001
sudo tailscale serve --service=svc:nas --tcp=6690 tcp://localhost:6690
sudo tailscale serve --service=svc:nas --tcp=445 tcp://localhost:445
sudo tailscale serve --service=svc:stream --https=443 http://localhost:8096
sudo tailscale serve status
```

Every port of a Service's definition has to be served: a host missing one
drops out of the Service. The definitions themselves (Services in the admin
console: `svc:nas` with tcp:443, tcp:5001, tcp:6690, tcp:445; `svc:stream`
with tcp:443) live outside this repo; the NAS's advertisements are approved
by `autoApprovers` in the policy.

DSM signs in through tsidp (Control Panel → Domain/LDAP → SSO Client). The
redirect URI `https://nas.sphinx-map.ts.net` has to be listed both there and on
the `synology` client in tsidp's admin UI, spelled the same way (no trailing
slash).

`svc:nas` has no port 80: an explicit `http://nas.sphinx-map.ts.net` gets
nothing, and browsers that go to HTTPS on their own get DSM.
