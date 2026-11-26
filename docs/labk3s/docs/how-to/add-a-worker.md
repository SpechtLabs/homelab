# Add a worker

Use this when a new Raspberry Pi should join labk3s as a worker.

**Before you start:** the Pi runs Raspberry Pi OS (Debian) and is on the tailnet. Its tailnet node name decides everything: Buckle puts every host whose id matches `clusterpi-worker*` into the `k3s-agent` group ([`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml)), and a host's id is its tailnet node name. So name it `clusterpi-worker5` (or the next free number). k3s is installed as the `arm64` release asset; every k3s node is a Pi.

1. **Tag the device.** In the Tailscale admin console (Machines > the Pi > Edit ACL tags) give it all three:

    | Tag | Why |
    |---|---|
    | `tag:buckle-agent` | the Buckle server accepts only agents carrying it (`allowed_tags` in `bootstrap/server.yaml`) |
    | `tag:k3s-node` | the grants to `svc:labk3s` tcp:6443 and node to node udp:8472, tcp:10250, tcp:8681; SSH for admins and SREs |
    | `tag:ceph-client` | ceph-csi on the node reaches the Ceph mons and OSDs |

    Do this before k3s starts: without `tag:k3s-node` the agent can't reach the API to join, and the other nodes drop its VXLAN traffic.

2. **Enrol it in Buckle.** Follow the [fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/) for enrolling a host. The first rollout that reaches it applies `base`, `pi-firmware` (cgroups in `cmdline.txt`, which k3s needs, and a reboot) and the rest, then `k3s-agent`. That writes `/etc/rancher/k3s/config.yaml` with `server: https://labk3s.sphinx-map.ts.net:6443`, the token and `node-ip` from the host's own `tailscale.ips[0]` fact, and starts `k3s-agent`.

    !!! warning "Unverified"
        The "Add an agent" button's tagged auth keys need the `provisioning` block in `bootstrap/server.yaml`, which is commented out there today. Check which tags a newly enrolled device actually gets, and fix them in the console before its first rollout.

3. **Give CI its facts.** Add `fixtures/facts/clusterpi-worker5.json`, trimmed as in [`bootstrap/README.md`](https://github.com/SpechtLabs/homelab/blob/main/bootstrap/README.md) step 5 (pull it from the server's API once the host is enrolled), so `buckle validate` plans it on every PR.

4. **Add it to the catalog.** A `Resource` for the host in [`catalog/hardware.yaml`](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml) (`system: labk3s`, like `clusterpi-worker4`) and a `dependsOn` entry in [`modules/k3s-agent/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-agent/catalog-info.yaml).

Nothing changes in the policy or in k8s-deployment: the grants go by tag, and the DaemonSets (ceph-csi node plugin, Alloy logs, node-exporter) schedule onto the new node by themselves.

## Check it worked

```sh
export KUBECONFIG=~/.kube/configs/labk3s
kubectl --context labk3s get nodes -o wide
kubectl --context labk3s -n ceph-csi-rbd get pods -l component=nodeplugin -o wide
ssh pi@clusterpi-worker5 "bash -c 'ip -d link show flannel.1 | head -3'"
```

The node is `Ready` with its `100.x` address as `INTERNAL-IP`, a node plugin runs on it, and `flannel.1` shows `mtu 1230` and `dev tailscale0`. In Buckle, its `k3s-agent` checks (`unit`, `kubelet`) pass.

## If it didn't

- **`k3s-agent` keeps restarting:** `journalctl -u k3s-agent` on the node. A timeout to `labk3s.sphinx-map.ts.net:6443` is a missing `tag:k3s-node`. An auth error means the token: `K3S_TOKEN` in the Buckle server's secret store must stay the cluster's token.
- **`Ready`, but pods on it can't reach pods elsewhere:** VXLAN between this node and the others. Check its tags, then `tailscale ping` another node.
