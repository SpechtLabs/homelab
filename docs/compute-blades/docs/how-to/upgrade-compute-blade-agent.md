# Upgrade compute-blade-agent

Use this when a new compute-blade-agent release is out and you want it on the blades, or a Renovate PR named `compute-blade-agent` showed up.

**Before you start:** the version lives in two places that must match: `compute_blade_agent_version` in [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml) (the agent and bladectl on the blades) and `"github:compute-blade-community/compute-blade-agent"` in [`mise.toml`](https://github.com/SpechtLabs/homelab/blob/main/mise.toml) (bladectl on your Mac). Renovate bumps both in one PR, grouped as `compute-blade-agent`, as soon as a release appears (no minimum release age for this project), and automerges patch and minor versions once the PR's checks pass. Majors automerge after the release is a week old. So usually the upgrade happens without you; this page is for watching it or doing it by hand.

1. By hand: set the same version in both files, then

   ```sh
   mise install
   mise run validate
   ```

   and open a PR. Read the release notes first: [releases](https://github.com/compute-blade-community/compute-blade-agent/releases).
2. Once merged, Buckle installs the release's `.deb` from GitHub on all four blades at once (the canary phase) and restarts the agent.
3. Watch the canary phase in the Buckle UI. The agent's health checks (`agent`, `packaged-binary`, `metrics`, `api-certificate`) have to pass before any other host gets the revision.

## Check it worked

```sh
bladectl version                      # bladectl and blade-pi1's agent
bladectl --blade blade-pi4 version
bladectl -A get status
ssh pi@blade-pi1 dpkg-query -W compute-blade-agent
```

The new version everywhere, every blade `HEALTH OK`, and fans at a few thousand RPM. The Compute Blade dashboard should look as before; a metric renamed upstream shows as an empty panel.

## If it didn't

- Rollout paused at `canary`: the new agent fails a health check on some blade. Check its log (`journalctl -u compute-blade-agent -n 50`), then revert the version bump in both files. The `apt.package` task pins an exact version, so the revert should install the old one again (a downgrade hasn't been tried here).
- bladectl on the Mac and the agents disagree after a partial upgrade: `mise install` in the checkout picks up the version `mise.toml` pins.
