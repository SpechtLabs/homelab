#!/bin/sh
# Buckle fact provider, mounted at host.facts.script.rpi.
# A HAT with an ID EEPROM (PoE+ HAT, most vendor HATs) shows up in the device tree.
hat=/proc/device-tree/hat
field() {
  [ -r "$hat/$1" ] || return 0
  tr -d '\000' < "$hat/$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}
printf '{"hat_product":"%s","hat_vendor":"%s"}\n' "$(field product)" "$(field vendor)"
