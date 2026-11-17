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
