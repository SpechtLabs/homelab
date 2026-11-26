# Design

The goal is the best time each host's hardware allows, kept that way without hand work. That ruled out the old setup, where systemd-timesyncd polled every 34 minutes and left the Pis 100-700 µs off timepi. Since 2026-11-19 every host runs chrony; the ones whose network card can timestamp in hardware also run PTP.

## timepi: ntpsec, with the GPS in charge

gpsd reads two things from the HAT: NMEA sentences over the UART at 9600 baud, which say which second it is, and the PPS edge on GPIO 18, which says exactly when that second starts. On its own NMEA is useless for timing (it arrives 150-600 ms late and wanders with the sentence load); the PPS on its own doesn't know which second it marks. gpsd puts the two together and hands ntpsec numbered pulses through shared memory segment 1, and ntpsec disciplines the system clock to them with ~0.4-2 µs jitter.

timepi runs ntpsec, which it already ran before Buckle took over; chrony conflicts with it and was never installed there. What matters more is the fallback order. PTB's three stratum 1 servers in Braunschweig come before the pool's random stratum 2s, so when the GPS drops its fix (several times a day, see [Known issues](../reference/known-issues.md#the-gps-only-pulses-with-a-fix)) timepi lands on Germany's legal time at ~1 ms.

## From the system clock to the wire

PTP needs the time in the network card's own hardware clock (PHC), because that's what stamps the packets. On timepi the chain is GPS → ntpsec → system clock → phc2sys → eth0's PHC → ptp4l. phc2sys copies the system clock into the PHC (`-s CLOCK_REALTIME -c eth0`); ptp4l serves that PHC as grandmaster. That's one hop more than feeding the PPS into the PHC directly, and in exchange ntpsec stays the single owner of "what time is it", fallbacks included.

The grandmaster also tells clients how good its clock is. A static clockClass 6 would claim GPS lock while timepi is really on PTB, so `ptp-gm-quality` re-announces every 15 s: 6 on PPS, 52 on network time, 248 on nothing. Clients don't change behaviour (they have no other grandmaster), but the state shows up in `pmc` and on the dashboard.

## Clients: ptp4l steers the PHC, chrony steers the system clock

On a PTP client, ptp4l locks the NIC's PHC to timepi and stops there; there's no phc2sys. chrony reads the PHC as a reference clock (`refclock PHC ... prefer`) and disciplines the system clock from it, with timepi's NTP and the public pool as further sources. That split gives one daemon, chrony, ownership of the system clock on every host, so NTP and PTP hosts look the same to the metrics, the alerts and Buckle's health checks, and a PTP failure degrades to NTP by itself instead of leaving the clock free-running.

The PHC runs on TAI, which is why chrony's refclock has `offset -37`.

Ordering matters at boot. ptp4l steps the PHC from boot time to TAI when it first locks, and a chrony that was already reading the PHC can keep a bogus error estimate for that source forever. chrony therefore starts after ptp4l reaches SLAVE (90 s at most, so a broken PTP can't hold up NTP), and a Buckle task restarts chrony if it still isn't following PTP while ptp4l is locked.

## hybrid_e2e

With plain E2E every client multicasts its Delay_Req, so every other client's NIC receives them too. isa's I219 can latch only one receive timestamp at a time; the others' Delay_Reqs took the latch and it missed Syncs. With `hybrid_e2e 1` clients send Delay_Req by unicast to the grandmaster, which still answers Syncs and Delay_Resps by multicast. isa went from ~700 ns RMS to ~130 ns.

## Who gets what: facts, not host lists

No file lists the PTP hosts. `ptp-facts` asks each host's kernel two questions, whether timepi is on-link and whether the NIC on that route timestamps in hardware with a clock of its own (`ethtool -T`), and `buckle.yaml` builds `ntp-client` and `ptp-client` from the answer. `ptp-grandmaster` comes from a `pps-gpio` node in the device tree. The reason is a real miss: when isa replaced the NUC on 2026-11-23 it slotted into the NUC's id-based place and stayed on NTP until 2026-11-24, even though its I219 could do PTP. A new or replaced host now gets the right role from its hardware.

## Why time stays off the tailnet

Clients reach timepi at `192.168.0.109`, not `timepi.sphinx-map.ts.net`. The tailnet name would make time wait for Tailscale to come up first, so timepi keeps a fixed DHCP lease instead. PTP is LAN multicast (`udp_ttl 1`) anyway.
