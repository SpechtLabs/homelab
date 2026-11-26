# Identify a blade

Use this when you need to find a particular blade in the rack (to swap a cable, check a fan unit, pull it), or to find out which name the blade in front of you has.

**Before you start:** bladectl on your Mac ([Set up bladectl on your Mac](set-up-bladectl-on-your-mac.md)), or be standing at the rack. Identify only changes an LED.

## From the Mac: light up a blade

1. Turn identify on for the blade you want:

   ```sh
   bladectl --blade blade-pi3 set identify
   ```

   Its edge LED shows the identify colour (dim magenta) until you turn it off.
2. Find the blade with the lit edge LED.
3. Turn it off again, from the Mac or at the blade:

   ```sh
   bladectl --blade blade-pi3 remove identify
   ```

   or press the blade's edge button once (a single press toggles identify).

To have bladectl wait until someone at the rack confirms with a button press, use `bladectl --blade blade-pi3 set identify --wait`. The agent emits `identify_confirm` when that happens.

## At the rack: which blade is this?

1. On the Mac, start the event stream:

   ```sh
   bladectl -A events -e identify -e button_press
   ```

2. Press the edge button once on the blade in front of you (or the button on its fan unit, which always toggles identify). The event line names the blade.
3. Press it once more to turn identify off.

## Check it worked

```sh
bladectl -A get identify
```

Every blade `Off` once you're done. The Compute Blade dashboard's **Blade state** panel shows identify too.
