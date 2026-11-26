# k3s configuration

Flags live in k3s's own config file, `/etc/rancher/k3s/config.yaml` (mode 0600, written by Buckle from a template), not on `ExecStart`.

## Server (`clusterpi-leader`)

From [`modules/k3s-server/files/config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-server/files/config.yaml.j2):

| Key | Value | From |
|---|---|---|
| `token` | `K3S_TOKEN` | Buckle secret, `/etc/buckle/secrets/K3S_TOKEN` on isa; changing it breaks node joins |
| `data-dir` | `/var/lib/rancher/k3s` | |
| `node-ip` | the host's tailnet IPv4 | fact `host.facts.tailscale.ips[0]` |
| `advertise-address` | `100.67.145.122` | var `k3s_service_ip`, `svc:labk3s`'s VIP |
| `flannel-iface` | `tailscale0` | |
| `tls-san` | `labk3s.sphinx-map.ts.net` | vars `k3s_service` + `tailnet` |
| `disable` | `traefik` | var `k3s_disable` |
| `disable-network-policy` | `true` | var `k3s_disable_network_policy` |

Datastore: SQLite through kine (single server, no etcd, no `cluster-init`). Other files: the unit `/etc/systemd/system/k3s.service` (`ExecStart=/usr/local/bin/k3s server`) and the admin kubeconfig `/etc/rancher/k3s/k3s.yaml`, which Buckle's `labk3s` cluster executor uses too.

## Agents (`clusterpi-worker1..4`)

From [`modules/k3s-agent/files/config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-agent/files/config.yaml.j2):

| Key | Value |
|---|---|
| `server` | `https://labk3s.sphinx-map.ts.net:6443` (vars `k3s_server`, `k3s_api_port`) |
| `token` | `K3S_TOKEN` |
| `data-dir` | `/var/lib/rancher/k3s` |
| `node-ip` | the host's tailnet IPv4 (`host.facts.tailscale.ips[0]`) |
| `flannel-iface` | `tailscale0` |

Unit: `/etc/systemd/system/k3s-agent.service` (`ExecStart=/usr/local/bin/k3s agent`).

## Both

| What | Value |
|---|---|
| Binary | `/usr/local/bin/k3s`, GitHub release `k3s-io/k3s` at `k3s_version` (asset `k3s-arm64`, checksummed) |
| Version | `k3s_version` in [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml) (`v1.37.2+k3s1` on 2026-11-26) |
| sysctls | `net.ipv4.ip_forward=1`, `net.ipv6.conf.all.forwarding=1` |
| Unit start | waits up to 120 s for `tailscale0` to have a `100.x` IPv4, loads `br_netfilter` and `overlay`; `Restart=always`, `KillMode=process` (pods keep running through a k3s restart) |
| Optional env | `/etc/default/k3s` or `/etc/default/k3s-agent` (`EnvironmentFile=-`) |
| Leftovers removed | `/etc/systemd/system/k3s*.service.env`, `/usr/local/bin/k3s-install.sh` (from k3s-ansible) |
| Still on disk | `k3s-killall.sh`, `k3s-uninstall.sh` (server), `k3s-agent-uninstall.sh` (agents) in `/usr/local/bin`, from the old installer |

A change to the template, the unit or the binary notifies the `restart` handler (`systemctl restart k3s` / `k3s-agent`).

## Health checks

From the modules' `health:` blocks; Buckle runs them after every apply and a failing required one pauses the rollout.

| Module | Check | Required | Passes when |
|---|---|---|---|
| `k3s-server` | `unit` | yes | `k3s` active for at least 60 s |
| | `kubelet` | yes | `http://127.0.0.1:10248/healthz` returns 200 with `ok` |
| | `apiserver` | yes | `k3s kubectl get --raw /readyz` prints `ok` |
| | `svc-api` | no | the same through `https://labk3s.sphinx-map.ts.net:6443` (checks the certificate name) |
| | `svc-ip` | no | `getent ahostsv4 labk3s.sphinx-map.ts.net` returns `k3s_service_ip` |
| | `nodes-ready` | no | every node `Ready` |
| `k3s-agent` | `unit` | yes | `k3s-agent` active for at least 60 s |
| | `kubelet` | yes | as on the server |
| `argocd-seed` | `argocd-server` | no | Deployment `argocd/argocd-server` has an available replica |

## Argo CD seed

[`modules/argocd-seed`](https://github.com/SpechtLabs/homelab/blob/main/modules/argocd-seed/module.yaml) on the server:

| Var | Value |
|---|---|
| `argocd_seed_repo` | `https://github.com/SpechtLabs/k8s-deployment.git` |
| `argocd_seed_ref` | `main` (cloned once, `update: false`) |
| `argocd_seed_overlay` | `apps/argocd/cluster/labk3s` |
| `argocd_seed_dir` | `/var/lib/argocd-seed` (tools, checkout, `age.key` from `ARGOCD_AGE_KEY`) |
| `argocd_seed_kustomize_version`, `_helm_version`, `_ksops_version` | in `vars/versions.yaml`; keep in step with k8s-deployment's `.mise.toml` |

The seed applies only when the API answers that `argocd/argocd-server` doesn't exist. A failed or slow query counts as "leave it".
