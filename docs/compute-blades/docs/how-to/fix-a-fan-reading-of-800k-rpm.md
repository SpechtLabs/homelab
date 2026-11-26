# Fix a fan reading of 800k RPM

Use this when a blade reports a fan speed of hundreds of thousands of RPM (around 800,000) and no airflow temperature, in `bladectl get fan` or on the Compute Blade dashboard.

**Before you start:** SSH to `pi@blade-piN`. The fan itself is fine; the agent is reading the wrong thing. Restarting the agent runs the fan at 100% for a moment, and the smart fan unit follows the higher of its two blades' requests, so the neighbour gets loud briefly too.

All four blades have the **smart** fan unit, which reports its speed and the airflow temperature over a serial line (UART5 on GPIO 12/13, `/dev/ttyAMA5`). If the agent misses it at startup (detection has a 3 s window), it falls back to the standard fan unit: GPIO 12 becomes PWM and GPIO 13 a tachometer input. The smart unit's serial packets on GPIO 13 then count as tachometer edges, about 33 every 2 s, which averages out to hundreds of thousands of RPM.

1. Confirm the agent took the blade for a standard fan unit:

   ```sh
   curl -s localhost:9666/metrics | grep computeblade_fan_unit
   sudo pinctrl get 12,13
   ```

   Stuck: `computeblade_fan_unit{type="standard"}` and `GPIO12 = PWM0_0`, `GPIO13 = input`. Healthy: `type="smart"` and `GPIO12 = TXD5`, `GPIO13 = RXD5`.
2. Check the agent version:

   ```sh
   dpkg-query -W compute-blade-agent
   ```

3. On **0.11.5 or later**, restart the agent. Since [PR #233](https://github.com/compute-blade-community/compute-blade-agent/pull/233) it puts both pins back on UART5 before detecting, so a failed detection no longer sticks:

   ```sh
   sudo systemctl restart compute-blade-agent
   ```

   On **0.11.4 or older** a restart doesn't help (the pins stay on PWM/input and every detection fails again); reboot the blade instead: `sudo reboot`.

## Check it worked

```sh
journalctl -u compute-blade-agent -b --no-pager | grep 'detected smart fan unit'
bladectl --blade blade-piN get fan
```

The log line from the restart, and a few thousand RPM. On the dashboard, the blade's airflow temperature comes back.

## If it didn't

- Still `standard` after a restart on 0.11.5: detection timed out again. Restart once more; if it keeps failing, check the fan unit's seating and its firmware (the package ships `/usr/share/compute-blade-agent/fanunit.uf2`; upstream has a how-to for flashing it).
- The agent isn't the packaged one (`readlink /proc/$(systemctl show -p MainPID --value compute-blade-agent)/exe` isn't `/usr/bin/compute-blade-agent`): someone is testing a build on this blade. See [What the agent does](../explanation/what-the-agent-does.md#test-builds-on-a-blade).
