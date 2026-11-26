# Compute blades

Four Raspberry Pi Compute Module 4s, `blade-pi1` to `blade-pi4`, each on a compute blade with PoE+ power, an NVMe drive and a smart fan unit. [compute-blade-agent](https://github.com/compute-blade-community/compute-blade-agent) runs on each one and drives the blade's hardware: the fan curve, the two LEDs, the edge button, a power policy for when PoE runs short, and Prometheus metrics. `bladectl` talks to the agents from your Mac over mTLS.

The blades carry nothing the rest of the homelab depends on. That's why Buckle uses them as its **canary**: every rollout runs on all four first and stops there if a health check fails. They're also PTP clients of timepi (see the [Timekeeping docs](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/)).

| Part | Where | Defined in |
|------|-------|------------|
| compute-blade-agent (fan, LEDs, button, power policy, metrics `:9666`, API `:8081`) | each blade | [`modules/compute-blade-agent`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/module.yaml) |
| Agent config | `/etc/compute-blade-agent/config.yaml` | [`files/config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/files/config.yaml.j2) |
| Agent and bladectl version | | `compute_blade_agent_version` in [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml), bladectl in [`mise.toml`](https://github.com/SpechtLabs/homelab/blob/main/mise.toml) |
| Metrics scrape (job `blade_exporter`) | Alloy on each blade | [`vars/group-blades.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-blades.yaml) |
| `mise run bladectl-config` | your Mac | `mise.toml` |
| Canary phase | Buckle | `rollout.phases` in [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml) |
| Compute Blade dashboard | Grafana | SpechtLabs/k8s-deployment |

Membership is a hardware fact: `buckle.yaml` puts every host with `host.facts.hardware.raspberry_pi.compute_module == true` into the `blades` group. A fifth CM4 would join by itself.

## Where to start

- An alert fired: [Respond to a blade alert](how-to/respond-to-a-blade-alert.md).
- First time on this Mac: [Set up bladectl on your Mac](how-to/set-up-bladectl-on-your-mac.md).
- Something looks hot or loud: [Check fans, temperatures and events](how-to/check-fans-temperatures-and-events.md); a fan at ~800,000 RPM has [its own page](how-to/fix-a-fan-reading-of-800k-rpm.md).
- Which blade is which in the rack: [Identify a blade](how-to/identify-a-blade.md).
- A rollout paused in the canary phase: [The blades as Buckle's canary](explanation/the-blades-as-buckles-canary.md).

The sections:

- [How-to guides](how-to/index.md): bladectl, fans, LEDs, power, certificates, config and upgrades.
- [Reference](reference/index.md): the blades, bladectl commands, the agent's settings, ports, metrics.
- [Explanation](explanation/index.md): what the agent does and why, and the canary role.
