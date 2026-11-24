#!/bin/sh
# Buckle fact provider, mounted at host.facts.script.rpi.
# hat_*: a HAT with an ID EEPROM (PoE+ HAT, most vendor HATs) shows up in the device tree.
# nvme:  whether an NVMe controller is attached (Pi 5 PCIe, CM4 carrier boards).
# pps_gpio: a GPIO PPS input is in the device tree (pps-gpio overlay): a GPS
#        board's pulse is wired up. Such boards have no ID EEPROM, so their
#        overlay is declared per host (rpi_gps_pps); this reports the result.
hat=/proc/device-tree/hat
field() {
  [ -r "$hat/$1" ] || return 0
  tr -d '\000' < "$hat/$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}
nvme=false
for c in /sys/class/nvme/nvme*; do [ -e "$c" ] && nvme=true && break; done
pps_gpio=false
for n in /proc/device-tree/pps@*; do
  [ -r "$n/compatible" ] && tr -d '\000' < "$n/compatible" | grep -q pps-gpio && pps_gpio=true && break
done
printf '{"hat_product":"%s","hat_vendor":"%s","nvme":%s,"pps_gpio":%s}\n' "$(field product)" "$(field vendor)" "$nvme" "$pps_gpio"
