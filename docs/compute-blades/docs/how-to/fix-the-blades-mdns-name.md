# Fix the blade's mDNS name

Use this when `bladectl discover` shows a blade as `address changed` with a server like `blade-pi3-2.local:8081`, or Buckle's informational `compute-blade-agent: mdns-name` check fails on a blade.

**Before you start:** SSH to `pi@blade-piN`. Restarting the agent runs its fan at 100% for a moment (and the neighbour's, which shares the fan unit).

avahi announces each blade as `<hostname>.local`. When the link drops and comes back, avahi can see its own stale record, take it for another host and rename itself `<hostname>-2.local`, and it keeps that name until it restarts. blade-pi3 did this on 2026-11-24 at 02:46 UTC after a link flap; nothing else on the LAN used the name. The API certificate names `blade-piN` and `blade-piN.local`, not the `-2` name, so bladectl can't use the address discovery reports.

1. Confirm the name avahi uses:

   ```sh
   busctl call org.freedesktop.Avahi / org.freedesktop.Avahi.Server GetHostName
   journalctl -u avahi-daemon --no-pager | grep 'Host name conflict'
   ```

   `s "blade-pi3-2"` and a `Host name conflict, retrying with blade-pi3-2` line.
2. Restart avahi, then the agent, which registers its `_compute-blade._tcp` service through avahi:

   ```sh
   sudo systemctl restart avahi-daemon && sudo systemctl restart compute-blade-agent
   ```

## Check it worked

```sh
busctl call org.freedesktop.Avahi / org.freedesktop.Avahi.Server GetHostName
```

On the blade: `s "blade-pi3"`, and the journal says `Host name is blade-pi3.local`. On the Mac, `bladectl discover --wait 6s` lists the blade as `blade-pi3.local:8081`, `configured`.

## If it didn't

If avahi picks `-2` again right after the restart, another device on the LAN answers for that name. From the Mac, `dns-sd -G v4 blade-pi3.local` lists who answers; find that device and rename it.
