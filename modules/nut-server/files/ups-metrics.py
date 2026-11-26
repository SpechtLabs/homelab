#!/usr/bin/python3 -I
# Managed by Buckle. Local changes will be overwritten.
"""Prometheus textfile for the UPS, as isa's upsd serves it.

Reads `upsc <ups>@localhost` (the dummy-ups proxy of the UPS Tower, with the
FSD flag upsd itself adds) and `upsc -c` (the upsmon clients logged in), and
leaves ups.prom in the node_exporter textfile directory, where Alloy's embedded
node_exporter picks it up. Read-only: upsc needs no login.

A failed read writes ups_metrics_up 0 and keeps the last success's timestamp,
so "stale" is something an alert can see; the other numbers disappear rather
than freeze.
"""

import argparse
import calendar
import math
import os
import re
import subprocess
import sys
import time

# ups.status flags worth a series of their own, 0 or 1 on every run. Any other
# flag the UPS reports gets a series while it's set.
FLAGS = ["OL", "OB", "LB", "FSD", "RB", "CHRG", "DISCHRG", "OFF", "OVER", "BYPASS"]

# (upsc variable, metric, help)
GAUGES = [
    ("battery.charge", "ups_battery_charge_percent", "Battery charge, percent."),
    ("battery.runtime", "ups_battery_runtime_seconds", "Runtime left on battery at the current load, as the UPS estimates it."),
    ("battery.voltage", "ups_battery_voltage_volts", "Battery voltage."),
    ("ups.load", "ups_load_percent", "Load, percent of the UPS's nominal power."),
    ("ups.realpower", "ups_realpower_watts", "Real power drawn by the load."),
    ("input.voltage", "ups_input_voltage_volts", "Mains voltage at the input."),
    ("input.frequency", "ups_input_frequency_hertz", "Mains frequency at the input."),
    ("output.voltage", "ups_output_voltage_volts", "Voltage at the outlets."),
    ("ups.temperature", "ups_temperature_celsius", "Internal temperature."),
]

# ups.test.result values that mean the last self-test found a problem.
TEST_FAILED = re.compile(r"fail|error|warn", re.IGNORECASE)

LAST_SUCCESS = "ups_metrics_last_success_timestamp_seconds"


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


def write_textfile(path, out):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(out.render())
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def previous_success(path):
    """The last success's timestamp from the file this run replaces, if any."""
    try:
        with open(path) as f:
            for line in f:
                if line.startswith(LAST_SUCCESS):
                    return float(line.rsplit(None, 1)[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def upsc(args, timeout):
    res = subprocess.run(["upsc"] + args, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError("upsc %s: exit %d: %s" % (" ".join(args), res.returncode, res.stderr.strip()))
    return res.stdout


def collect(out, ups, timeout):
    lbl = {"ups": ups}
    variables = {}
    for line in upsc(["%s@localhost" % ups], timeout).splitlines():
        key, sep, value = line.partition(": ")
        if sep:
            variables[key.strip()] = value.strip()
    if "ups.status" not in variables:
        raise RuntimeError("no ups.status from upsd")

    flags = set(variables["ups.status"].split())
    for flag in sorted(set(FLAGS) | flags):
        out.add("ups_status", 1 if flag in flags else 0, dict(lbl, flag=flag),
                "1 while the UPS (or upsd, for FSD) reports this ups.status flag.")

    for var, metric, help_ in GAUGES:
        out.add(metric, variables.get(var), lbl, help_)

    result = variables.get("ups.test.result")
    if result is not None:
        out.add("ups_test_failed", 1 if TEST_FAILED.search(result) else 0, lbl,
                "1 if the UPS's last self-test reported a failure or warning (ups.test.result).")
    date = variables.get("ups.test.date")
    if date:
        try:
            out.add("ups_test_last_timestamp_seconds", calendar.timegm(time.strptime(date, "%Y-%m-%d")), lbl,
                    "Day of the UPS's last self-test (ups.test.date, midnight UTC).")
        except ValueError:
            pass

    clients = [c for c in upsc(["-c", "%s@localhost" % ups], timeout).splitlines() if c.strip()]
    out.add("ups_clients", len(clients), lbl,
            "upsmon clients logged in to upsd for this UPS (the primary on isa included).")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, help="node_exporter textfile directory")
    ap.add_argument("--ups", default="ups", help="UPS name on the local upsd")
    ap.add_argument("--timeout", type=float, default=10.0)
    a = ap.parse_args()

    path = os.path.join(a.dir, "ups.prom")
    lbl = {"ups": a.ups}
    out = Out()
    start = time.monotonic()
    ok = 1
    try:
        collect(out, a.ups, a.timeout)
        last_success = time.time()
    except Exception as e:  # report it, and leave a file that says so
        print("ups: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        out = Out()
        ok = 0
        last_success = previous_success(path)
    out.add("ups_metrics_up", ok, lbl, "1 if the last read of the UPS through upsd succeeded.")
    out.add(LAST_SUCCESS, last_success, lbl, "When the UPS was last read successfully.")
    out.add("ups_metrics_duration_seconds", time.monotonic() - start, lbl, "How long reading the UPS took.")
    write_textfile(path, out)


if __name__ == "__main__":
    main()
