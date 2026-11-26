# Metrics and dashboard

Alloy on each blade scrapes the agent on `:9666` as job `blade_exporter` ([`vars/group-blades.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-blades.yaml)) into the homelab Mimir tenant (`mimir-homelab`). Select a blade with `instance=~"blade-pi1:.*"`. node_exporter metrics from the same blades come as job `integrations/unix`, instance `blade-piN:9100`.

## Agent metrics

As served by 0.11.5 (`curl -s localhost:9666/metrics` on a blade):

| Metric | Labels | Meaning |
|--------|--------|---------|
| `computeblade_soc_temperature` | | SoC temperature, °C |
| `computeblade_airflow_temperature` | | air temperature at the smart fan unit; missing when the agent fell back to the standard unit |
| `computeblade_fan_speed` | | fan RPM |
| `computeblade_fan_target_percent` | | the duty the agent asks for |
| `computeblade_fan_unit` | `type="smart"` or `"standard"` | which fan unit the agent detected |
| `computeblade_state_state` | `state="normal"`, `critical`, `fan_stall`, `undervoltage`, `throttled`, `identify` | 1 while that state is on |
| `computeblade_power_status` | `type="poe+"`, `"poeOrUsbC"` | 1 for the current supply. Up to 0.11.4 the labels were `"1"` and `"0"` |
| `computeblade_power_limit_active` | | 1 while the power policy caps the CPU |
| `computeblade_throttle_active`, `computeblade_throttle_occurred` | `flag="under_voltage"`, `arm_freq_capped`, `throttled`, `soft_temp_limit` | firmware flags now / since boot |
| `computeblade_agent_events_count` | `type=<event name>` | counter per event type |
| `computeblade_stealth_mode_enabled` | | |
| `computeblade_compute_module_present` | `type="cm4"` | |
| `computeblade_edge_button_event_count`, `computeblade_button_events_dropped_count`, `computeblade_led_color_change_event_count` | | counters |

Dashboards and queries should match `type=~"1|poe\\+"` on `computeblade_power_status` while old data is in range.

## Dashboard

**Compute Blade** (uid `compute-blades`), Grafana folder Infrastructure > Providers: [open](https://spechtlabs.grafana.net/d/compute-blades). Source: [`components/grafana-dashboards/infrastructure/compute_blades.json`](https://github.com/SpechtLabs/k8s-deployment/blob/main/components/grafana-dashboards/infrastructure/compute_blades.json) in SpechtLabs/k8s-deployment (last rebuilt in commit `446654bb`; no generator script is checked in there). The grafana-operator picks up a changed dashboard on its periodic resync, about 10 minutes after Argo CD syncs.

| Row | Panels |
|-----|--------|
| Cluster | Blades online, Cluster health, Hottest SoC, CPU busy, Memory used, Network |
| Chassis (front view) | per blade: SoC, Fan; Blade state |
| Thermals & airflow | SoC temperature, Airflow temperature, SoC above airflow, NVMe temperature |
| Fans | Fan speed, Fan target |
| Power & throttling | Power source, CPU limited by power policy, CPU frequency, Firmware throttling (now), Throttling since boot |
| Compute | CPU cores busy, Memory used, Load per core, Network receive/transmit, NVMe root filesystem used |
| Events | Agent events in range, Events per blade |

The **Raspberry Pi Fleet** dashboard in the same folder has blade fan speed and duty too.

## Alerts

Rule group `compute-blades` in `grafanaalertrules-blades.yaml` in [`apps/grafana-operator/cluster/specht-labs/`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/grafana-operator/cluster/specht-labs) (SpechtLabs/k8s-deployment), folder Infrastructure > Providers, evaluated every minute on `mimir-homelab`. All `severity=warning`, `service=compute-blades`, one alert per blade. Runbooks: [Respond to a blade alert](../how-to/respond-to-a-blade-alert.md).

| Title | UID | Fires when | For |
|-------|-----|-----------|-----|
| Blade — agent metrics missing | `blade-agent-down` | a blade's `up{job="blade_exporter"}` was there in the last day but isn't 1 now | 10m |
| Blade — fan stalled | `blade-fan-stall` | `computeblade_state_state{state="fan_stall"}` is 1 | 5m |
| Blade — smart fan unit not detected | `blade-fan-unit-misdetected` | `computeblade_fan_unit` with a type other than `smart`, or `computeblade_fan_speed` above 20,000 | 5m |
| Blade — critical temperature | `blade-critical-temperature` | `computeblade_state_state{state="critical"}` is 1 | 10m |
| Blade — under-voltage | `blade-undervoltage` | `computeblade_state_state{state="undervoltage"}` is 1 | 5m |
| Blade — not on PoE+ | `blade-not-on-poe-plus` | the `computeblade_power_status` series for `poe+` (or `type="1"`, its label before 0.11.5) is 0 | 15m |
| Blade — CPU throttled | `blade-throttled` | `computeblade_state_state{state="throttled"}` is 1 | 15m |

No data counts as OK everywhere; `blade-agent-down` exists for exactly that gap.
