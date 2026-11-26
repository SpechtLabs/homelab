# What the agent does

A compute blade is a carrier board for a CM4 with PoE, an NVMe slot, a fan unit, two RGB LEDs (top and edge) and an edge button. None of that hardware does anything useful on its own. compute-blade-agent is the program that does: it reads the SoC temperature and sets the fan, drives the LEDs, watches the button and the PoE supply, and exports all of it as metrics. When the agent stops, it deliberately leaves the fan at 100% and the LEDs off, since nothing controls the temperature anymore. A blade without its agent is loud and blind.

cedi maintains the agent upstream ([compute-blade-community/compute-blade-agent](https://github.com/compute-blade-community/compute-blade-agent), released with release-please), so most of the features configured here were written with these four blades in mind, and bugs found here get fixed there (the 800k RPM bug was [#233](https://github.com/compute-blade-community/compute-blade-agent/pull/233), released in 0.11.5).

## How this repo configures it

[`config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/files/config.yaml.j2) spells out every setting rather than relying on upstream defaults, so a default changing in a release doesn't silently change the blades. A few choices worth knowing:

- **TCP with mTLS** instead of the default Unix socket, so bladectl works from the Mac. Each agent issues its own CA and certificates.
- **A steep fan curve** (40% at 45 °C to 100% at 60 °C) with critical mode at 60 °C. On 2026-11-26 the CM4s sat at 47-51 °C with the fans at 50-58%.
- **Throttling on the edge LED.** Upstream leaves this indicator off because sustained load throttles often; these blades hadn't throttled once in a week, so it's worth seeing, and the edge LED keeps the top one free for hardware faults.
- **A power policy.** On 802.3af PoE or USB-C (anything short of PoE+) the CPU is capped at 1200 MHz, because a CM4 under full load can draw more than 802.3af delivers; during under-voltage it drops to the lowest clock until the supply recovers.
- **Button gestures** for the moments you're at the rack without a laptop: a single press toggles identify, holding 5 s shuts down cleanly, five presses power off at once for a blade whose shutdown hangs.
- **mDNS discovery**, so `bladectl discover` and `mise run bladectl-config` find the blades without a host list. Discovery carries no secrets; the client certificates travel over SSH.

## Certificates

The agent creates its certificates when they're missing and never renews them: the CA lasts 10 years, the server and client certificates one. Left alone, bladectl would stop working a year after the first start. The module turns that into renewal: 30 days before either certificate expires it deletes them and restarts the agent, which issues new ones under the same CA. The `api-certificate` health check fails at 14 days, so it only trips if that renewal didn't happen. The Mac keeps a copy of the client certificate, which is why `mise run bladectl-config` needs a rerun after a renewal.

## Test builds on a blade

Testing an agent build on a real blade (upstream's `docs/how-to/test-on-a-blade.md` and its e2e runs) swaps the agent's `ExecStart` through a systemd drop-in, `compute-blade-agent.service.d/dev.conf` or `e2e.conf`, with binaries under `/usr/local/lib/cba-e2e`. The module removes both drop-ins and that directory, so a rollout always puts the packaged agent back.

Removing a drop-in isn't enough on its own, though. A Buckle run that stops after removing it never fires the restart handler, and the package's postinst restarts the agent with whatever `ExecStart` systemd still has loaded. So the `packaged-agent` task checks what's actually running (`/proc/<pid>/exe`) and reloads and restarts until it's `/usr/bin/compute-blade-agent`, and the `packaged-binary` health check holds a rollout until it is. If you test on a blade, expect the next rollout to undo it.
