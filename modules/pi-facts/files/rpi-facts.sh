#!/bin/sh
# Buckle fact provider, mounted at host.facts.script.rpi.
# hat_*: a HAT with an ID EEPROM (PoE+ HAT, most vendor HATs) shows up in the device tree.
# nvme:  whether an NVMe controller is attached (Pi 5 PCIe, CM4 carrier boards).
hat=/proc/device-tree/hat
field() {
  [ -r "$hat/$1" ] || return 0
  tr -d '\000' < "$hat/$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}
nvme=false
for c in /sys/class/nvme/nvme*; do [ -e "$c" ] && nvme=true && break; done
printf '{"hat_product":"%s","hat_vendor":"%s","nvme":%s}\n' "$(field product)" "$(field vendor)" "$nvme"
