# Set up bladectl on your Mac

Use this the first time you want `bladectl` on a machine, after the agents renewed their certificates, or when bladectl stops connecting to a blade.

**Before you start:**

- A checkout of SpechtLabs/homelab with mise. `mise install` in it installs `bladectl` (pinned in `mise.toml` to the agents' version, 0.11.5 today) and `yq`.
- SSH as `pi` to every blade without a password prompt (the task uses `ssh -o BatchMode=yes`), with `sudo`.
- Best on the home LAN: the task finds the blades by mDNS. Away from it, it refreshes the blades already in your config instead.

Nothing on the blades changes; the task only reads each blade's client config.

1. From the repo checkout, run the task:

   ```sh
   cd ~/src/gh/cedi/homelab
   mise run bladectl-config
   ```

   It runs `bladectl discover`, fetches `/root/.config/bladectl/config.yaml` from each blade over SSH (the agent wrote it, with a client certificate signed by that blade's CA), sets each entry's server to `blade-piN:8081`, and merges them into `~/.config/bladectl/config.yaml` (mode 0600) with `blade-pi1` as `current-blade`. You should see:

   ```text
   wrote /Users/cedi/.config/bladectl/config.yaml: blade-pi1 blade-pi2 blade-pi3 blade-pi4
   ```

   followed by the discovery table and `try: bladectl -A get fan; bladectl -A events`.
2. If it printed `no blades found`, discovery heard nothing within its 3 s and you had no config yet. Run it again; on 2026-11-26 the first `discover --wait 3s` from the Mac found nothing while a 6 s wait found all four.

## Check it worked

```sh
bladectl -A get fan
```

Four lines like `blade-pi1: 5177 RPM (58%)`. Inside the checkout mise puts `bladectl` on your PATH; elsewhere use `mise exec -C ~/src/gh/cedi/homelab -- bladectl ...`.

## If it didn't

- `ssh: ... Permission denied` or a password prompt: fix SSH to `pi@blade-piN` first; the certificates only travel over SSH, discovery carries no secrets.
- One blade fails with a TLS error: check its server address in your config.

  ```sh
  yq '.blades[] | .name + " " + .blade.server' ~/.config/bladectl/config.yaml
  ```

  Each should read `blade-piN:8081`. The server certificate names `blade-piN`, `blade-piN.local`, `localhost` and the blade's IP addresses at the time it was made.

!!! warning "Unverified: blade-pi3 announces itself as `blade-pi3-2.local`"
    On 2026-11-26 avahi on blade-pi3 had renamed it to `blade-pi3-2.local` (a host name conflict), and `bladectl discover` showed blade-pi3 as `address changed`. The task's last step, `bladectl discover --save`, updates the address of configured blades, so it may write `blade-pi3-2.local:8081`, a name the certificate doesn't contain. It hadn't happened in the config on this Mac (still `blade-pi3:8081`). If blade-pi3 fails with a certificate error, set the address back:
    ```sh
    yq -i '(.blades[] | select(.name == "blade-pi3") | .blade.server) = "blade-pi3:8081"' ~/.config/bladectl/config.yaml
    ```
