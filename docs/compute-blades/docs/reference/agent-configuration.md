# Agent configuration

The values in [`modules/compute-blade-agent/files/config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/files/config.yaml.j2), rendered to `/etc/compute-blade-agent/config.yaml` on each blade. Buckle restarts the agent on every change; the agent doesn't reload. Every key is in upstream's [configuration reference](https://github.com/compute-blade-community/compute-blade-agent/blob/main/docs/reference/configuration.md). `log.mode` has done nothing since 0.11.3; `--debug` on the command line does.

## API and metrics

| Key | Value |
|-----|-------|
| `listen.metrics` | `:9666` |
| `listen.grpc` | `:8081` |
| `listen.mode` | `tcp` |
| `listen.authenticated` | `true` (mTLS) |
| `discovery.mdns.enabled` | `true`: announces `_compute-blade._tcp` through avahi |

## Fan and temperature

| Key | Value |
|-----|-------|
| `fan_controller.steps` | 45 °C → 40%, 55 °C → 80%, 60 °C → 100%, interpolated between |
| `critical_temperature_threshold` | 60 °C: fan 100%, stealth off, top LED blinking red, until 5 °C below |
| `hal.rpm_reporting_standard_fan_unit` | `true`: read the tachometer if the agent falls back to a standard fan unit |
| `stealth_mode` | `false` |

## Health conditions

| Condition | Settings | Shows as |
|-----------|----------|----------|
| `fan_stall` | judged from 20% duty, stalled below 100 RPM, 15 s grace for spin-up | top LED, fast blink, `{64, 24, 0}`, priority 30 |
| `undervoltage` | firmware flag, clears after 30 s | top LED, burst, `{64, 40, 0}`, priority 20 |
| `throttling` | firmware flags (capped, throttled, soft limit), clears after 30 s | edge LED, slow blink, `{32, 32, 0}`, priority 10 (off by default upstream) |

Each condition is also a `computeblade_state_state{state=...}` series and a bladectl event.

## LEDs and indicators

Colours are `{red, green, blue}`, 0-255 per channel.

| Key | Value |
|-----|-------|
| `idle_led_color` | `{0, 16, 0}` |
| `identify_led_color` | `{16, 0, 16}` (edge LED) |
| `critical_led_color` | `{64, 0, 0}` (top LED) |

Identify (edge) and critical mode (top) always win; otherwise the higher priority wins on an LED.

## Power policy

| Situation | Governor | Max CPU |
|-----------|----------|---------|
| `limited_power`: not on 802.3at PoE+ (802.3af or USB-C) | unchanged | 1200 MHz (CM4 maximum 1500) |
| `undervoltage` | `powersave` | lowest clock (`max_freq_mhz: 0`) |

The agent restores the original CPU settings when the limit ends or it stops.

## Button gestures

| Gesture | Action |
|---------|--------|
| single press (edge button) | `identify-toggle` |
| double press | unbound (only a `button_gesture` event) |
| hold 5 s (`long_press`) | `shutdown`; the edge LED blinks white after 1 s |
| 5 quick presses (`multi_press`) | `emergency-poweroff`: off at once, no unmount, flushes up to 2 s; stays off until the PoE port is power-cycled |
| fan unit button | always toggles identify |

`gesture_window: 400ms`. Every gesture is a `button_gesture` event, bound or not.
