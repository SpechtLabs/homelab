# bladectl commands

bladectl 0.11.5, as pinned in [`mise.toml`](https://github.com/SpechtLabs/homelab/blob/main/mise.toml). Upstream reference: [bladectl.md](https://github.com/compute-blade-community/compute-blade-agent/blob/main/docs/reference/bladectl.md).

## Global flags

| Flag | Meaning |
|------|---------|
| `--blade NAME` | the blade to talk to; default `current-blade` from the config (`blade-pi1` after `mise run bladectl-config`) |
| `-A`, `--all` | all configured blades at once |
| `--timeout D` | gRPC timeout, default `1m0s` |

## Commands

| Command | Does |
|---------|------|
| `get status` | one-row table: temperature, fan override, fan speed, stealth, identify, critical mode, power status, health |
| `get fan` | fan RPM and duty, e.g. `blade-pi1: 5177 RPM (58%)` |
| `get temp` | SoC temperature |
| `get power_status` | `poe+` or `poeOrUsbC` |
| `get identify`, `get critical`, `get stealth` | `On` / `Off` |
| `describe fan` | the fan curve: percent at each temperature step |
| `set fan --percent N` / `set fan --auto` | fixed fan speed / back to the curve (aliases `fan_speed`, `rpm`) |
| `remove fan` | remove the fan speed override |
| `set identify [--wait] [--confirm]` | identify LED on; `--wait` blocks until confirmed by a button press |
| `remove identify` | identify off |
| `set stealth [--disable]` / `remove stealth` | stealth mode on / off |
| `events [-e NAME ...] [-o text\|json]` | stream events until Ctrl-C; reconnects when a blade restarts |
| `monitor` | live chart of fan speed and temperature |
| `discover [--wait D] [--save]` | find agents by mDNS (`_compute-blade._tcp`); `--save` adds new blades to the config and updates the address of configured ones |
| `version` | bladectl's version and the selected blade's agent version |

There's no power command: see [Power a blade off and on](../how-to/power-a-blade-off-and-on.md).

## Config file

`~/.config/bladectl/config.yaml`, mode 0600, written by `mise run bladectl-config`:

```yaml
current-blade: blade-pi1
blades:
  - name: blade-pi1
    blade:
      server: blade-pi1:8081
      cert:
        certificate-authority-data: <base64 PEM, the blade's CA>
        client-certificate-data: <base64 PEM>
        client-key-data: <base64 PEM>
```

Each blade has its own CA, so each entry carries its own three values. On the blade itself, root's copy is `/root/.config/bladectl/config.yaml`, with `server: localhost:8081`.
