# Check fans, temperatures and events

Use this when a blade seems hot or loud, an LED blinks, or you just want to see how the blades are doing.

**Before you start:** bladectl set up on your Mac ([Set up bladectl on your Mac](set-up-bladectl-on-your-mac.md)); run the commands from the homelab checkout. `--blade blade-piN` picks one blade, `-A` asks all four.

1. The overview of one blade:

   ```sh
   bladectl --blade blade-pi2 get status
   ```

   One table row: temperature, fan speed override, fan speed (RPM and %), stealth mode, identify, critical mode, power status (`poe+` is normal), health (`OK`).
2. Fans and SoC temperatures of all four:

   ```sh
   bladectl -A get fan
   bladectl -A get temp
   ```

   With the default curve expect 4,000-5,500 RPM at 50-60% and 45-52 °C (2026-11-26). The curve is 40% at 45 °C, 80% at 55 °C, 100% at 60 °C; `bladectl --blade blade-pi2 describe fan` prints it.
3. A live chart of fan speed and temperature for one blade (Ctrl-C to quit):

   ```sh
   bladectl --blade blade-pi2 monitor
   ```

4. What the agents report as it happens:

   ```sh
   bladectl -A events
   ```

   Leave it running. Filter with `-e`, repeatable (`-e fan_stall -e critical`), or get JSON with `-o json`. Event names: `critical`, `critical_reset`, `fan_stall`, `fan_stall_clear`, `undervoltage`, `undervoltage_clear`, `throttled`, `throttled_clear`, `power_limit`, `power_limit_clear`, `identify`, `identify_confirm`, `button_press`, `button_gesture`.

## Reading the LEDs

| LED | Pattern | Means |
|-----|---------|-------|
| idle colour | dim green | all fine (`idle_led_color`) |
| top | blinking red | critical mode: SoC at 60 °C or more, fan forced to 100% until 5 °C below |
| top | fast blink, orange | fan stall |
| top | bursts, amber | under-voltage (PoE budget ran out) |
| edge | slow blink, yellow | firmware throttling |
| edge | magenta | identify (see [Identify a blade](identify-a-blade.md)) |

The exact colours and priorities are in [Agent configuration](../reference/agent-configuration.md#leds-and-indicators).

## In Grafana

The [Compute Blade dashboard](https://spechtlabs.grafana.net/d/compute-blades) (folder Infrastructure > Providers) has a front view of the chassis with each blade's SoC temperature, fan and state, then rows for thermals and airflow, fans, power and throttling, compute, and an event log. The **Raspberry Pi Fleet** dashboard in the same folder has the blades' fan speed and duty too.

## If something's off

- A fan at hundreds of thousands of RPM, and no airflow temperature: [Fix a fan reading of 800k RPM](fix-a-fan-reading-of-800k-rpm.md).
- `fan_stall`: the fan is commanded to 20% or more but reports under 100 RPM for 15 s. Check the fan unit physically; the stall clears with `fan_stall_clear` once it spins.
- `undervoltage` or `power_limit`: the blade isn't getting 802.3at PoE+. `bladectl -A get power_status` should say `poe+`; anything else means the switch port or cable delivers 802.3af or less, and the agent caps the CPU at 1200 MHz meanwhile (lowest clock during under-voltage).
- Critical mode often: airflow. Look at **SoC above airflow** on the dashboard.

Grafana alerts on the same conditions (fan stall, critical temperature, under-voltage, PoE+, throttling, a missed fan unit, missing metrics); see [Respond to a blade alert](respond-to-a-blade-alert.md).
