# Deploy a NAS compose project

Use this to change or update `media` or `o11y` on the NAS, or to add a project. Buckle can't do
this: DSM has no apt and Buckle doesn't run containers.

**Before you start:** `ssh -J cedi@nyx king@nas.local`, and DSM's web UI
(`https://nas.sphinx-map.ts.net`) for Container Manager. The projects are listed in
[Synology NAS](../reference/nas.md#compose-projects).

!!! warning "`media` has drifted"
    The NAS's `media` project runs only Jellyfin; the repo's still defines Nginx Proxy Manager
    on ports 80, 81 and 443. Deploying the repo's file as it is would bring that container back.
    Decide first whether it should exist, and fix the repo or the NAS to match.

1. See how the NAS's copy differs from the repo's, from the repo root:

    ```sh
    ssh -J cedi@nyx king@nas.local 'cat /volume1/docker/o11y/docker-compose.yaml' | diff - nas/o11y/docker-compose.yaml
    ```

    Only the change you mean to deploy should show up (`<` is the NAS, `>` the repo).

2. Commit the change to `nas/<project>/` first, so the repo stays the record.

3. Copy the directory to the NAS. The repo's README says:

    ```sh
    rsync -a nas/o11y/ nas:/volume1/docker/o11y/
    ```

    !!! warning "Unverified"
        `nas` is an SSH alias the repo doesn't define; spelled out it's
        `rsync -a -e "ssh -J cedi@nyx" nas/o11y/ king@nas.local:/volume1/docker/o11y/`. A dry run
        of that (`-n`) on 2026-11-26 was refused with `Permission denied`, which is what DSM
        answers when its rsync service (Control Panel > File Services > rsync) is off. Turn it
        on, or copy the files another way, and check with step 1 afterwards.

4. In DSM, open Container Manager > Project, select the project and rebuild it. For a new
    project, create it there with the directory `/volume1/docker/<project>` and its
    `docker-compose.yaml`.

!!! note
    The images are tagged `latest`. Whether a rebuild pulls newer images isn't recorded here;
    Container Manager's project actions decide that.

## Check it worked

```sh
ssh -J cedi@nyx king@nas.local 'sudo /usr/local/bin/docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Label \"com.docker.compose.project\"}}"'
```

Each container of the project is `Up` (and `(healthy)` where it has a health check), with the
project's name in the last column. Then, from isa:

```sh
ssh cedi@isa "bash -c 'curl -s http://192.168.0.64:8096/health; echo; curl -s -o /dev/null -w \"%{http_code}\n\" http://192.168.0.64:9116/; curl -s -o /dev/null -w \"%{http_code}\n\" http://192.168.0.64:8123/healthz'"
```

`Healthy` (Jellyfin), `200` (snmp-exporter), `200` (cAdvisor). The `Synology Dashboard` in
Grafana (folder Applications) fills again within a minute or two.

## If it didn't

- A container restarts in a loop: its log in Container Manager, or
  `sudo /usr/local/bin/docker logs <name>` on the NAS.
- Jellyfin up on the LAN but not at `https://stream.sphinx-map.ts.net`:
  [Re-create the NAS's Tailscale serve config](recreate-the-nas-tailscale-serve-config.md).
