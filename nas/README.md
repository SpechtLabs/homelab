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

The NAS runs DSM's Tailscale package, tagged `tag:nas` (the only tag
allowed to serve `svc:nas`, `svc:stream`, `svc:node-exporter` and `svc:nfs`). What each group
may reach on it is in `tailscale/policy.hujson`, with tests.

The device is `nas-elbschloss` on the tailnet. Clients reach the NAS only
through the Tailscale Services it hosts:

| URL | Backend | Service |
|---|---|---|
| `https://nas.sphinx-map.ts.net` | DSM, `https+insecure://localhost:5001` | `svc:nas` (also tcp:5001 DSM for the mobile apps, tcp:6690 Drive) |
| `https://stream.sphinx-map.ts.net` | Jellyfin, `http://localhost:8096` | `svc:stream` |
| `http://node-exporter.sphinx-map.ts.net:9100` | node-exporter (compose project `o11y`) | `svc:node-exporter` |
| `nfs.sphinx-map.ts.net:/volume1/...` | NFS v4.1, `127.0.0.1:2049` | `svc:nfs` |

NFS goes through `svc:nfs` as v4.1 (one port; v3's portmapper and mountd
can't). tailscaled forwards it from localhost, so DSM sees every client as
`127.0.0.1` on a high port: a shared folder's NFS rule is for `127.0.0.1`
with "Allow connections from non-privileged ports", and the tailnet policy
decides who reaches `svc:nfs`. The forward names `127.0.0.1`, not
`localhost`: that is `::1` here, which the rule doesn't match ("access
denied by server").

tailscaled keeps the serve config in its state file, so it survives reboots
and package updates. Uninstalling the Tailscale package loses it; to set it up
again, on the NAS:

```sh
sudo tailscale serve --service=svc:nas --https=443 https+insecure://localhost:5001
sudo tailscale serve --service=svc:nas --tcp=5001 tcp://localhost:5001
sudo tailscale serve --service=svc:nas --tcp=6690 tcp://localhost:6690
sudo tailscale serve --service=svc:stream --https=443 http://localhost:8096
sudo tailscale serve --service=svc:node-exporter --tcp=9100 tcp://localhost:9100
sudo tailscale serve --service=svc:nfs --tcp=2049 tcp://127.0.0.1:2049
sudo tailscale serve status
```

Every port of a Service's definition has to be served: a host missing one
drops out of the Service. The definitions themselves (Services in the admin
console: `svc:nas` with tcp:443, tcp:5001, tcp:6690; `svc:stream` with
tcp:443; `svc:node-exporter` with tcp:9100; `svc:nfs` with tcp:2049) live
outside this repo; the NAS's advertisements are approved
by `autoApprovers` in the policy.

DSM signs in through tsidp (Control Panel → Domain/LDAP → SSO Client). The
redirect URI `https://nas.sphinx-map.ts.net` has to be listed both there and on
the `synology` client in tsidp's admin UI, spelled the same way (no trailing
slash).

`svc:nas` has no port 80: an explicit `http://nas.sphinx-map.ts.net` gets
nothing, and browsers that go to HTTPS on their own get DSM.
