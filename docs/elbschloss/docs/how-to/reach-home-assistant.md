# Reach Home Assistant

Use this to open Home Assistant at home, call its API, or give someone access.

**Before you start:** you're in `group:hass-users` or `group:admins` on the tailnet, or on the
home LAN. Addresses are in [Home Assistant](../reference/home-assistant.md).

1. Open the web UI over the tailnet: `https://hass.sphinx-map.ts.net`. Plain HTTP works too, on
   `http://hass.sphinx-map.ts.net:8123`. Both are `svc:hass`, served by Home Assistant's
   Tailscale add-on.

2. On the home LAN without Tailscale, use `http://192.168.0.62:8123`.

3. For the REST API, create a long-lived access token in Home Assistant (your user profile),
   then:

    ```sh
    curl -s -H "Authorization: Bearer $HASS_TOKEN" https://hass.sphinx-map.ts.net/api/
    ```

    Home Assistant answers with a short JSON message that the API is running. The WebSocket API
    is `/api/websocket`, the Prometheus metrics `/api/prometheus`.

4. To give someone access, add them to `group:hass-users`. Groups are Backstage Groups in
   SpechtLabs/backstage_resources, and the grant follows from the catalog; see the
   [Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/). They
   still need a Home Assistant user of their own.

5. Home Assistant in Schiltach is a different box: `http://hass-schiltach.sphinx-map.ts.net:8123`,
   tailnet only; see the [Schiltach docs](https://backstage.k8s.specht-labs.de/docs/default/system/schiltach/).

## Check it worked

```sh
curl -s -o /dev/null -w "%{http_code}\n" https://hass.sphinx-map.ts.net/
```

`200`. That's the same URL family the availability probe on isa uses
(`http://hass.sphinx-map.ts.net:8123/`).

## If it didn't

- `hass.elbschloss.xyz` doesn't answer, and won't: the Nginx Proxy Manager behind it is gone.
  Use the tailnet or LAN address.
- `400 Bad Request` over `svc:hass`: Home Assistant rejects the proxy; its `trusted_proxies`
  setting has to allow the add-on (seen on 2026-11-25).
- Timeouts: `tailscale status | grep hass-elbschloss`. Offline means the box or its add-on is
  down. Online but no answer: the add-on's `services:` option must serve both tcp:443 and
  tcp:8123, or the host drops out of `svc:hass`.
- More steps: [Respond to an availability alert](respond-to-an-availability-alert.md).
