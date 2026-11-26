# The NAS and Tailscale

## Why the NAS sits outside Buckle

DSM has no apt, and Buckle only pulls container images; it doesn't run them. So the Synology is
configured in DSM by hand, and what can be versioned is: the compose projects in
[nas/](https://github.com/SpechtLabs/homelab/tree/main/nas), deployed through Container Manager.
That leaves drift possible, and it happened: the NAS's `media` project no longer has the Nginx
Proxy Manager the repo still lists ([Synology NAS](../reference/nas.md#compose-projects)).

## Only Services, no device

Clients reach the NAS only through the Tailscale Services it hosts: `svc:nas` (DSM, Drive),
`svc:stream` (Jellyfin), `svc:node-exporter` and `svc:nfs`. No grant names the device. A
Service name can't be taken while a device holds the same MagicDNS name, which is why the
device was renamed from `nas` to `nas-elbschloss` and `nas.sphinx-map.ts.net` now means the
Service. The policy's tests check that the device's own ports stay closed.

Every port in a Service's definition has to be served on the host, or the host drops out of
that Service ("required ports are missing"). Adding a port to a definition in the console
therefore takes the Service down until the NAS serves it too.

## Unserved ports pass through on 1.98.4

On isa, clusterpi-leader and hass-elbschloss (Tailscale 1.104.x) a Service address answers
only on the ports it serves. On the NAS (DSM's package, Tailscale 1.98.4, kernel tun) it
doesn't: tested on 2026-11-26, `svc:nas:8096` reached Jellyfin and `svc:stream:5001` reached
DSM. A grant of `"*"` to a NAS Service would therefore open every port on the box, so the
grants to `svc:nas` and `svc:stream` list their ports. Test again after the next package
update before relying on `"*"` there.

## NFS through `127.0.0.1`

NFS v3 needs the portmapper and mountd on their own ports, which a one-port Service can't
carry; v4.1 needs only 2049. So `svc:nfs` is v4.1.

tailscaled forwards the connection from localhost, and DSM sees every client as `127.0.0.1`
on a high port. Two consequences:

1. The DSM rule has to be for `127.0.0.1` with "Allow connections from non-privileged ports".
    The forward names `127.0.0.1` because `localhost` is `::1` on the NAS, which the rule
    doesn't match ("access denied by server").
2. DSM can't tell clients apart. The tailnet policy decides who reaches `svc:nfs`, and any
    client it lets in can mount every folder that has a `127.0.0.1` rule. Today that's one
    client (isa) and one folder (`/volume1/homelab`). A second client that should see only its
    own folder needs something other than DSM's host rules.

## State that survives, and what doesn't

tailscaled keeps the serve config in its state file: reboots and package updates keep it, an
uninstall loses it. The node key lives in the same file, so after an uninstall the NAS comes
back as a new device that needs its name (`nas-elbschloss`) and tags again. The NAS needs
`tag:nas` to serve its Services and `tag:tsidp-client` to reach tsidp for DSM's SSO. DSM
sign-in broke on 2026-11-25 when the NAS lost its old `tag:core-infra`, and came back once it
got `tag:tsidp-client`.

## Why some traffic stays on the LAN

The collector scrapes snmp-exporter and cAdvisor on `192.168.0.64` directly; only
node-exporter goes through a Service. Home Assistant backs up to DSM over the LAN as user
`hass` and has no grant on the NAS at all.
