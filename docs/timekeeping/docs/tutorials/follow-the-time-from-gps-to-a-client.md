# Follow the time from GPS to a client

You'll look at every link in the chain once, on the live hosts, so the alerts and how-to guides make sense later. Nothing here changes anything; every command only reads.

**You need:** SSH to `cedi@timepi` and `pi@blade-pi1` (any Pi works the same; the login shell is fish, and every command below works in it). About 15 minutes.

## 1. The receiver

Log in to timepi and ask gpsd for ten of its JSON reports:

```sh
ssh cedi@timepi
gpspipe -w -n 10
```

Look for three classes of line. `TPV` carries the fix: `"mode":3` is a 3D fix, `1` none. `SKY` lists the satellites, `"uSat"` being how many the fix uses (8 of 24 visible when this page was written). `PPS` lines come once a second, one per PPS source gpsd reads, with `clock_nsec` close to `0` or `999999...`: the system clock's reading at the pulse.

!!! note
    `TPV` also carries timepi's position. It's fine in your terminal and in Mimir; don't paste it into git.

## 2. The kernel's PPS

The pulse arrives on GPIO 18, which the `pps-gpio` overlay in `/boot/firmware/config.txt` turns into `/dev/pps0`:

```sh
grep pps /boot/firmware/config.txt
sudo ppstest /dev/pps0
```

`ppstest` prints one `assert` line a second while the receiver has a fix. Press Ctrl-C to stop it. No lines at all means no fix, because this receiver only pulses with one (see [Handle a GPS without a fix](../how-to/handle-a-gps-without-a-fix.md)).

## 3. ntpsec

gpsd numbers each pulse with the second from the NMEA sentences and hands it to ntpsec through shared memory unit 1:

```sh
ntpq -pn
```

You should see `*SHM(1)  .PPS.` at the top, the `*` meaning ntpsec follows it, with an offset of a few microseconds or less (the column is in milliseconds, so `-0.0036` is 3.6 µs). `SHM(0) .GPS.` is the NMEA time; it's never selected because serial NMEA arrives 150-600 ms late and wanders. The three `.PTB.` servers and the pool servers are the fallback.

```sh
ntpq -c rv
```

`stratum=1` and `refid=PPS` confirm it.

## 4. From the system clock to the network card

phc2sys copies the system clock to eth0's hardware clock (`/dev/ptp0`), and ptp4l serves that clock on the LAN:

```sh
systemctl status phc2sys-eth0 ptp4l@eth0 --no-pager
sudo pmc -u -b 0 'GET PORT_DATA_SET' 'GET GRANDMASTER_SETTINGS_NP'
```

`portState MASTER` means timepi is the grandmaster. `clockClass 6` with `timeSource 0x20` says "locked to GPS"; it changes to 52 when ntpsec falls back to network time and to 248 with nothing selected. `ptp-gm-quality.timer` keeps that current every 15 s.

Log out of timepi.

## 5. A PTP client

```sh
ssh pi@blade-pi1
sudo /var/lib/buckle/facts.d/ptp
```

That's the fact that put this blade in the `ptp-client` group: `"lan":true` (timepi is on-link), `"hardware":true` (eth0 timestamps in hardware and has PHC 0).

```sh
sudo pmc -u -b 0 'GET PORT_DATA_SET' 'GET TIME_STATUS_NP'
```

`portState SLAVE`, `gmPresent true`, and `master_offset` in nanoseconds (single digits on a quiet LAN). ptp4l here only steers the blade's own hardware clock.

## 6. chrony

chrony reads that hardware clock and steers the system clock from it. Its socket is root's only, so every `chronyc` needs `sudo`:

```sh
sudo chronyc -n sources
sudo chronyc -n tracking
```

The line `#* PTP` is the hardware clock (`#` a reference clock, `*` selected), with an error bound of some tens of nanoseconds. `^- 192.168.0.109` is timepi over NTP, kept as the fallback. In `tracking`, `Reference ID : 50545000 (PTP)` and `Leap status : Normal`.

On a Pi 4 worker (`pi@clusterpi-worker1`) the same commands show `^* 192.168.0.109` selected instead and a system offset of a few microseconds: that's an NTP client.

## 7. The same thing in Grafana

Open the [Time Server dashboard](https://spechtlabs.grafana.net/d/stratum1) (folder Infrastructure). The top row, **Now**, has what you just read by hand: what disciplines timepi, PPS offset, satellites used, PTP port and clock class. The **Fleet clients** row shows every host's offset and its source.

You've now seen each piece the alerts watch. Next: [Check a host's time sync](../how-to/check-a-hosts-time-sync.md) is the short version of steps 5-6 for any host, and [Design](../explanation/design.md) says why the chain looks like this.
