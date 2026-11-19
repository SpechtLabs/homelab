#!/usr/bin/python3 -I
# Managed by Buckle. Local changes will be overwritten.
"""Prometheus textfiles for a GPS-disciplined time server.

Reads, never writes, what the time daemons already know and leaves one .prom
file per source in the node_exporter textfile directory (Alloy's embedded
node_exporter picks them up):

  ntpsec.prom  system variables, every association (refclocks and upstream
               servers), packet counters, the MRU list's clients
  gpsd.prom    fix, DOP, satellites (per satellite SNR), PPS and NMEA timing
               as gpsd sees them over a few seconds of its JSON stream
  pps.prom     the kernel's PPS assert counter and timestamp (sysfs)
  ptp.prom     ptp4l's data sets over its management socket (pmc), and
               phc2sys's offset/frequency/delay from its journal lines

Every query is read-only with a short timeout; a source that fails writes
only `time_metrics_up{source="..."} 0`, so stale numbers disappear.
"""

import argparse
import calendar
import ipaddress
import json
import math
import os
import re
import socket
import subprocess
import sys
import threading
import time

NTP_EPOCH_OFFSET = 2208988800  # 1900 -> 1970


def esc(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class Out:
    """Collects samples, grouped by metric so HELP/TYPE are written once."""

    def __init__(self):
        self.metrics = {}

    def add(self, name, value, labels=None, help_="", type_="gauge"):
        if value is None:
            return
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        if math.isnan(value):
            return
        m = self.metrics.setdefault(name, {"help": help_, "type": type_, "samples": []})
        m["samples"].append((labels or {}, value))

    def render(self):
        lines = []
        for name, m in self.metrics.items():
            if m["help"]:
                lines.append("# HELP %s %s" % (name, m["help"]))
            lines.append("# TYPE %s %s" % (name, m["type"]))
            for labels, value in m["samples"]:
                lbl = ",".join('%s="%s"' % (k, esc(v)) for k, v in labels.items())
                lines.append("%s%s %s" % (name, "{%s}" % lbl if lbl else "", repr(round(value, 12))))
        return "\n".join(lines) + "\n"


def write_textfile(directory, name, out):
    path = os.path.join(directory, name + ".prom")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(out.render())
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def run(source, directory, fn, *args):
    out = Out()
    start = time.monotonic()
    ok = 1
    try:
        fn(out, *args)
    except Exception as e:  # report, keep the other sources going
        print("%s: %s: %s" % (source, type(e).__name__, e), file=sys.stderr)
        out = Out()
        ok = 0
    out.add("time_metrics_up", ok, {"source": source},
            "1 if the last read of this source succeeded.")
    out.add("time_metrics_duration_seconds", time.monotonic() - start, {"source": source},
            "How long reading this source took.")
    out.add("time_metrics_last_run_timestamp_seconds", time.time(), {"source": source},
            "When this source was last read.")
    write_textfile(directory, source, out)


# ── ntpsec ───────────────────────────────────────────────────────────────────

# Peer status word, selection field (bits 8-10); see ntpq(1) "tally".
NTP_SELECT = ["reject", "falsetick", "excess", "outlier", "candidate", "backup", "sys_peer", "pps_peer"]

# Counters from `ntpq -c sysstats/iostats/monstats`: (variable, metric, help).
NTP_COUNTERS = [
    ("ss_received", "ntpsec_packets_received_total", "NTP packets received (sysstats)."),
    ("ss_processed", "ntpsec_packets_processed_total", "NTP packets processed for time (sysstats)."),
    ("ss_thisver", "ntpsec_packets_current_version_total", "Packets of the current NTP version."),
    ("ss_oldver", "ntpsec_packets_older_version_total", "Packets of an older NTP version."),
    ("ss_badformat", "ntpsec_packets_bad_format_total", "Packets with a bad length or format."),
    ("ss_badauth", "ntpsec_packets_auth_failed_total", "Packets that failed authentication."),
    ("ss_declined", "ntpsec_packets_declined_total", "Packets declined."),
    ("ss_restricted", "ntpsec_packets_restricted_total", "Packets dropped by restrict lines."),
    ("ss_limited", "ntpsec_packets_rate_limited_total", "Packets rate limited."),
    ("ss_kodsent", "ntpsec_kod_sent_total", "Kiss-o'-death responses sent."),
    ("ss_numctlreq", "ntpsec_control_requests_total", "Mode 6 control requests (ntpq, this collector)."),
    ("io_received", "ntpsec_io_received_packets_total", "Packets received on all interfaces (iostats)."),
    ("io_sent", "ntpsec_io_sent_packets_total", "Packets sent (iostats)."),
    ("io_sendfailed", "ntpsec_io_send_failures_total", "Packet send failures (iostats)."),
    ("io_dropped", "ntpsec_io_dropped_packets_total", "Packets dropped (iostats)."),
    ("io_ignored", "ntpsec_io_ignored_packets_total", "Packets ignored (iostats)."),
    ("mru_new", "ntpsec_mru_new_total", "Addresses added to the MRU list."),
]
NTP_GAUGES = [
    ("ss_uptime", "ntpsec_stats_reset_seconds", "Seconds since ntpd's statistics were reset (its uptime).", 1),
    ("mru_depth", "ntpsec_mru_entries", "Addresses in the MRU list.", 1),
    ("mru_mem", "ntpsec_mru_memory_bytes", "Memory used by the MRU list.", 1024),
    ("mru_maxmem", "ntpsec_mru_memory_limit_bytes", "MRU list memory limit.", 1024),
    ("mru_oldest_age", "ntpsec_mru_oldest_age_seconds", "Age of the oldest MRU entry.", 1),
]


def lfp_to_unix(text):
    """ntpd's l_fp text ("0xeea97a33.f9a5ca30") to Unix seconds (NTP era 0)."""
    try:
        sec, frac = str(text).split(".")
        s = int(sec, 16)
        if s == 0:
            return None
        return s - NTP_EPOCH_OFFSET + int(frac, 16) / 2**32
    except (ValueError, AttributeError):
        return None


def iso_to_unix(text):
    try:
        return calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%MZ"))
    except (ValueError, TypeError):
        return None


def reverse_names(addresses, timeout):
    """Reverse DNS for the private client addresses, all at once, bounded."""
    names = {}

    def lookup(a):
        try:
            names[a] = socket.gethostbyaddr(a)[0].split(".")[0]
        except OSError:
            pass

    threads = [threading.Thread(target=lookup, args=(a,), daemon=True) for a in addresses]
    for t in threads:
        t.start()
    deadline = time.monotonic() + timeout
    for t in threads:
        t.join(max(0.0, deadline - time.monotonic()))
    return dict(names)


def collect_ntpsec(out, timeout):
    import ntp.packet  # ntpsec's own library (what ntpq uses)

    s = ntp.packet.ControlSession()
    s.primary_timeout = int(timeout * 1000)
    s.secondary_timeout = int(timeout * 1000)
    if not s.openhost("127.0.0.1"):
        raise RuntimeError("cannot open ntpd's control socket")

    def v(d, key):
        return d[key][0] if key in d else None

    sysvars = s.readvar(0, raw=True)
    status = s.rstatus
    out.add("ntpsec_stratum", v(sysvars, "stratum"), help_="System stratum (1: synchronised to a reference clock).")
    out.add("ntpsec_leap", v(sysvars, "leap"), help_="Leap indicator: 0 none, 1 insert, 2 delete, 3 unsynchronised.")
    out.add("ntpsec_sync_source", (status >> 8) & 0x3F, help_="Clock source from the system status word (4: uhf_radio, the refclock).")
    out.add("ntpsec_precision_seconds", 2.0 ** v(sysvars, "precision"), help_="Clock read precision.")
    ms = 1e-3
    for key, metric, help_ in [
        ("rootdelay", "ntpsec_root_delay_seconds", "Round-trip delay to the primary reference."),
        ("rootdisp", "ntpsec_root_dispersion_seconds", "Dispersion to the primary reference."),
        ("offset", "ntpsec_offset_seconds", "Combined offset of the system clock to the selected sources."),
        ("sys_jitter", "ntpsec_system_jitter_seconds", "Jitter of the selected sources (combine algorithm)."),
        ("clk_jitter", "ntpsec_clock_jitter_seconds", "Jitter of the system clock's offsets."),
    ]:
        val = v(sysvars, key)
        out.add(metric, None if val is None else val * ms, help_=help_)
    rd, rdisp = v(sysvars, "rootdelay"), v(sysvars, "rootdisp")
    if rd is not None and rdisp is not None:
        out.add("ntpsec_root_distance_seconds", (rd / 2 + rdisp) * ms,
                help_="Root distance (delay/2 + dispersion): the bound clients see on this server's error.")
    out.add("ntpsec_frequency_ppm", v(sysvars, "frequency"), help_="Frequency correction of the system clock.")
    out.add("ntpsec_clock_wander_ppm", v(sysvars, "clk_wander"), help_="Frequency stability (RMS of frequency changes).")
    out.add("ntpsec_time_constant", v(sysvars, "tc"), help_="Clock discipline time constant (log2 s).")
    out.add("ntpsec_tai_offset_seconds", v(sysvars, "tai"), help_="TAI-UTC offset from the leap file.")
    out.add("ntpsec_reference_timestamp_seconds", lfp_to_unix(v(sysvars, "reftime")),
            help_="When the system clock was last updated from a source.")
    out.add("ntpsec_leapfile_expiry_timestamp_seconds", iso_to_unix(v(sysvars, "expire")),
            help_="When the leap second file expires.")
    out.add("ntpsec_last_leap_timestamp_seconds", iso_to_unix(v(sysvars, "leapsec")),
            help_="The last leap second in the leap file.")
    out.add("ntpsec_build_info", 1, {"version": v(sysvars, "version") or ""}, help_="ntpd version.")

    now = time.time()
    sys_peer = None
    for p in s.readstat():
        pv = s.readvar(p.associd, raw=True)
        refid = v(pv, "refid") or ""
        src = v(pv, "srcadr") or ""
        if refid == "POOL":  # pool prototypes: they only spawn servers
            continue
        if src.startswith("127.127."):
            kind, peer = "refclock", refid      # PPS, GPS (fudge refid)
        else:
            kind, peer = "server", src
        lbl = {"peer": peer, "kind": kind}
        sel = (p.status >> 8) & 0x7
        reach = v(pv, "reach") or 0
        out.add("ntpsec_peer_selection", sel, lbl,
                "Peer selection: 0 reject, 1 falsetick, 2 excess, 3 outlier, 4 candidate, 5 backup, 6 sys.peer, 7 pps.peer.")
        out.add("ntpsec_peer_reach", reach, lbl, "Reach register (last 8 polls, 255: all answered).")
        out.add("ntpsec_peer_reach_ratio", bin(int(reach)).count("1") / 8.0, lbl, "Share of the last 8 polls answered.")
        out.add("ntpsec_peer_stratum", v(pv, "stratum"), lbl, "Peer stratum.")
        hpoll = v(pv, "hpoll")
        out.add("ntpsec_peer_poll_seconds", None if hpoll is None else 2.0 ** hpoll, lbl, "Poll interval.")
        for key, metric, help_ in [
            ("offset", "ntpsec_peer_offset_seconds", "Offset of the peer to the system clock."),
            ("delay", "ntpsec_peer_delay_seconds", "Round-trip delay to the peer."),
            ("jitter", "ntpsec_peer_jitter_seconds", "Peer jitter."),
            ("dispersion", "ntpsec_peer_dispersion_seconds", "Peer dispersion."),
            ("rootdelay", "ntpsec_peer_root_delay_seconds", "Peer's root delay."),
            ("rootdisp", "ntpsec_peer_root_dispersion_seconds", "Peer's root dispersion."),
        ]:
            val = v(pv, key)
            out.add(metric, None if val is None else val * ms, lbl, help_)
        rec = lfp_to_unix(v(pv, "rec"))
        out.add("ntpsec_peer_last_receive_age_seconds", None if rec is None else max(0.0, now - rec), lbl,
                "Seconds since the last sample from the peer.")
        out.add("ntpsec_peer_info", 1, dict(lbl, refid=refid, address=src),
                "Peer reference ID and address.")
        if sel == 6:
            sys_peer = peer
    out.add("ntpsec_sys_peer_info", 1, {"peer": sys_peer or "none"}, help_="The system peer.")

    counters = s.readvar(0, [c[0] for c in NTP_COUNTERS] + [g[0] for g in NTP_GAUGES], raw=True)
    for key, metric, help_ in NTP_COUNTERS:
        out.add(metric, v(counters, key), help_=help_, type_="counter")
    for key, metric, help_, scale in NTP_GAUGES:
        val = v(counters, key)
        out.add(metric, None if val is None else val * scale, help_=help_)

    # The MRU list: who asked for time. Mode 3 is a client; 4 (server
    # replies) are our own upstreams, 6 control queries like this one.
    mru = s.mrulist()
    clients = {}
    # timesyncd polls every 34 min once settled: an hour sees every client.
    windows = {"1h": 3600, "24h": 86400}
    other = {w: 0 for w in windows}
    for e in mru.entries:
        if e.mv is None or (e.mv & 0x7) != 3:
            continue
        addr = e.addr[1:e.addr.find("]")] if e.addr.startswith("[") else e.addr.rsplit(":", 1)[0]
        last = lfp_to_unix(e.last)
        if last is None:
            continue
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
        private = ip.is_private or ip in ipaddress.ip_network("100.64.0.0/10")
        if private and ip.version == 4:
            prev = clients.get(addr)
            if prev is None or last > prev[0]:
                clients[addr] = (last, e.ct, lfp_to_unix(e.first))
        else:
            for w, secs in windows.items():
                if now - last <= secs:
                    other[w] += 1
    names = reverse_names(list(clients), timeout=2.0)
    for w, secs in windows.items():
        lan = sum(1 for last, _, _ in clients.values() if now - last <= secs)
        out.add("ntpsec_clients", lan, {"scope": "lan", "window": w},
                "Distinct client addresses that sent a request within the window (MRU list).")
        out.add("ntpsec_clients", other[w], {"scope": "other", "window": w})
    for addr, (last, count, first) in sorted(clients.items()):
        lbl = {"client": names.get(addr, addr), "address": addr}
        out.add("ntpsec_client_last_request_timestamp_seconds", last, lbl, "When the client last asked for time.")
        out.add("ntpsec_client_requests", count, lbl, "Requests from the client since its MRU entry was created.")
        if first and count > 1:
            out.add("ntpsec_client_mean_interval_seconds", (last - first) / (count - 1), lbl,
                    "Average interval between the client's requests.")


# ── gpsd ─────────────────────────────────────────────────────────────────────

GNSS = {0: "GPS", 1: "SBAS", 2: "Galileo", 3: "BeiDou", 4: "IMES", 5: "QZSS", 6: "GLONASS", 7: "NavIC"}


def collect_gpsd(out, window, pps_device):
    sock = socket.create_connection(("127.0.0.1", 2947), timeout=2)
    try:
        sock.sendall(b'?WATCH={"enable":true,"json":true,"pps":true,"timing":true};\n')
        buf = b""
        tpv = sky = devices = None
        pps, toff = [], []
        deadline = time.monotonic() + window
        while time.monotonic() < deadline:
            sock.settimeout(max(0.05, deadline - time.monotonic()))
            try:
                data = sock.recv(65536)
            except socket.timeout:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                cls = msg.get("class")
                if cls == "TPV":
                    tpv = msg
                elif cls == "SKY" and msg.get("satellites") is not None:
                    sky = msg
                elif cls == "DEVICES":
                    devices = msg.get("devices", [])
                elif cls == "PPS" and msg.get("device") == pps_device:
                    pps.append(msg)  # gpsd repeats each pulse for the serial device
                elif cls == "TOFF" and msg.get("device") != pps_device:
                    toff.append(msg)
            # Enough once we have a fix report, a sky view and two pulses.
            if tpv and sky and len(pps) >= 2 and time.monotonic() > deadline - window / 2:
                break
    finally:
        sock.close()

    if devices is None:
        raise RuntimeError("no DEVICES from gpsd")
    for d in devices:
        out.add("gpsd_device_info", 1, {"path": d.get("path", ""), "driver": d.get("driver", ""),
                                        "subtype": d.get("subtype", "")}, "Devices gpsd reads.")
        if d.get("bps"):
            out.add("gpsd_device_baud", d["bps"], {"path": d.get("path", "")}, "Serial speed.")
            out.add("gpsd_device_cycle_seconds", d.get("cycle"), {"path": d.get("path", "")}, "Report cycle.")

    out.add("gpsd_tpv_seen", 1 if tpv else 0, help_="1 if gpsd reported a fix (TPV) during the sample.")
    if tpv:
        out.add("gpsd_fix_mode", tpv.get("mode", 0), help_="Fix: 0 unknown, 1 no fix, 2 2D, 3 3D.")
        out.add("gpsd_status", tpv.get("status", 1), help_="Fix status: 1 GPS, 2 DGPS, ... (absent: 1).")
        out.add("gpsd_time_error_seconds", tpv.get("ept"), help_="Estimated time error (ept).")
        for key, axis in [("eph", "horizontal"), ("epv", "vertical"), ("epx", "longitude"),
                          ("epy", "latitude"), ("sep", "spherical")]:
            out.add("gpsd_position_error_meters", tpv.get(key), {"axis": axis},
                    "Estimated position error (95%).")
        out.add("gpsd_leap_seconds", tpv.get("leapseconds"), help_="GPS-UTC leap seconds the receiver reports.")
        out.add("gpsd_satellites_used_tpv", tpv.get("sats"), help_="Satellites used, per TPV (ublox).")
        if tpv.get("time"):
            out.add("gpsd_fix_timestamp_seconds", iso_ms_to_unix(tpv["time"]), help_="Time of the last fix.")

    out.add("gpsd_sky_seen", 1 if sky else 0, help_="1 if gpsd reported a sky view (SKY) during the sample.")
    if sky:
        for key in ["hdop", "vdop", "pdop", "gdop", "tdop", "xdop", "ydop"]:
            out.add("gpsd_dop", sky.get(key), {"kind": key[0]}, "Dilution of precision.")
        sats = sky.get("satellites") or []
        out.add("gpsd_satellites_visible", sky.get("nSat", len(sats)), help_="Satellites in view.")
        out.add("gpsd_satellites_used", sky.get("uSat", sum(1 for x in sats if x.get("used"))), help_="Satellites used in the fix.")
        per = {}
        for x in sats:
            gnss = GNSS.get(x.get("gnssid"), "PRN") if "gnssid" in x else "PRN"
            svid = x.get("svid", x.get("PRN"))
            lbl = {"constellation": gnss, "svid": str(svid), "prn": str(x.get("PRN"))}
            ss = x.get("ss")
            out.add("gpsd_satellite_snr_dbhz", ss, lbl, "Signal strength (C/N0).")
            out.add("gpsd_satellite_elevation_degrees", x.get("el"), lbl, "Elevation.")
            out.add("gpsd_satellite_azimuth_degrees", x.get("az"), lbl, "Azimuth.")
            out.add("gpsd_satellite_used", 1 if x.get("used") else 0, lbl, "1 if used in the fix.")
            c = per.setdefault(gnss, {"visible": 0, "tracked": 0, "used": 0})
            c["visible"] += 1
            if ss and ss > 0:
                c["tracked"] += 1
            if x.get("used"):
                c["used"] += 1
        for gnss, c in per.items():
            for state, n in c.items():
                out.add("gpsd_constellation_satellites", n, {"constellation": gnss, "state": state},
                        "Satellites per constellation: visible, tracked (signal > 0), used.")

    def offsets(msgs):
        return [(m["clock_sec"] - m["real_sec"]) + (m["clock_nsec"] - m["real_nsec"]) * 1e-9 for m in msgs]

    out.add("gpsd_pps_pulses", len(pps), help_="PPS pulses gpsd reported during the sample (~1 per second).")
    out.add("gpsd_sample_seconds", window, help_="Length of the gpsd sample.")
    if pps:
        o = offsets(pps)
        out.add("gpsd_pps_offset_seconds", o[-1], help_="System clock minus GPS second at the last PPS edge.")
        out.add("gpsd_pps_offset_abs_max_seconds", max(abs(x) for x in o), help_="Largest |PPS offset| in the sample.")
        out.add("gpsd_pps_precision_seconds", 2.0 ** pps[-1].get("precision", 0), help_="PPS timestamp precision.")
    if toff:
        o = offsets(toff)
        out.add("gpsd_nmea_offset_seconds", o[-1],
                help_="System clock minus the NMEA second when its sentence arrived (serial latency).")


def iso_ms_to_unix(text):
    try:
        base, _, frac = text.rstrip("Z").partition(".")
        t = calendar.timegm(time.strptime(base, "%Y-%m-%dT%H:%M:%S"))
        return t + (float("0." + frac) if frac else 0.0)
    except ValueError:
        return None


# ── kernel PPS ───────────────────────────────────────────────────────────────

def collect_pps(out, device):
    name = os.path.basename(device)
    with open("/sys/class/pps/%s/assert" % name) as f:
        stamp, _, seq = f.read().strip().partition("#")
    sec, _, nsec = stamp.partition(".")
    lbl = {"device": device}
    out.add("pps_assert_total", int(seq), lbl, "PPS assert events the kernel counted.", "counter")
    out.add("pps_assert_timestamp_seconds", float(stamp), lbl, "System time of the last PPS assert.")
    # From the text: a float of the whole timestamp can't hold nanoseconds.
    frac = int(nsec.ljust(9, "0")[:9]) * 1e-9
    out.add("pps_assert_offset_seconds", frac - 1 if frac >= 0.5 else frac, lbl,
            "System clock's distance from the whole second at the last PPS assert.")


# ── PTP ──────────────────────────────────────────────────────────────────────

PORT_STATES = {"INITIALIZING": 1, "FAULTY": 2, "DISABLED": 3, "LISTENING": 4, "PRE_MASTER": 5,
               "MASTER": 6, "PASSIVE": 7, "UNCALIBRATED": 8, "SLAVE": 9}
PMC_QUERIES = ["PORT_DATA_SET", "CURRENT_DATA_SET", "PARENT_DATA_SET", "DEFAULT_DATA_SET",
               "TIME_PROPERTIES_DATA_SET", "TIME_STATUS_NP", "PORT_STATS_NP"]
PHC2SYS_LINE = re.compile(r"(\S+) (\S+) offset\s+(-?\d+) s(\d) freq\s+([+-]?\d+) delay\s+(-?\d+)")


def num(text):
    try:
        return int(text, 0)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def pmc(timeout):
    args = ["pmc", "-u", "-b", "0"] + ["GET " + q for q in PMC_QUERIES]
    res = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True)
    sets, cur = {}, None
    for line in res.stdout.splitlines():
        m = re.search(r"RESPONSE MANAGEMENT (\S+)", line)
        if m:
            cur = sets.setdefault(m.group(1), {})
            continue
        if cur is not None and line.startswith("\t\t"):
            parts = line.split(None, 1)
            if len(parts) == 2:
                cur[parts[0]] = parts[1].strip()
    return sets


