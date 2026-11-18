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

The NAS runs DSM's Tailscale package, tagged `tag:core-infra` only (not
`tag:core-services`, which would open every port to every member). What each
group may reach on it is in `tailscale/policy.hujson`, with tests.

Two `tailscale serve` handlers put DSM and Jellyfin on tailnet names with
Tailscale certificates:

| URL | Backend | Kind |
|---|---|---|
| `https://nas.sphinx-map.ts.net` | DSM, `https+insecure://localhost:5001` | serve on the node's own name |
| `https://stream.sphinx-map.ts.net` | Jellyfin, `http://localhost:8096` | Tailscale Service `svc:stream` |

tailscaled keeps both in its state file, so they survive reboots and package
updates. Uninstalling the Tailscale package loses them; to set them up again,
on the NAS:

```sh
sudo tailscale serve --bg --https=443 https+insecure://localhost:5001
sudo tailscale serve --bg --service=svc:stream --https=443 http://localhost:8096
sudo tailscale serve status   # both should be listed
```

`svc:stream` also has to exist in the admin console (Services, port `tcp:443`);
the NAS's advertisement is then approved by `autoApprovers` in the policy.
That definition is the one piece that lives outside this repo.

DSM signs in through tsidp (Control Panel → Domain/LDAP → SSO Client). The
redirect URI `https://nas.sphinx-map.ts.net` has to be listed both there and on
the `synology` client in tsidp's admin UI, spelled the same way (no trailing
slash).

Serve only handles 443. Browsers go to HTTPS on their own and get DSM, but
an explicit `http://nas.sphinx-map.ts.net` (port 80) reaches Nginx Proxy
Manager's default page, because NPM binds port 80 on every interface.
