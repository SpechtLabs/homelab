# Known issues

Traps that have bitten this setup, and what in the repo handles each. The background is in [Design](../explanation/design.md).

## AppArmor blocks pmc on Ubuntu

**Where:** any PTP client with `apparmor.service` active; today that's isa (Ubuntu).

**Symptom:** ptp4l runs, but `sudo pmc -u -b 0 'GET PORT_DATA_SET'` returns nothing. chrony's start gate times out after 90 s, `chrony-follow-ptp` can't tell whether ptp4l is SLAVE, and `time-client-metrics` reports `ptp4l_port_slave 0`, which fires `PTP client lost the grandmaster`. Syslog logging from ptp4l fails the same way.

**Cause:** linuxptp's AppArmor profile (`/etc/apparmor.d/usr.sbin.ptp4l`) lacks `attach_disconnected`, and the package's `ptp4l@` unit runs ptp4l in its own mount namespace. Inside that sandbox every client socket is a "disconnected path" to the profile, so it denies them.

**Handled by:** `time-sync` symlinks the profile into `/etc/apparmor.d/disable/` (task `ptp4l-apparmor-disabled`), and task `ptp4l-unconfined` unloads it and restarts ptp4l and chrony if a ptp4l is still confined (`/proc/<pid>/attr/current` starts with `ptp4l `). The systemd sandbox stays. ptp4l logs to stdout (`use_syslog 0`, `verbose 1`) for the same reason. The Pis run without AppArmor.

## The GPS only pulses with a fix

The receiver (u-blox M8, SPG 3.01 standard firmware, no timing mode) emits PPS only while it has a fix, and the antenna's sky view loses it several times a day (best SNR around 28 dB-Hz). ntpsec then follows PTB. `ptp-server` enforces Galileo and the stationary dynamic model through `ubxtool` to hold the fix longer. Real fix: antenna placement.

## Pi kernel 6.12.34 PHCs refuse adjustment

On kernel 6.12.34 the Pis' hardware clocks refused every adjustment ("physical clock is free running"). Every Pi has run 6.12.115 since 2026-11-19 and the nightly upgrades keep it current. Buckle's `os.kernel` fact stayed stale after reboots back then, so no group depends on it.

## A ptp4l started before the link stays FAULTY

The NIC's hardware clock appears only once the link is up, and `fault_reset_interval` doesn't recover a ptp4l that started earlier. Both ptp4l drop-ins (grandmaster and clients) wait for `/sys/class/net/<if>/operstate` to read `up` first.

## chrony started with ptp4l can ignore PTP for good

ptp4l steps the NIC clock from boot time to TAI once it locks; a chrony reading the PHC meanwhile can keep a wild error estimate and never select it (blade-pi4, 2026-11-19: on NTP for 40 min with ptp4l locked at 130 ns). Hence chrony's drop-in waits up to 90 s for SLAVE, and `chrony-follow-ptp` restarts chrony when ptp4l is SLAVE but chrony doesn't follow `PTP`.

## Multicast Delay_Req starves the I219

isa's I219 latches one receive timestamp at a time. With every client sending Delay_Req by multicast, it missed Syncs ("received SYNC without timestamp", RMS ~700 ns instead of ~130). Clients use `hybrid_e2e 1`: Delay_Req by unicast to the grandmaster. isa still shows a ~10 µs outlier every few minutes; Intel AMT shares that NIC.

## Debian has no leap-second zone

PTP runs on TAI and chrony's `tai` option needs a `right/UTC` zone with leap data, which Debian's tzdata no longer ships. TAI-UTC is the constant `time_tai_utc_offset: 37` instead; no leap second is scheduled and they end by 2035.

## The fallback clockAccuracy says "more than 10 s"

`ptp-gm-quality` announces `clockAccuracy 0x31` while timepi is on network time, and its comment calls that ±10 ms. In IEEE 1588's table 0x31 means "greater than 10 s"; 10 ms would be 0x2B. Clients don't act on it (they're `slaveOnly` with a single grandmaster), so it only affects what the dashboard and `pmc` show.

## chronyc needs sudo

chrony listens only on its local socket (`cmdport 0`), which is root's: `chronyc` as `pi` or `cedi` prints `506 Cannot talk to daemon`.
