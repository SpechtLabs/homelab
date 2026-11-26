#!/bin/sh
# Managed by Buckle (modules/pi-firmware). Keeps a Pi's one-shot SD-root
# fallback in step with its live boot config:
#   /boot/firmware/cmdline-sd.txt  cmdline.txt with root= set to ROOT
#   /boot/firmware/tryboot.txt     config.txt plus `cmdline=cmdline-sd.txt`
# `reboot '0 tryboot'` boots that once; the next reboot is normal again.
# Written by hand on timepi on 2026-11-19, so config.txt changes since never
# reached tryboot.txt; this derives both from the live files instead.
#
# It only ever writes those two files, never config.txt or cmdline.txt, and
# refuses (exit 2) rather than write a fallback that can't boot: ROOT must be
# a partition that exists, and cmdline.txt must hold exactly one root= token.
#
# Usage: rpi-sd-fallback ROOT          write the files where they differ
#        rpi-sd-fallback ROOT --check  exit 1 if either differs, write nothing
set -eu
root=${1:?usage: rpi-sd-fallback PARTUUID=... [--check]}
mode=${2:-write}
fw=/boot/firmware

case "$root" in
  PARTUUID=?*) ;;
  *) echo "rpi-sd-fallback: ROOT must be PARTUUID=..., got '$root'" >&2; exit 2 ;;
esac
if [ ! -e "/dev/disk/by-partuuid/${root#PARTUUID=}" ]; then
  echo "rpi-sd-fallback: no partition $root" >&2; exit 2
fi
n=$(tr ' ' '\n' < "$fw/cmdline.txt" | grep -c '^root=' || true)
if [ "$n" != 1 ]; then
  echo "rpi-sd-fallback: $fw/cmdline.txt has $n root= tokens, want 1" >&2; exit 2
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# (^| ): rootwait and rootfstype= are tokens of their own.
sed -E "s#(^| )root=[^ ]*#\\1root=$root#" "$fw/cmdline.txt" > "$tmp/cmdline-sd.txt"
# [all]: config.txt may end inside a conditional section ([cm4], [pi5], ...).
{ cat "$fw/config.txt"; printf '\n[all]\ncmdline=cmdline-sd.txt\n'; } > "$tmp/tryboot.txt"

changed=0
for f in cmdline-sd.txt tryboot.txt; do
  cmp -s "$tmp/$f" "$fw/$f" && continue
  changed=1
  [ "$mode" = --check ] && continue
  # Same directory (vfat), so the rename replaces the file in one step.
  cp "$tmp/$f" "$fw/.$f.new"
  sync "$fw/.$f.new"
  mv "$fw/.$f.new" "$fw/$f"
  echo "rpi-sd-fallback: wrote $fw/$f"
done
[ "$mode" = --check ] && exit "$changed"
exit 0
