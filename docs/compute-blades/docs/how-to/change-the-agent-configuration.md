# Change the agent configuration

Use this to change the fan curve, the critical temperature, LED colours, health indicators, button gestures or the power policy, for all four blades.

**Before you start:** the config on the blades (`/etc/compute-blade-agent/config.yaml`) comes from the repo and Buckle overwrites local edits. Every key is documented upstream in the agent's [configuration reference](https://github.com/compute-blade-community/compute-blade-agent/blob/main/docs/reference/configuration.md). The change goes to the blades first, as the canary, and only on to the rest of the fleet if their health checks pass.

To try a fan speed on one blade without a commit, override it with bladectl, and put it back afterwards:

```sh
bladectl --blade blade-pi2 set fan --percent 80    # fixed speed
bladectl --blade blade-pi2 set fan --auto          # back to the curve
```

## Change it for good

1. Edit [`modules/compute-blade-agent/files/config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/files/config.yaml.j2). For example the fan curve:

   ```yaml
   fan_controller:
     steps:
       - { temperature: 45, percent: 40 }
       - { temperature: 55, percent: 80 }
       - { temperature: 60, percent: 100 }
   ```

   Keep `critical_temperature_threshold` in step with the top of the curve (60 today).
2. Validate locally:

   ```sh
   mise run validate
   ```

3. Open a PR. CI dry-plans every host; the blades' plans show the config diff. Merge it.
4. Buckle rolls it out: the canary phase writes the file on all four blades and restarts the agent (handler `restart`; there's no reload). The agent's own `metrics`, `agent` (30 s uptime) and `api-certificate` health checks then gate the next phase.

## Check it worked

```sh
bladectl --blade blade-pi2 describe fan
bladectl -A get status
```

The new curve, and every blade `HEALTH OK`. In the Buckle UI the rollout moves past `canary`.

## If it didn't

- The rollout paused in `canary`: a blade's health check failed. Look at that host's run in the Buckle UI; the agent's log says why it didn't start:

  ```sh
  ssh pi@blade-pi2 journalctl -u compute-blade-agent -n 50 --no-pager
  ```

  Revert the PR to roll back.
- The log warns about a deprecated key: rename it as the warning says; the old name keeps working until upstream removes it.
