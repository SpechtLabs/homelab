#!/bin/sh
# Managed by Buckle (modules/ptp-server). Announces over PTP what timepi's
# clock is locked to right now, from ntpsec's selection:
#   PPS selected       clockClass 6   (primary reference)  ±100 ns  GPS
#   network NTP        clockClass 52  (degraded)           ±10 ms   NTP
#   nothing selected   clockClass 248 (default)            unknown  oscillator
# Only sets the grandmaster settings when they differ, and logs each change.
# Usage: ptp-gm-quality TAI_UTC_OFFSET
set -u
utc_offset=${1:?usage: ptp-gm-quality TAI_UTC_OFFSET}

peers=$(ntpq -pn 2>/dev/null) || exit 0
if printf '%s\n' "$peers" | grep -qE '^[*o]SHM\(1\)'; then
    state=gps class=6 accuracy=0x21 source=0x20 traceable=1
elif printf '%s\n' "$peers" | grep -q '^\*'; then
    state=ntp class=52 accuracy=0x31 source=0x50 traceable=1
else
    state=free-running class=248 accuracy=0xfe source=0xa0 traceable=0
fi

current=$(pmc -u -b 0 "GET GRANDMASTER_SETTINGS_NP" 2>/dev/null) || exit 0
field() { printf '%s\n' "$current" | awk -v k="$1" '$1 == k { print tolower($2); exit }'; }
if [ "$(field clockClass)" = "$class" ] && [ "$(field clockAccuracy)" = "$accuracy" ] &&
   [ "$(field timeSource)" = "$source" ] && [ "$(field timeTraceable)" = "$traceable" ]; then
    exit 0
fi

pmc -u -b 0 "SET GRANDMASTER_SETTINGS_NP clockClass $class clockAccuracy $accuracy offsetScaledLogVariance 0xffff currentUtcOffset $utc_offset leap61 0 leap59 0 currentUtcOffsetValid 1 ptpTimescale 1 timeTraceable $traceable frequencyTraceable $traceable timeSource $source" >/dev/null 2>&1 &&
    echo "grandmaster now $state: clockClass $class, clockAccuracy $accuracy, timeSource $source"
