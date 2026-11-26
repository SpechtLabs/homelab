# Respond to a blade alert

Use this when a Grafana alert from the rule group `compute-blades` (folder Infrastructure > Providers, label `service=compute-blades`) fires. Each section below is one rule, titled as the alert, and the alert's runbook link points here. The rules are in `grafanaalertrules-blades.yaml` in [`apps/grafana-operator/cluster/specht-labs/`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/grafana-operator/cluster/specht-labs); queries and thresholds in [Metrics and dashboard](../reference/metrics-and-dashboard.md#alerts).

**Before you start:** the alert names the blade in its `instance` label (`blade-pi2:9666`). You need SSH to `pi@blade-piN`, or bladectl on your Mac ([Set up bladectl on your Mac](set-up-bladectl-on-your-mac.md)). Every rule is a warning: the blades carry nothing else, so none of this is urgent at night. Keep the [Compute Blade dashboard](https://spechtlabs.grafana.net/d/compute-blades) open.

## Blade — agent metrics missing {#blade-agent-down}

**After 10 min.** Alloy hasn't scraped compute-blade-agent on the blade (`:9666`) for 10 minutes, though it did within the last day. The agent is down, Alloy is, or the whole blade is. A blade without its agent runs its fan at 100% with dark LEDs.

1. Is the blade up at all?

   ```sh
   ssh pi@blade-pi2 uptime
   ```

   No answer: it's off or hung. See [Power a blade off and on](power-a-blade-off-and-on.md).
2. Check the agent and Alloy:

   ```sh
   ssh pi@blade-pi2 systemctl status compute-blade-agent alloy --no-pager
   ssh pi@blade-pi2 journalctl -u compute-blade-agent -n 50 --no-pager
   ```

3. If the agent failed, start it again: `ssh pi@blade-pi2 sudo systemctl restart compute-blade-agent`. Its log says why it stopped; a config error shows there too.

**Check it worked:** `curl -s http://blade-pi2:9666/metrics | head` from the Mac, and the alert resolves on the next evaluation. A blade that stays away longer than a day drops out of this rule, so don't leave one dead.

## Blade — fan stalled {#blade-fan-stall}

**After 5 min.** The agent drives the fan at 20% or more, but it turns slower than 100 RPM (`fan_stall`). The top LED blinks fast in orange.

1. Look at what the agent sees:

   ```sh
   bladectl --blade blade-pi2 get status
   bladectl --blade blade-pi2 get fan
   ```

2. If the RPM is 0 or very low, look at the fan unit at the rack: blocked blades, a loose fan unit. One fan unit cools two blades, so check its neighbour too.
3. If the RPM is in the hundreds of thousands instead, it's not a stall: see [Blade — smart fan unit not detected](respond-to-a-blade-alert.md#blade-fan-unit-misdetected).

**Check it worked:** `bladectl -A events -e fan_stall_clear` shows the clear event, and the top LED goes back to normal.

## Blade — smart fan unit not detected {#blade-fan-unit-misdetected}

**After 5 min.** The agent runs the standard fan unit driver, or reports a fan speed above 20,000 RPM (~800,000 is the known symptom). All four blades have the smart unit, so detection failed at startup and the speed and airflow readings are wrong.

Follow [Fix a fan reading of 800k RPM](fix-a-fan-reading-of-800k-rpm.md). On 0.11.5 a restart re-detects:

```sh
ssh pi@blade-pi2 sudo systemctl restart compute-blade-agent
```

**Check it worked:** `curl -s http://blade-pi2:9666/metrics | grep computeblade_fan_unit` says `type="smart"`.

## Blade — critical temperature {#blade-critical-temperature}

**After 10 min.** The SoC has stayed at or above the critical threshold (60 °C) for 10 minutes, with the fan already forced to 100%. Normal is 45-55 °C (the hottest any blade got in the week before this rule was 55.5 °C).

1. Check temperature and fan:

   ```sh
   bladectl --blade blade-pi2 get status
   ```

2. Fan at speed but still hot: airflow. Look at **SoC above airflow** on the dashboard; a high airflow temperature means the air coming in is warm (rack, room), a big gap means poor contact or a blocked path on this blade.
3. Fan not at speed: treat it as [a stalled fan](respond-to-a-blade-alert.md#blade-fan-stall).
4. Find what's loading the CPU (`ssh pi@blade-pi2 top`) if the blade usually runs cooler.

**Check it worked:** `bladectl -A events -e critical_reset` shows the blade leaving critical mode once it's 5 °C below the threshold.

## Blade — under-voltage {#blade-undervoltage}

**After 5 min.** The Pi firmware has flagged under-voltage for 5 minutes. The agent holds the CPU at its lowest clock until the supply recovers; the top LED shows amber bursts.

1. Check the supply:

   ```sh
   bladectl -A get power_status
   ```

2. `poe+` with under-voltage anyway: the switch's PoE budget is exhausted or the cable is marginal. Check the switch's PoE budget and the cable to this blade.
3. Anything other than `poe+`: see [Blade — not on PoE+](respond-to-a-blade-alert.md#blade-not-on-poe-plus) too.

**Check it worked:** `bladectl -A events -e undervoltage_clear`, and the dashboard's **CPU limited by power policy** goes back to 0.

## Blade — not on PoE+ {#blade-not-on-poe-plus}

**After 15 min.** The blade has run on 802.3af PoE or USB-C for 15 minutes instead of 802.3at PoE+, so the agent caps its CPU at 1200 MHz (`limited_power`).

1. Confirm:

   ```sh
   bladectl --blade blade-pi2 get power_status
   ```

   `poeOrUsbC` means not PoE+.
2. Check the switch port's PoE mode (it must offer 802.3at) and the cable. The blades are on PoE+ normally; a port that renegotiated down after a switch restart is the first suspect.

!!! warning "Unverified"
    Which switch and port feeds each blade isn't recorded in the repo, so this page can't name them.

**Check it worked:** `poe+` again, and `bladectl -A events -e power_limit_clear`.

## Blade — CPU throttled {#blade-throttled}

**After 15 min.** The firmware has reported the CPU capped, throttled or at the soft temperature limit for 15 minutes. The edge LED blinks yellow, slowly. These blades hadn't throttled once in the week before this rule.

1. Which flag:

   ```sh
   curl -s http://blade-pi2:9666/metrics | grep computeblade_throttle_active
   ```

   `soft_temp_limit` or `throttled` with a hot SoC: work through [Blade — critical temperature](respond-to-a-blade-alert.md#blade-critical-temperature). `under_voltage` or `arm_freq_capped` with a normal temperature: work through [Blade — under-voltage](respond-to-a-blade-alert.md#blade-undervoltage).

**Check it worked:** `bladectl -A events -e throttled_clear`; **Firmware throttling (now)** on the dashboard back to none.
