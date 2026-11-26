# Blades

As read from the blades on 2026-11-26. Catalog entries: `resource:blade-pi1` to `blade-pi4` in [`catalog/hardware.yaml`](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml).

| Host | Module | RAM | NVMe | LAN IPv4 (DHCP) | Fan unit | Power |
|------|--------|-----|------|-----------------|----------|-------|
| blade-pi1 | CM4 Rev 1.0 | 8 GB | 931.5 GB | 192.168.0.30 | smart | PoE+ |
| blade-pi2 | CM4 Rev 1.1 | 8 GB | 465.8 GB | 192.168.0.182 | smart | PoE+ |
| blade-pi3 | CM4 Rev 1.1 | 8 GB | 465.8 GB | 192.168.0.70 | smart | PoE+ |
| blade-pi4 | CM4 Rev 1.1 | 8 GB | 465.8 GB | 192.168.0.169 | smart | PoE+ |

The addresses come from DHCP and can change; `bladectl discover` and `tailscale status` show the current ones. Use the host names: `blade-piN` resolves on the LAN and over the tailnet (`blade-piN.sphinx-map.ts.net`).

Common to all four:

- SSH as `pi` (login shell fish). Kernel 6.12.115 (`rpt-rpi-v8`).
- Buckle group `blades` (from `host.facts.hardware.raspberry_pi.compute_module == true`), rollout phase `canary`.
- Vars from [`vars/group-blades.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-blades.yaml): Alloy scrapes `rpi_exporter` on :9243 and `blade_exporter` (the agent) on :9666.
- PTP clients of timepi (eth0, PHC 0): see the [Timekeeping docs](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/).
- Smart fan unit on UART5 (GPIO 12/13, `/dev/ttyAMA5`). One fan unit serves two blades and follows the higher of their two requests.
- The blade board has no ID EEPROM of its own; its fan unit and I2C appear only once the agent's overlays are in, which is why the group keys on the CM4.
