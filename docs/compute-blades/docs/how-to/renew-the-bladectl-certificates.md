# Renew the bladectl certificates

Use this when bladectl reports a certificate error, Buckle's `compute-blade-agent: api-certificate` check fails, or you want to know when the certificates expire.

**Before you start:** SSH to the blades as `pi`. Each agent made its own CA (valid 10 years), a server certificate and root's bladectl client certificate (1 year each) when it first started; the current ones expire on 2027-11-18.

## Normally: nothing to do on the blades

Buckle renews them. The `agent-certificates` task in [`modules/compute-blade-agent`](https://github.com/SpechtLabs/homelab/blob/main/modules/compute-blade-agent/module.yaml) deletes the server certificate and root's bladectl config once either expires within 30 days, and restarts the agent, which writes new ones under the same CA. Your Mac's config still holds the old client certificate; it keeps working until it expires itself, since the CA is the same. Refresh it once after the renewal:

```sh
cd ~/src/gh/cedi/homelab
mise run bladectl-config
```

## Check when they expire

On a blade:

```sh
sudo openssl x509 -enddate -noout -in /etc/compute-blade-agent/server.pem
```

On the Mac, for the first blade in your config:

```sh
yq '.blades[0].blade.cert.client-certificate-data' ~/.config/bladectl/config.yaml | base64 -d | openssl x509 -enddate -noout
```

Change `[0]` to `[1]` and so on for the others.

## Renew early, by hand

Do this if the automatic renewal didn't happen or the server certificate lacks a name you need. On the blade, the same as the Buckle task:

```sh
sudo rm /etc/compute-blade-agent/server.pem /etc/compute-blade-agent/server-key.pem /root/.config/bladectl/config.yaml
sudo systemctl restart compute-blade-agent
```

Then `mise run bladectl-config` on the Mac.

Only if the CA key may have leaked, delete `ca.pem` and `ca-key.pem` as well; every client certificate signed by the old CA stops working.

## Check it worked

```sh
bladectl -A get fan
```

Four answers. On the blade, `openssl x509 -enddate` shows a date a year out. The api-certificate health check passes once the server certificate is more than 14 days from expiry.
