# Respond to an availability alert

Use this when one of these pages you: `Homelab — NAS (DSM) availability`, `Homelab — Jellyfin
availability` or `Homelab — Home Assistant availability` is burning its error budget fast.

**Before you start:** SSH to isa (`ssh cedi@isa`), where the probes run. For the NAS,
`ssh -J cedi@nyx king@nas.local`. The probes and SLOs are listed in
[Monitoring](../reference/monitoring.md).

1. Is it one service, or every probe? Look at `probe_success{job="blackbox"}` in Grafana
    (datasource `mimir-homelab`). If the Buckle, tsidp and labk3s probes failed at the same
    moment, the collector is the problem, not the NAS or Home Assistant:

    ```sh
    ssh cedi@isa "bash -c 'systemctl is-active alloy; curl -s http://127.0.0.1:12345/-/ready'"
    ```

    Go to the [Observability docs](https://backstage.k8s.specht-labs.de/docs/default/system/observability/)
    from there.

2. Repeat the probe from isa:

    ```sh
    ssh cedi@isa "bash -c 'for u in https://nas.sphinx-map.ts.net/ https://stream.sphinx-map.ts.net/health http://hass.sphinx-map.ts.net:8123/; do printf \"%s \" \$u; curl -s -o /dev/null -w \"%{http_code}\n\" --max-time 8 \$u; done'"
    ```

    `200` for each. A `200` now means it recovered; read the logs below for the cause anyway.

3. Is the device on the tailnet?

    ```sh
    tailscale status | grep -E 'nas-elbschloss|hass-elbschloss'
    ```

    Offline: it's down, rebooting or lost Tailscale. Try the LAN path from isa next.

4. Try the LAN path from isa, which skips Tailscale:

    ```sh
    ssh cedi@isa "bash -c 'curl -sk -o /dev/null -w \"%{http_code}\n\" https://192.168.0.64:5001/; curl -s http://192.168.0.64:8096/health; echo; curl -s -o /dev/null -w \"%{http_code}\n\" http://192.168.0.62:8123/'"
    ```

    DSM `200`, Jellyfin `Healthy`, Home Assistant `200`.

    - LAN works, tailnet doesn't: the Service. For the NAS, check its serve config
      ([Re-create the NAS's Tailscale serve config](recreate-the-nas-tailscale-serve-config.md)).
      For Home Assistant, the Tailscale add-on's `services:` option must serve both tcp:443 and
      tcp:8123; a missing port takes the host out of `svc:hass`.
    - LAN fails too: the service itself. Go on with step 5 or 6.

5. Jellyfin or DSM down on the NAS:

    ```sh
    ssh -J cedi@nyx king@nas.local 'sudo /usr/local/bin/docker ps -a --format "{{.Names}} {{.Status}}"'
    ```

    `jellyfin` should be `Up ... (healthy)`. Restart a stopped project in Container Manager.
    DSM itself not answering on the LAN means the NAS is down or rebooting (a DSM update does
    that); check it in person or in DSM once it's back.

6. Home Assistant down: it isn't managed from this repo. Past causes: on 2026-11-25 `svc:hass`
    returned 400 (Home Assistant's `trusted_proxies`), and later that night an HA OS update
    rebooted the box and it stayed offline. Look at the box, or at the `Home Assistant —
    Diagnostics` dashboard for when it stopped sending.

## Check it worked

The probe in step 2 returns `200` and `probe_success` for that `service` stays at 1. The burn
alert resolves on its own once the rate drops.

## If it didn't

- Who may reach which Service, and debugging grants:
  [Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/).
- The NAS's Tailscale behaviour: [The NAS and Tailscale](../explanation/nas-and-tailscale.md).
