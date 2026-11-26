# Handle a GPS without a fix

Use this when `timepi — GPS PPS lost` fires, the Time Server dashboard's **Disciplined by** panel shows something other than PPS, or `ntpq -pn` on timepi has its `*` on a `.PTB.` line.

**Before you start:** SSH to `cedi@timepi`. Nothing here is urgent: timepi keeps serving network time (~1 ms) and the clients stay in sync with it. The receiver, a u-blox M8 with standard firmware, only emits PPS while it has a fix, and the antenna's poor sky view loses the fix several times a day.

1. Confirm what ntpsec follows:

   ```sh
   ntpq -pn
   ```

   `SHM(1) .PPS.` without a `*` (often with a falling `reach`) and `*` on a PTB server: no PPS.
2. Look at the fix and the satellites:

   ```sh
   gpspipe -w -n 10
   ```

   In the `TPV` lines `"mode":1` is no fix, `2` a 2D and `3` a 3D fix. The `SKY` line's `"uSat"` is the number of satellites in use. No `PPS` lines appear without a fix.
3. Check the antenna and jamming:

   ```sh
   ubxtool -P 18 -p MON-HW localhost:2947:/dev/ttyAMA0 | grep -E 'aStatus|jamInd'
   ```

   `aStatus 2` is OK (3 short circuit, 4 open, i.e. no antenna). `jamInd` runs 0-255; it read 23 on 2026-11-23 and 52 on 2026-11-26, and only a value near the top means interference.
4. Check the receiver still has the settings Buckle enforces (they live in its RAM and a power loss drops them):

   ```sh
   ubxtool -P 18 -p CFG-GNSS localhost:2947:/dev/ttyAMA0 | grep 'Galileo E1 enabled'
   ubxtool -P 18 -p CFG-NAV5 localhost:2947:/dev/ttyAMA0 | grep -o 'dynModel [0-9]*'
   ```

   You want the Galileo line and `dynModel 2` (stationary). If either is missing, Buckle's `gps-galileo` and `gps-stationary` tasks in [`modules/ptp-server`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/module.yaml) set them again on the next drift pass (every 15 min) or rollout.
5. With the antenna OK and the settings in place, wait. The fix comes back when enough satellites are in view; the dashboard's **GPS receiver** row (Sky, Signal per satellite, Satellites) shows how far off that is. A best SNR around 28 dB-Hz is typical here, which is weak.

## Check it worked

`ntpq -pn` shows `*SHM(1) .PPS.` again and `sudo pmc -u -b 0 'GET GRANDMASTER_SETTINGS_NP' | grep clockClass` says `6`. `ptp-gm-quality` logs each change:

```sh
journalctl -u ptp-gm-quality --since -1d --no-pager | grep 'grandmaster now'
```

## If it didn't

- Fix for hours with `aStatus 2`: the sky view is the limit. The real fix is a better antenna position; no software setting gets around a receiver that pulses only with a fix.
- `aStatus 3` or `4`: check the antenna cable and connector.
- No output at all from `gpspipe`: `systemctl status gpsd --no-pager`, and check `/etc/default/gpsd` lists `/dev/ttyAMA0 /dev/pps0` (Buckle writes it).
- PPS lines but ntpsec still not on PPS after 5 minutes: `systemctl status ntpsec --no-pager`; ntpsec polls the SHM refclocks every 16 s and needs a few good samples.

The timepi stratum-1 SLO (80% over 28 days) tracks how much of the time the GPS wins; see [Alerts, SLOs and dashboards](../reference/alerts-slos-and-dashboards.md).