def collect_ptp(out, interface, phc2sys_unit, window, timeout):
    ds = pmc(timeout)
    if "PORT_DATA_SET" not in ds:
        raise RuntimeError("no PORT_DATA_SET from ptp4l")
    port = ds["PORT_DATA_SET"]
    plbl = {"interface": interface}
    state = port.get("portState", "")
    out.add("ptp4l_port_state", PORT_STATES.get(state, 0), plbl,
            "Port state: 1 initializing, 2 faulty, 3 disabled, 4 listening, 5 pre_master, 6 master, 7 passive, 8 uncalibrated, 9 slave.")
    out.add("ptp4l_log_sync_interval", num(port.get("logSyncInterval", "")), plbl, "log2 of the Sync interval.")
    out.add("ptp4l_log_announce_interval", num(port.get("logAnnounceInterval", "")), plbl, "log2 of the Announce interval.")
    out.add("ptp4l_peer_mean_path_delay_seconds", (num(port.get("peerMeanPathDelay", "")) or 0) * 1e-9, plbl,
            "Peer delay (P2P only).")

    cur = ds.get("CURRENT_DATA_SET", {})
    out.add("ptp4l_steps_removed", num(cur.get("stepsRemoved", "")), help_="Hops to the grandmaster (0: this is it).")
    off = num(cur.get("offsetFromMaster", ""))
    out.add("ptp4l_offset_from_master_seconds", None if off is None else off * 1e-9, help_="Offset from the master (0 as grandmaster).")
    mpd = num(cur.get("meanPathDelay", ""))
    out.add("ptp4l_mean_path_delay_seconds", None if mpd is None else mpd * 1e-9, help_="Mean path delay to the master.")

    dflt = ds.get("DEFAULT_DATA_SET", {})
    par = ds.get("PARENT_DATA_SET", {})
    out.add("ptp4l_clock_class", num(dflt.get("clockClass", "")), help_="This clock's clockClass (6: locked to a primary reference, 248: default).")
    out.add("ptp4l_clock_accuracy", num(dflt.get("clockAccuracy", "")), help_="This clock's clockAccuracy (0xFE unknown).")
    out.add("ptp4l_offset_scaled_log_variance", num(dflt.get("offsetScaledLogVariance", "")), help_="This clock's offsetScaledLogVariance.")
    out.add("ptp4l_priority", num(dflt.get("priority1", "")), {"n": "1"}, "BMCA priorities.")
    out.add("ptp4l_priority", num(dflt.get("priority2", "")), {"n": "2"})
    out.add("ptp4l_domain", num(dflt.get("domainNumber", "")), help_="PTP domain.")
    out.add("ptp4l_grandmaster_clock_class", num(par.get("gm.ClockClass", "")), help_="The grandmaster's clockClass.")
    out.add("ptp4l_grandmaster_info", 1, {
        "grandmaster": par.get("grandmasterIdentity", ""), "clock": dflt.get("clockIdentity", ""),
        "port_state": state, "interface": interface}, "Grandmaster and own clock identity.")

    tp = ds.get("TIME_PROPERTIES_DATA_SET", {})
    out.add("ptp4l_utc_offset_seconds", num(tp.get("currentUtcOffset", "")), help_="Announced TAI-UTC.")
    for key, metric in [("currentUtcOffsetValid", "ptp4l_utc_offset_valid"), ("timeTraceable", "ptp4l_time_traceable"),
                        ("frequencyTraceable", "ptp4l_frequency_traceable"), ("ptpTimescale", "ptp4l_ptp_timescale"),
                        ("leap61", "ptp4l_leap61"), ("leap59", "ptp4l_leap59")]:
        out.add(metric, num(tp.get(key, "")), help_="Announced time property %s." % key)
    out.add("ptp4l_time_source", num(tp.get("timeSource", "")), help_="Announced timeSource (0x20 GPS, 0xA0 internal oscillator).")

    ts = ds.get("TIME_STATUS_NP", {})
    out.add("ptp4l_gm_present", 1 if ts.get("gmPresent") == "true" else 0, help_="1 if a remote grandmaster is present.")

    stats = ds.get("PORT_STATS_NP", {})
    for key, val in stats.items():
        m = re.match(r"(rx|tx)_(\w+)", key)
        if m:
            out.add("ptp4l_messages_total", num(val), dict(plbl, direction=m.group(1), type=m.group(2)),
                    "PTP messages by direction and type.", "counter")

    # phc2sys logs one line per update to the journal; summarise the window.
    res = subprocess.run(["journalctl", "-u", phc2sys_unit, "--since", "-%ds" % window, "-o", "cat",
                          "--no-pager", "-q"], capture_output=True, text=True, timeout=timeout)
    samples = [m.groups() for m in map(PHC2SYS_LINE.search, res.stdout.splitlines()) if m]
    out.add("phc2sys_samples", len(samples), help_="phc2sys updates in the window.")
    out.add("phc2sys_window_seconds", window, help_="Window the phc2sys summary covers.")
    if samples:
        clock, source, offset, state, freq, delay = samples[-1]
        lbl = {"clock": clock, "source": source}
        offs = [int(x[2]) * 1e-9 for x in samples]
        out.add("phc2sys_offset_seconds", offs[-1], lbl, "Last offset of the target clock to its source.")
        out.add("phc2sys_offset_abs_max_seconds", max(abs(x) for x in offs), lbl, "Largest |offset| in the window.")
        out.add("phc2sys_offset_rms_seconds", math.sqrt(sum(x * x for x in offs) / len(offs)), lbl, "RMS offset in the window.")
        out.add("phc2sys_servo_state", int(state), lbl, "Servo state: 0 unlocked, 1 jump, 2 locked.")
        out.add("phc2sys_frequency_ppb", int(freq), lbl, "Frequency adjustment of the target clock.")
        out.add("phc2sys_delay_seconds", int(delay) * 1e-9, lbl, "Delay of reading the clocks.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, help="node_exporter textfile directory")
    ap.add_argument("--pps-device", default="/dev/pps0")
    ap.add_argument("--gpsd-window", type=float, default=4.0, help="seconds of gpsd's stream to sample")
    ap.add_argument("--ptp-interface", default="", help="ptp4l's interface; empty: no PTP")
    ap.add_argument("--phc2sys-unit", default="")
    ap.add_argument("--phc2sys-window", type=int, default=60)
    ap.add_argument("--timeout", type=float, default=3.0)
    a = ap.parse_args()

    run("ntpsec", a.dir, collect_ntpsec, a.timeout)
    run("gpsd", a.dir, collect_gpsd, a.gpsd_window, a.pps_device)
    run("pps", a.dir, collect_pps, a.pps_device)
    if a.ptp_interface:
        run("ptp", a.dir, collect_ptp, a.ptp_interface,
            a.phc2sys_unit or "phc2sys-%s.service" % a.ptp_interface, a.phc2sys_window, a.timeout)
    elif os.path.exists(os.path.join(a.dir, "ptp.prom")):
        os.remove(os.path.join(a.dir, "ptp.prom"))


if __name__ == "__main__":
    main()
