# Reset k3s

Use this when you want to wipe k3s off the labk3s nodes and start over with an empty cluster. This destroys the cluster: every object, secret, PV binding and the CA.

**Before you start:** root on the nodes (admins may Tailscale-SSH as root to `tag:k3s-node`). Read [Replace or re-create the server](replace-or-re-create-the-server.md) for what breaks afterwards.

Reset is by hand on purpose. A Buckle task with a removal hook (say `k3s-uninstall.sh`) runs whenever its rendered command changes, so a harmless refactor of the module could wipe the cluster. `homelab-ansible` had a `k3s-reset.yml`; it wasn't ported.

The uninstall scripts from k3s's installer are on the nodes: `/usr/local/bin/k3s-uninstall.sh` on `clusterpi-leader`, `/usr/local/bin/k3s-agent-uninstall.sh` on the workers (both checked 2026-11-26). They stop k3s, remove its binary, unit and `/etc/rancher/k3s`, and delete `/var/lib/rancher/k3s`. The old `k3s-reset.yml` ran exactly these.

!!! warning "Unverified"
    Not run since the move to Buckle. As long as the hosts stay in the `k3s-server`/`k3s-agent` groups, Buckle puts k3s back: drift correction re-applies a host's modules (the repo's notes put that at about 15 minutes), which reinstalls the binary, config and unit and starts a fresh cluster. Whether that's what you want, or whether you should take the hosts out of the groups first, depends on why you're resetting.

1. Agents first, one at a time:

   ```sh
   ssh root@clusterpi-worker1 /usr/local/bin/k3s-agent-uninstall.sh
   ```

   Repeat for `clusterpi-worker2` to `clusterpi-worker4`.
2. Then the server:

   ```sh
   ssh root@clusterpi-leader /usr/local/bin/k3s-uninstall.sh
   ```

3. Let Buckle bring k3s back, or start a rollout. On the empty API, `argocd-seed` installs Argo CD and `workloads/argocd-root` creates `1-meta-labk3s`.

## Check it worked

`kubectl --context labk3s get nodes` (with a [fresh admin kubeconfig](get-kubectl-access.md)) shows the nodes with a young `AGE`, and `kubectl --context labk3s -n argocd get applications` fills up as Argo CD syncs.

## If it didn't

The `k3s-server` and `k3s-agent` checks in Buckle say which host is stuck. Then go through the list in [Replace or re-create the server](replace-or-re-create-the-server.md#steps): the workers, TKA's CA, Backstage's token.
