# Get kubectl access

Use this when you need `kubectl` against labk3s from your own machine.

**Before you start:** you're on the tailnet as a member of `group:admins`. Admins may reach `svc:labk3s` on tcp:6443; `group:sre` may not (they get SSH to the nodes and the Argo CD UI, see [Addresses, ports and Services](../reference/network.md)).

There are two ways in. The admin kubeconfig is k3s's own cluster-admin client certificate and never expires on its own. TKA hands out a kubeconfig for a short-lived service account, one hour at a time.

## Option A: the admin kubeconfig

The working copy lives at `~/.kube/configs/labk3s`, with context `labk3s` and server `https://labk3s.sphinx-map.ts.net:6443`.

1. Point kubectl at it and always name the context:

   ```sh
   export KUBECONFIG=~/.kube/configs/labk3s
   kubectl --context labk3s get nodes
   ```

   You should see five `Ready` nodes with `100.x` internal IPs.

### If the file is missing

Rebuild it from the server's own kubeconfig, `/etc/rancher/k3s/k3s.yaml` on `clusterpi-leader` (root-only, mode 0600; admins may Tailscale-SSH there as root).

!!! warning "Unverified"
    How `~/.kube/configs/labk3s` was first made isn't recorded. k3s writes `k3s.yaml` with a localhost `server:` and a context called `default`; the steps below assume that. Check the copied file before using it.

1. Copy it and point it at the Service:

   ```sh
   ssh root@clusterpi-leader cat /etc/rancher/k3s/k3s.yaml > ~/.kube/configs/labk3s
   chmod 600 ~/.kube/configs/labk3s
   ```

   Then set the `server:` line to `https://labk3s.sphinx-map.ts.net:6443` and rename the context to `labk3s` (`kubectl config rename-context default labk3s`). The serving certificate carries that name as a `tls-san` ([`config.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/k3s-server/files/config.yaml.j2)), so TLS verifies.

## Option B: TKA

TKA (`lab-tka`, tcp:8123 on the tailnet, app `tka` in [k8s-deployment](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/tka/cluster/labk3s)) checks your tailnet identity against the capability grant `specht-labs.de/cap/tka` and gives `group:admins` the role `cluster-admin` for 1 hour.

!!! warning "Unverified"
    Not run against `lab-tka` while writing this. The flags come from the TKA CLI's help (`ts-k8s-auth`, `-s/--server`, `-p/--port`) and the local `~/.config/tka/config.yaml`, which points at the specht-labs instance (`tka.sphinx-map.ts.net`, port 8123).

1. With TKA's shell integration loaded (`eval "$(ts-k8s-auth generate integration zsh)"`), sign in to the labk3s instance:

   ```sh
   tka login --server lab-tka.sphinx-map.ts.net --port 8123
   ```

   `tka shell` with the same flags gives a subshell whose access ends when you exit; `tka signout` ends a `login` session.

The kubeconfig TKA hands out points at `https://labk3s.sphinx-map.ts.net:6443`, like the admin one (`clusterInfo.apiEndpoint` in [`tka-config.patch.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/tka/cluster/labk3s/tka-config.patch.yaml), with the cluster CA as `caData`).

## The `KUBECONFIG` trap

`~/src/gh/SpechtLabs/k8s-deployment/.mise.toml` sets `KUBECONFIG=~/.kube/configs/specht-labs` for anything run inside that checkout. A `kubectl` there talks to **specht-labs**, and the NotFound or drift you see is that cluster's. The Mac's default context isn't labk3s either (it has been a local kind cluster). So:

- run kubectl for labk3s from outside that repo, or set `KUBECONFIG` explicitly on the command line;
- always pass `--context labk3s`.

## Check it worked

```sh
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s get --raw /readyz
```

You should see `ok`.

## If it didn't

- `Unable to connect` or a timeout: check `dig +short labk3s.sphinx-map.ts.net` returns `100.67.145.122` and that you're on the tailnet as yourself (not a tagged device). Then [Respond to a labk3s alert](respond-to-a-labk3s-alert.md) has the checks for the API itself.
- `x509` errors with `curl`: expected. `curl` doesn't know the k3s CA; use the kubeconfig.
