#!/usr/bin/python3 -I
# Managed by Buckle. Local changes will be overwritten.
"""Prometheus textfile for this host's NUT client: will it shut down?

Every 30 s: is upsmon (nut-monitor) running, can this host read the UPS
through svc:nut the way upsmon does, and how it's set to shut down. Leaves
nut-client.prom in the node_exporter textfile directory, where Alloy's embedded
node_exporter picks it up. Read-only: upsc needs no login.

isa's ups-metrics only counts the upsmon logins (all from 127.0.0.1 behind
svc:nut), so this is the only place that says which host is missing.
"""

import argparse
import os
import subprocess
import sys
import time


def esc(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def write_textfile(path, samples):
    lines, seen = [], set()
    for name, help_, labels, value in samples:
        if name not in seen:
            seen.add(name)
            lines.append("# HELP %s %s" % (name, help_))
            lines.append("# TYPE %s gauge" % name)
        lbl = ",".join('%s="%s"' % (k, esc(v)) for k, v in labels.items())
        lines.append("%s%s %s" % (name, "{%s}" % lbl if lbl else "", repr(round(float(value), 12))))
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, help="node_exporter textfile directory")
    ap.add_argument("--ups", required=True, help="UPS name on the NUT server")
    ap.add_argument("--server", required=True, help="the NUT server upsmon monitors it on")
    ap.add_argument("--affinity", required=True, help="early or late")
    ap.add_argument("--onbatt-grace", type=float, required=True)
    ap.add_argument("--finaldelay", type=float, required=True)
    ap.add_argument("--timeout", type=float, default=10.0)
    a = ap.parse_args()

    ups = {"ups": a.ups}
    target = "%s@%s" % (a.ups, a.server)
    out = []

    monitor = subprocess.run(["systemctl", "is-active", "--quiet", "nut-monitor"]).returncode == 0
    out.append(("nut_client_monitor_up", "1 while upsmon (nut-monitor) is running.", ups, 1 if monitor else 0))

    start = time.monotonic()
    try:
        res = subprocess.run(["upsc", target, "ups.status"], capture_output=True, text=True, timeout=a.timeout)
        ok = res.returncode == 0 and res.stdout.strip() != ""
        if not ok:
            print("upsc %s: exit %d: %s" % (target, res.returncode, res.stderr.strip()), file=sys.stderr)
    except subprocess.TimeoutExpired:
        ok = False
        print("upsc %s: timed out after %ss" % (target, a.timeout), file=sys.stderr)
    took = time.monotonic() - start
    out.append(("nut_client_ups_reachable", "1 if this host read ups.status through the NUT server, as upsmon does.", ups, 1 if ok else 0))
    out.append(("nut_client_ups_read_duration_seconds", "How long that read took, the round trip to upsd.", ups, took))

    out.append(("nut_client_info", "How this host shuts down: affinity early (on battery) or late (on FSD).",
                dict(ups, affinity=a.affinity, server=a.server), 1))
    if a.affinity == "early":
        out.append(("nut_client_onbatt_grace_seconds", "An early host powers off this long after the UPS goes on battery.", ups, a.onbatt_grace))
    out.append(("nut_client_finaldelay_seconds", "upsmon's FINALDELAY: from the shutdown decision to SHUTDOWNCMD.", ups, a.finaldelay))
    out.append(("nut_client_metrics_timestamp_seconds", "When this file was written.", ups, time.time()))

    write_textfile(os.path.join(a.dir, "nut-client.prom"), out)


if __name__ == "__main__":
    main()
