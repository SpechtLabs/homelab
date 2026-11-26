# Power a blade off and on

Use this when a blade has to go off (to pull it, move it, or because it hangs) and come back afterwards.

**Before you start:** decide how. bladectl has no power command; you shut a blade down over SSH or with its edge button. A blade that's off is a canary host that's missing, so don't leave one off while you expect a rollout; see [The blades as Buckle's canary](../explanation/the-blades-as-buckles-canary.md).

## Shut it down cleanly

Over SSH:

```sh
ssh pi@blade-pi3 sudo poweroff
```

Or at the rack: **hold the edge button for 5 s**. The edge LED blinks white after 1 s; at 5 s the agent shuts the blade down cleanly (gesture `long_press`, action `shutdown`).

## Power it off at once

For a blade whose shutdown hangs: **press the edge button 5 times quickly** (gesture `multi_press`, action `emergency-poweroff`). The agent powers off without unmounting, after flushing for up to 2 s. Expect a filesystem check on the next boot.

If the agent itself is gone and nothing reacts, remove the blade's PoE power at the switch.

## Power it on again

After an emergency power-off the blade stays off until its PoE port is power-cycled; the comment on the gesture in [`config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/files/config.yaml.j2) says so.

!!! warning "Unverified"
    Which PoE switch and port feeds each blade isn't recorded in this repo, and the steps to power-cycle a port depend on that switch. Whether a clean shutdown (`sudo poweroff` or the 5 s hold) also needs a port power cycle to come back is untested here; assume it does. Unplugging the blade's Ethernet cable and plugging it back in cuts its PoE power just as well.

## Check it worked

1. The blade answers again (a minute or two after power):

   ```sh
   ssh pi@blade-pi3 uptime
   bladectl --blade blade-pi3 get status
   ```

   `HEALTH OK` and `POWER STATUS poe+`.
2. The agent found its smart fan unit (a few thousand RPM, not ~800,000):

   ```sh
   bladectl --blade blade-pi3 get fan
   ```

   If not: [Fix a fan reading of 800k RPM](fix-a-fan-reading-of-800k-rpm.md).
3. In the Buckle UI the host is connected and healthy again, and on the Compute Blade dashboard **Blades online** is back to 4.

Every button press shows as a `button_press` and `button_gesture` event (`bladectl -A events`), so you can see from the Mac what the blade registered.
