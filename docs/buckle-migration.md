# Homelab: Ansible → Buckle migration strategy

Status: implemented in this repo, validated, not yet deployed · 2026-11-17
Source: `~/src/gh/cedi/homelab-ansible` @ `d675b51` · Buckle 2.13.0

The code samples below were written before the build and are kept as the design record; where the
build changed them, [What changed while building it](#what-changed-while-building-it) says so and
the repo is authoritative.

## TL;DR

- **Buckle server runs on the NUC** as a static binary under systemd. It listens on the NUC's tailnet IP only and authenticates agents by **Tailscale identity**, so there are no tokens, no TLS setup and no SSH.
- **The inventory goes away.** Group membership comes from facts Buckle already collects: Raspberry Pi model, CPU arch, Tailscale tags, and host-ID globs. The only hand-kept lists left are the ones hardware can't tell you (which Pis have a PoE HAT, NUT shutdown order).
- **Rollout phases replace `serial:`, `k3s-upgrade.yml`, `k3s-reboot.yml` and `--check`.** A k3s upgrade becomes a one-line version bump that rolls out server first, then agents one at a time, gated on health checks.
- **The `artis3n.tailscale` role, the vaulted auth key and `--ask-pass` all go away.** Buckle's server mints single-use tagged auth keys for new hosts, and existing hosts keep their current Tailscale install.
- **This is a redesign, not a port.** Three copy-pasted 120-line Alloy configs become one template. The `k3s-ansible` fork (about 600 lines, mostly RedHat/Suse/airgap/firewalld branches you don't use) becomes two small modules. About 60 lines of `set_fact` regex for Pi detection become one fact lookup.
- **Known gaps:** templates can't read other hosts' data (no `hostvars`), there are no task loops, there's no container lifecycle (only image pulls), and the server has no HA. Each gap gets a design answer below. Two of the answers change your architecture on purpose: monitoring moves to an Alloy on every host, and the Synology NAS moves to its own track.

## What changed while building it

Checked against the real CLI (`buckle validate` with one facts file per host, plans run inside the
`ghcr.io/sierrasoftworks/buckle:2.13.0` container, rendered Alloy configs run through
`alloy validate`):

- **List fields can't come from a template.** Buckle coerces rendered strings to scalars only
  (`secrets/field.rs: coerce`), so `lines: '{{ vars.x }}'` is a type error. `pi-firmware` therefore
  uses one `file.ini` task per hardware concern (PoE+ HAT, Pi 5 cooling/PCIe, GPS/PPS wiring) with
  literal lists and scalar vars for the tunables. Separate `id`s keep them separate resources in
  the same `[all]` section. The `include buckle.txt` design below was dropped.
- **PoE HATs are a fact, not a host list.** Buckle has a `script` fact provider: `pi-facts` drops
  `/var/lib/buckle/facts.d/rpi`, which reads the HAT EEPROM, and the PoE task selects on
  `host.facts.script.rpi.hat_product contains "PoE"`.
- **Actions replace the reboot and upgrade playbooks.** Modules can declare operator-triggered
  tasks: `base` has *upgrade packages* and *reboot*, `k3s-agent` has *reboot*.
- **tsidp publishes release binaries**, so it's a plain `github.release` with a `-version` probe.
- **No `ansible-cleanup` module.** Each module removes its own Ansible leftovers (old apt `.list`
  files, `k3s*.service.env`, `/lib/systemd/system/phc2sys-eth0.service`, `/root/go/bin/tsidp`,
  standalone node_exporter) with `removal: leave`, so they never come back.
- **`only_if` isn't an idempotency guard** for `command.run`; `unless` is. The node_exporter
  retirement uses `unless`.
- **Defaults taken for the open questions**: Alloy runs on every host; the NAS stays out of
  Buckle (`nas/`); dotfiles keep installing their own packages; `hole` no longer scrapes a
  `jitsi_exporter` on :8080 (copy-paste from `meet`).
- **Answered once hosts enrolled (2026-11-17)**: `timepi-gps`, `lora` and `lyv` are dead, and
  `timepi` (a Pi 5) is the time server. It runs **ntpsec**, not chrony, with a hand-edited
  `ntp.conf` and gpsd options that `ptp-server` now reproduces. PTP is broken there (`ptp4l`:
  "driver rejected most general HWTSTAMP filter"; `phc2sys` exits on its arguments), so it sits
  behind `ptp_enabled: false`. Login shells are unmanaged by default (the Pis use fish, the NUC
  zsh), and PCIe Gen 3 on a Pi 5 depends on an NVMe fact from `pi-facts`.
- **timepi fixed (2026-11-18)**: the hand-edited gpsd options forced 115200 baud while the
  receiver talks 9600, so gpsd decoded nothing and ntpsec had no GPS source to number the PPS
  seconds with. Even decoded, NMEA at 9600 baud lands 150-600 ms after the second depending on
  the sentence load, too unsteady for ntpsec to select; ntpsec now follows gpsd's PPS (SHM 1),
  where gpsd numbers each PPS edge itself, and is stratum 1 within ~13 us of GPS. PTP had two more causes: the Pi 5's Ethernet only timestamps all packets or none
  (`hwts_filter full`), and kernel 6.12.34's PHCs refused every adjustment ("physical clock is
  free running", fixed upstream after the `ptp_vclock_in_use()` rework); 6.12.115 works.
  `ptp_enabled` is on, and GPS, PPS and the ptp4l port state are health checks.

---

## 1. Where the server lives: the NUC

| | NUC | Pi (e.g. `jumphost`) |
|---|---|---|
| Arch | amd64; server image and binary both supported | arm64; also supported |
| Rebooted by its own fleet? | Rarely. Not in k3s or ceph | `jumphost` is fine, but cluster Pis get rolled |
| Already "core infra" | yes (NUT proxy, tsidp, o11y collector) | no |
| Storage for SQLite + secrets | SSD | SD card / NVMe |

Use the NUC. The one real downside is that critical services pile up on one box. That risk is small here because **agents keep enforcing their last applied revision when the server is down**. A dead NUC only stops new changes from going out; it doesn't undo the current state.

How to run it:

- Run the **binary under systemd, not the container**. Tailscale auth needs tailscaled's LocalAPI socket (`/var/run/tailscale/tailscaled.sock`), and a host binary reaches it without bind-mount tricks.
- Bind gRPC `:7700` and UI `:7701` to the NUC's `100.x` address only.
- Back up `data_dir` (single-writer SQLite) and the secrets directory. A nightly `sqlite3 .backup` copied to the NAS is enough.
- Give the NUC an extra tag, `tag:buckle-server`, in the admin console, so the ACL grant can be narrow (see §3).

Sketch of `/etc/buckle/server.yaml`. It's assembled from documented keys but the docs don't show it as one file, so check it with `buckle server --help` and `buckle validate`:

```yaml
listen:
  grpc: "100.x.y.z:7700"       # NUC tailnet IP
  http: "100.x.y.z:7701"
  tls: { mode: none }          # WireGuard already encrypts the transport
source:
  git:
    url: https://github.com/cedi/homelab.git
    branch: main
    poll: 30s
    credentials: ...           # deploy key / fine-grained PAT if private
agents:
  auth: [tailscale]
  tailscale:
    allowed_tags: [tag:homelab, tag:core-infra, tag:core-services]
    provisioning:
      flow: client             # OAuth client, server mints tagged single-use keys
  desired_version: "2.13.0"    # fleet-wide agent version, bumped by renovate
secrets:
  providers:
    file: { root: /etc/buckle/secrets }
```

Later, add OIDC for the UI with your existing **tsidp** as the provider. Keep an `admin_acl` fallback, because tsidp also runs on the NUC and a broken tsidp would otherwise lock you out of the UI.

---

## 2. Target repo layout (this repo)

```
homelab/
├── buckle.yaml              # fleet.groups, vars overlays, secrets, rollout phases
├── vars/
│   ├── defaults.yaml
│   ├── pi.yaml  pi4-poe.yaml  pi5.yaml
│   ├── k3s.yaml
│   └── o11y-homelab.yaml  o11y-spechtlabs.yaml
├── modules/
│   ├── base/                # hostname, locales, admin user + shell, unattended-upgrades
│   ├── dotfiles/
│   ├── tailscale/           # apt repo + package (keeps it updated) + `tailscale set` flags
│   ├── pi-firmware/         # config.txt include + cmdline.txt tokens + reboot handler
│   ├── pi-tools/            # rpi-clone (Pi 5)
│   ├── rpi-exporter/
│   ├── alloy/               # one template, per-role fragments from vars
│   ├── nut-client/          # replaces geerlingguy.nut_client + nut_shutdown_behavior
│   ├── nut-server/
│   ├── k3s-server/
│   ├── k3s-agent/
│   ├── ptp-server/
│   ├── tsidp/
│   └── ansible-cleanup/     # temporary: removes Ansible leftovers, deleted after cutover
├── fixtures/facts/*.json    # `buckle facts` captures for CI planning
├── .mise.toml               # buckle CLI pinned via the github: backend
├── renovate.json            # regex managers for version pins in vars/
└── .github/workflows/validate.yml   # buckle validate + plan per fixture
```

Put the CLI on your Mac with `mise use github:SierraSoftworks/buckle@2.13.0` (no Homebrew tap), and pin it to match `agents.desired_version`.

---

## 3. Tailscale: what's native, and what stays a module

**What Buckle does natively, and what to use it for:**

| Feature | Use |
|---|---|
| Agent transport over tailnet (plaintext gRPC inside WireGuard) | All agents. No certificates to manage. |
| Agent identity = tailnet node (LocalAPI `whois`) | Replaces bootstrap tokens. `host.id` is the tailnet node name. |
| `allowed_tags` auto-registration | Hosts tagged `homelab` / `core-infra` / `core-services` register themselves; anything else waits for approval in the UI. |
| `host.facts.tailscale.{tags,ips,online,…}` | **Group selectors.** Your tags already encode roles (`o11y-collector`, `core-infra`, …). |
| Server-side key provisioning (OAuth client, `auth_keys` scope) | New hosts join with a one-hour, single-use join command that installs Tailscale and the agent with the right tags. **This replaces the vaulted `tailscale_authkey` and `insecurely_log_authkey: true`.** |
| Installer `--tailscale-tags`, `--tailscale-arg` | Sets the tags and `--ssh` at first join. |

**What isn't native:** there's no task kind for `tailscale up` flags, ACLs, exit nodes or Tailscale SSH settings. The `tailscale` module covers this:

```yaml
# modules/tailscale/module.yaml (sketch)
name: tailscale
facts:
  provides: [tailscale]
tasks:
  - apt.repository:
      name: tailscale
      uri: https://pkgs.tailscale.com/stable/debian
      suites: ['{{ host.facts.os.codename }}']
      components: [main]
      signed_by: { url: 'https://pkgs.tailscale.com/stable/debian/{{ host.facts.os.codename }}.noarmor.gpg' }
  - apt.package: { name: tailscale, state: latest }
  - systemd.unit: { name: tailscaled, enabled: true, active: true }
  - id: tailscale-prefs
    command.run:
      # `tailscale set` changes prefs without re-auth, unlike `tailscale up`
      run: ['tailscale', 'set', '--ssh', '--advertise-exit-node={{ vars.tailscale.exit_node }}']
      unless: "tailscale debug prefs | jq -e '.RunSSH == true and ...'"
    removal: leave
health:
  - command: { run: ['tailscale', 'status', '--peers=false'] }
```

Tags are deliberately left out of the module. They're set once at join and act as identity, and changing them means re-auth, which you do in the admin console.

**Tailnet policy additions** (in whatever repo holds your policy):

```jsonc
"tagOwners": { "tag:buckle-server": ["autogroup:admin"] },
"grants": [
  { "src": ["tag:homelab", "tag:core-infra", "tag:core-services"],
    "dst": ["tag:buckle-server"], "ip": ["tcp:7700"] },
  { "src": ["autogroup:admin"], "dst": ["tag:buckle-server"], "ip": ["tcp:7701"] }
]
```

Create a Tailscale OAuth client with `auth_keys` write scope, limited to your homelab tags, and give it to the server as a secret.

---

## 4. Replacing the inventory with facts

Labels can't be declared in git; they come only from `--label` at install time or the UI. Instead of fighting that, derive as much as possible from facts, which are always correct:

```yaml
# buckle.yaml (excerpt)
version: 2
fleet:
  groups:
    pi:        'host.facts.hardware.raspberry_pi != null'
    pi5:       'host.facts.hardware.raspberry_pi != null && host.facts.hardware.raspberry_pi.version == 5'
    cm4:       'host.facts.hardware.raspberry_pi != null && host.facts.hardware.raspberry_pi.compute_module'
    k3s-server: 'host.id == "clusterpi-leader"'
    k3s-agent:  'host.id like "clusterpi-worker*"'
    ceph:       'host.id like "storagepi-ceph*"'
    blades:     'host.id like "blade-pi*"'
    # Hardware a fact can't see: PoE+ HAT fan curve
    poe-hat:    'host.id like "clusterpi-worker*" || host.id == "lora"'
    nut-server: 'host.id == "nuc"'
    nut-late:   'host.id == "jumphost" || host.id == "timepi"'
    nut-early:  'host.facts.hardware.raspberry_pi != null && !(host.id == "jumphost" || host.id == "timepi")'
    o11y-collector: 'host.facts.tailscale != null && host.facts.tailscale.tags contains "tag:o11y-collector"'
    spechtlabs: 'host.id == "hole" || host.id == "meet"'
```

What this fixes compared with `inventory/homelab.yaml`:

- `raspberry_pi_4` / `raspberry_pi_5` were maintained by hand, and `storagepi-ceph*` reached Pi 5 only through a `children:` quirk. Now hardware decides.
- The 60-line `pi-version.yml` regex parser and the `os-detection.yml` set_facts are replaced by `host.facts.hardware.raspberry_pi.{version,model,compute_module}` and `host.facts.os.{family,id,codename,version}`.
- Per-host `ansible_user` (`pi`, `root`, `cedi`, `king`) and `--ask-pass` disappear, because agents run as root locally.

Vars layering replaces group_vars and host_vars:

```yaml
vars:
  - file: vars/defaults.yaml
  - { when: 'host.groups contains "pi"',      file: vars/pi.yaml }
  - { when: 'host.groups contains "poe-hat"', file: vars/pi4-poe.yaml }
  - { when: 'host.groups contains "pi5"',     file: vars/pi5.yaml }
  - { when: 'host.groups contains "spechtlabs"', file: vars/o11y-spechtlabs.yaml }
  - when: 'host.id == "timepi"'
    values:
      rpi: { enable_uart: true, dtparams: [i2c_arm=on, i2s=on, spi=on, uart0=on],
             dtoverlays: [pps-gpio,gpiopin=18], cmdline_remove: ['console=serial0,115200'] }
  - when: 'host.id == "hole"'
    values: { tailscale: { exit_node: true } }
```

**No `hostvars`.** Only two things read another host's data today:

1. `k3s api_endpoint` (`groups['server'][0]`): becomes `vars.k3s.server: clusterpi-leader` and resolves through MagicDNS.
2. The NUC's Alloy scrape list, which hard-codes 16 hostnames and 11 Tailscale IPs: §6 removes it.

---

## 5. Concept mapping: Ansible → Buckle

| Today (Ansible) | Buckle-native replacement |
|---|---|
| `ansible-playbook --check` | `buckle plan` (exit 0/2/1) in CI against `fixtures/facts/*.json`, plus the live plan in the UI before approval |
| `serial: 1` in `k3s-upgrade.yml` / `k3s-reboot.yml` | `rollout.phases` with `parallel: 1`, `bake`, `approval: if_destructive` |
| "Verify rpi_exporter is responding" via `uri` | Module `health:` (`http`, `systemd`, `command`) that gates the rollout and repeats during bake |
| `register` + `when: x.changed` + manual `daemon_reload` | `notify` → `handlers`; `systemd.unit` handles daemon-reload |
| `lineinfile` soup on `config.txt` / `cmdline.txt` | A template plus `include` for config.txt; `file.tokens` for cmdline.txt |
| GitHub API "latest" lookup on the controller | `github.release` with a pinned `version`, `probe`, and renovate bumps |
| `ansible-vault` blobs in the inventory | `secrets:` with the file provider on the NUC; fingerprinted in plans, delivered only to hosts that use them |
| No drift detection | Every agent re-plans every 15 minutes, corrects drift, reports hand edits, and never removes or reboots on its own |
| Galaxy deps (`geerlingguy.*`, `artis3n.*`, `grafana.grafana`) | None |
| Removing a role does nothing | Removing a task removes what it created (`removal: cleanup` is the default; use `leave` to opt out) |

---

## 6. Module-by-module design

### base
- `hostname.set: { name: '{{ host.id }}' }`
- Locales: use `apt.package: locales-all` instead of `locale-gen`. It ships every locale precompiled, so no command is needed. Write `/etc/default/locale` and `/etc/profile.d/lang.sh` with `file.copy`.
- `user.account: { name: '{{ vars.admin_user }}', shell: /usr/bin/fish }`. Optionally add `ssh.authorized_key` with `exclusive: true` if you want Buckle to own SSH keys, though Tailscale SSH makes this mostly moot.
- Add `unattended-upgrades` (new). Reboots are handled in §7.

### dotfiles
- `git.repository: { repo: https://github.com/cedi/dotfiles.git, path: '/home/{{ vars.admin_user }}/.dotfiles', ref: main, owner: ... }` with `notify: [install]`.
- A handler runs `bash install_linux.sh --yes --preset {{ vars.dotfiles_preset }}` as `user: {{ vars.admin_user }}`, so it runs only when the repo changes. An unguarded `command.run` would run on every drift check.
- Caveat: the installer is opaque to Buckle, so packages it installs are never tracked or removed. **Suggestion:** move the system package list from the dotfiles script into `base` as `apt.package: { names: [...] }`, and leave the dotfiles for user-level config only.

### pi-firmware (replaces `raspberrypi/firmware-config.yml`)
Without loops, one `file.line` per dtoverlay doesn't work. Use the firmware's own `include` directive instead:

```yaml
tasks:
  - file.template:
      src: buckle.txt.j2               # loops over vars.rpi.* in Jinja
      dest: /boot/firmware/buckle.txt
    notify: [reboot]
  - file.block:
      path: /boot/firmware/config.txt
      marker: "# {mark} BUCKLE"
      block: "[all]\ninclude buckle.txt"
    notify: [reboot]
  - file.tokens:
      path: /boot/firmware/cmdline.txt
      present: [cgroup_enable=cpuset, cgroup_memory=1, cgroup_enable=memory]
      absent: '{{ vars.rpi.cmdline_remove }}'   # verify list templating with `buckle validate`
    notify: [reboot]
handlers:
  reboot: { system.reboot: { delay: 10s, timeout: 3m } }
```

`buckle.txt.j2` holds the dtoverlays, dtparams, fan trip points (`poe_fan_temp*` for PoE HATs, `fan_temp*` for Pi 5), `pciex1_gen` (only when `raspberry_pi.version >= 5`), and `enable_uart`.

**Adoption step:** the `dtoverlay=`/`dtparam=` lines Ansible added still sit in `config.txt`. `ansible-cleanup` removes them with `file.line` `state: absent`, in the same rollout that introduces `buckle.txt`, so the device ends up with one reboot and no duplicates.

### pi-tools
`git.repository` for `geerlingguy/rpi-clone` into `/opt/rpi-clone`, then `file.symlink` into `/usr/local/sbin`, gated `when: 'host.groups contains "pi5"'`. This replaces a `cp` that ran on every play.

### rpi-exporter
```yaml
tasks:
  - github.release:
      repo: cedi/rpi_exporter
      version: '{{ vars.rpi_exporter_version }}'   # renovate-pinned, not "latest"
      asset: 'rpi_exporter_{version}_linux_{arch}.tar.gz'
      extract: rpi_exporter
      dest: /usr/local/bin/rpi_exporter
      mode: "0755"
      probe: [rpi_exporter, --version]
    notify: [restart]
  - user.account: { name: rpi_exporter, system: true, shell: /usr/sbin/nologin, groups: [video] }
  - file.template: { src: rpi_exporter.service.j2, dest: /etc/systemd/system/rpi_exporter.service }
    notify: [restart]
  - systemd.unit: { name: rpi_exporter, enabled: true, active: true, daemon_reload: true }
handlers:
  restart: { systemd.restart: { name: rpi_exporter } }
health:
  - http: { url: http://localhost:9243/, expect: { body_contains: Metrics } }
```
The duplicate `rpi_exporter.service.j2` in `roles/raspberrypi/templates/` goes away.

### alloy: the deliberate architecture change
Today the NUC scrapes 16 hosts by name and 11 Tailscale exporters by **hard-coded 100.x IP**. Buckle can't build that list from fleet data (no hostvars), and the hard-coded list was already fragile.

**New model:** every host runs Alloy, scrapes its own exporters on `localhost`, and remote-writes directly to Mimir and Loki.
- **Drop `node_exporter`.** Alloy embeds it as `prometheus.exporter.unix`, which means one fewer binary, role and port.
- Each host scrapes its own tailscaled metrics locally, so the IP list is gone.
- Adding a host requires no change to the collector.
- The NUC keeps its collector-only parts: the OTLP receiver (4317/4318 → Tempo/Mimir/Loki) and the NAS targets (SNMP, cAdvisor).
- Cost: roughly 100–150 MB RSS per Pi. That's fine on 4 GB+ boards. If it isn't, fall back to `node_exporter` via `github.release` and keep a short static scrape list in `vars/`.

Module shape:
- `apt.repository` for Grafana (`https://apt.grafana.com stable main`, `signed_by.url: https://apt.grafana.com/gpg.key`), `apt.package: { name: alloy, version: '{{ vars.alloy_version }}' }`
- `systemd.dropin` with `User=root`. The `alloy_user_groups` list is redundant when running as root, so drop it.
- `file.template: config.alloy.j2` with `validate: [alloy, fmt, '{path}']`, `notify: [reload]`
- `file.line` on `/etc/default/alloy` for `CUSTOM_ARGS` (collector only)
- `health: http://localhost:12345/-/ready`

`config.alloy.j2` is one file with Jinja blocks driven by vars: `vars.o11y.{loki_url, mimir_url, tempo_url}` (homelab vs spechtlabs endpoints), `vars.o11y.extra_log_paths` (jitsi/prosody, letsencrypt), `vars.o11y.local_scrapes` (jitsi_exporter :8080, rpi_exporter :9243, blade exporter :9666), and `{% if host.groups contains "o11y-collector" %}` for the OTLP receiver and NAS scrapes. Note that `hole` and `meet` define an `otelcol.exporter.otlphttp "tempo"` that nothing feeds today. Keep it only on the collector.

### nut-server (NUC) and nut-client (Pis)
- **Template whole files** (`nut.conf`, `upsd.conf`, `upsd.users`, `ups.conf`, `upsmon.conf`, `upssched.conf`, `upssched-cmd`) instead of `lineinfile`/`blockinfile`. They're small, and owning the whole file is what makes drift detection meaningful. Today `geerlingguy.nut_client` and `nut_shutdown_behavior` both edit `upsmon.conf` line by line and can fight each other.
- `upssched-cmd`: `file.template` with `mode: "0750"`, `group: nut`. Early/late behaviour comes from the `nut-early` / `nut-late` group overlays.
- Passwords move to `secrets.nut_admin_password` and `secrets.nut_monitor_password`. **`secret` and `foobar2342` are committed in plain text today (inventory and role defaults), so rotate them during the move.**
- Handlers: `systemd.restart` for `nut-server` / `nut-monitor`. Health: `command: { run: [upsc, 'ups@{{ vars.nut.server }}'] }`.
- While you're in there, replace the deprecated `slave` with `secondary` in the `MONITOR` line.

### k3s-server / k3s-agent (replaces the `k3s-ansible` fork)
Drop everything that doesn't apply to Debian/Pi OS on arm64: RedHat, Suse, Arch, firewalld, airgap, SELinux, the iptables-legacy flip for iptables < 1.6.2, and the kubeconfig `fetch` to the controller.

```yaml
# k3s-agent (sketch)
needs: [base]
tasks:
  - sysctl.param: { name: net.ipv4.ip_forward, value: "1" }
  - sysctl.param: { name: net.ipv6.conf.all.forwarding, value: "1" }
  - github.release:
      repo: k3s-io/k3s
      version: '{{ vars.k3s.version }}'        # e.g. 1.31.1+k3s1
      asset: 'k3s-{arch}'                      # arm64 → k3s-arm64
      dest: /usr/local/bin/k3s
      mode: "0755"
      probe: [k3s, --version]
      probe_regex: 'k3s version v(\S+)'
    notify: [restart]
  - file.template:
      src: config.yaml.j2                      # server: https://{{ vars.k3s.server }}:6443, token: {{ secrets.k3s_token }}
      dest: /etc/rancher/k3s/config.yaml
      mode: "0600"
    notify: [restart]
  - file.copy: { src: k3s-agent.service, dest: /etc/systemd/system/k3s-agent.service }
    notify: [restart]
  - systemd.unit: { name: k3s-agent, enabled: true, active: true, daemon_reload: true }
handlers:
  restart: { systemd.restart: { name: k3s-agent } }
health:
  - systemd: { unit: k3s-agent, min_uptime: 60s }
```

- Flags move from `ExecStart` into k3s's native `config.yaml`: `disable: [traefik]`, `disable-network-policy: true`. The unit file becomes static, and the `.service.env` token juggling and `K3S_TOKEN` regex deletes go away.
- `k3s-server` is the same pattern, plus `command` health `k3s kubectl get nodes`. You have one server today, which means the **SQLite/kine datastore, not etcd**. Keep that. `--cluster-init` only matters if you add servers.
- **An upgrade is a var bump.** The rollout runs the server phase, bakes, then agents `parallel: 1`, bakes, then goes on. `k3s-upgrade.yml` and its `.bak` service-file dance go away.
- **`k3s-reset.yml` is not ported.** You could attach `remove: [k3s-uninstall.sh]` to a `command.run`, but Buckle runs `remove` whenever the *rendered command changes*, so a refactor could wipe the cluster. Keep reset as a manual runbook.
- **k3s v1.31.1 is past end of life.** Migrate on the *same* version first, then upgrade one minor at a time through the phases. Don't combine the two.

### ptp-server (timepi; see the top of this doc for what changed)
- **Existing bug:** the role installs and starts **both chrony and ntpsec**, and both bind UDP/123 and try to discipline the clock. Pick chrony (its `refclock SOCK` setup already consumes gpsd and PPS) and drop ntpsec and its 2 KB `ntp.conf`.
- Today every run *restarts* chrony, gpsd and ntp unconditionally. Handlers restart them only when config changes.
- `phc2sys-eth0.service` moves from `/lib/systemd/system` to `/etc/systemd/system`. Add health checks: `systemd` for `gpsd`, `chrony`, `ptp4l@eth0`, `phc2sys-eth0`, plus `command: chronyc tracking`.
- **Question for you:** the PPS and UART firmware vars are set on `timepi`, but `ptp.yml` targets `timepi-gps`. Are these two devices, or is one a renamed leftover?

### tsidp (NUC)
- Today it runs `go install …@latest` as root on every play, which needs a Go toolchain on the NUC and reports `changed_when: false`, so restarts depend on a checksum side-channel.
- **Native:** `tailscale/tsidp` publishes release binaries, so it's `github.release` with a pinned version and a `-version` probe, and Go comes off the NUC.
- `TS_AUTHKEY` goes into `/etc/default/tsidp` as `{{ secrets.tsidp_authkey }}`. Drop the one-off legacy-state migration tasks after confirming `/data/tailscaled.state` exists.

### Synology NAS: own track, probably not Buckle
DSM isn't Debian (`apt.*` won't work), and Buckle has no container lifecycle beyond `docker.image` pulls. **The current role only copies compose files and never starts anything.** Options, best first:
1. Leave the NAS unmanaged by Buckle. Keep the compose files in this repo under `nas/`, and point DSM Container Manager "Projects" at them.
2. Experimental: run the static `buckle-linux-amd64` agent on DSM, with `file.copy` and `command.run: docker compose up -d` guarded by `unless`. A DSM update may wipe the unit.

### hole, meet (external VPS)
These are a good fit as-is. They're already on the tailnet, they dial out, and the only per-host differences are o11y endpoints and the exit-node flag.

---

## 7. Rollouts and reboots

```yaml
rollout:
  trigger: auto            # start with manual during migration
  on_failure: pause
  settle: 2m
  phases:
    - { name: canary,     select: 'host.id == "blade-pi4"', bake: 10m }
    - { name: k3s-server, select: 'host.groups contains "k3s-server"', approval: if_destructive }
    - { name: k3s-agents, select: 'host.groups contains "k3s-agent"', parallel: 1, approval: if_destructive }
    - { name: ceph,       select: 'host.groups contains "ceph"', parallel: 1, approval: if_destructive }
    - { name: core,       select: 'host.id == "nuc" || host.id == "hole" || host.id == "meet"', parallel: 1, approval: required }
    - { name: rest,       select: 'true', parallel: 3 }
```

Reboot semantics to design around:
- **Drift correction never reboots.** It logs the request for the next apply. A rollout reboots, inside its phase's parallelism, and waits for the host to reconnect. So the `parallel: 1` phases give you `k3s-reboot.yml` for free whenever a change needs a reboot.
- **OS-patch reboots for k3s nodes** (`/var/run/reboot-required`) should be handled by **kured** inside the cluster (it drains, reboots and uncordons one node at a time), not by Buckle. For non-cluster Pis, an optional `system.reboot` with `only_if: test -f /var/run/reboot-required` fires on the next rollout.
- The NUC hosts the server. The server resumes interrupted rollouts after a restart, but keep the NUC in an `approval: required` phase anyway.

---

## 8. Secrets

Server-side file provider: `/etc/buckle/secrets/<name>`, mode 0600, root-owned, backed up with the DB.

| Secret | Source today | Notes |
|---|---|---|
| `k3s_token` | inventory vault blob | Same value. Changing it breaks node joins. |
| `nut_admin_password`, `nut_monitor_password` | **plain text** in inventory and role defaults | Rotate |
| `tsidp_authkey` | role var (empty) | Optional |
| Tailscale OAuth client secret | new | For server-side key provisioning |
| `tailscale_authkey` | inventory vault blob | **Retired.** Revoke it in the admin console. |

Get them out of Ansible once with `ansible-vault view`/`decrypt`, then shred the vault password file. If you use a password-manager CLI, the `exec` provider (`secrets.providers.exec.allow`) can read from it directly instead.

---

## 9. Migration phases

Each phase can be undone without touching the next.

**Phase 0: Prep (no host changes)**
- Scaffold this repo (§2), pin `buckle` in `.mise.toml`, and add CI that runs `buckle validate`.
- Add the tailnet policy grants and `tag:buckle-server`, and create the OAuth client.
- Pull the vault secrets out (§8).
- Freeze the Ansible repo: no new features. It's broken anyway, because `site.yml` imports a `metrics-collector.yml` that doesn't exist.

**Phase 1: Server on the NUC**
- Install the binary, add the systemd unit and `server.yaml` (§1), and back up `/data`.
- Point it at this repo with **`rollout.trigger: manual` and no modules selected**.

**Phase 2: Enroll agents, observe only**
- On each existing host (via Tailscale SSH), run the server's join command. Tailscale is already present, so only the agent gets installed. Hosts with allowed tags register automatically.
- **Gate:** on one Pi each of Pi OS Bookworm and any Ubuntu boxes, run `buckle facts` and confirm `os.family == "debian"`. The docs list Debian and Ubuntu, but Raspberry Pi OS isn't named. If it maps differently, every `apt.*` task needs rethinking, so check this before writing modules.
- Save `buckle facts` output for representative hosts into `fixtures/facts/` (Pi 4 with PoE HAT, Pi 5, CM4 blade, NUC, VPS) so CI can plan against them.
- Settle the unknown inventory entries: `lyn`, `lyv` and `lora` have no `ansible_host` and no role assignments. Are they live?

**Phase 3: Write modules, aim for no-op plans**
- Write `base`, `tailscale`, `rpi-exporter`, `pi-firmware` (with `ansible-cleanup`), and `dotfiles`.
- Iterate until `buckle plan` against live hosts shows only the changes you intend. That plan is your parity check against what Ansible left on disk.

**Phase 4: Roll out in increasing order of risk.** Each step is a PR, then a manual rollout trigger with approval:
1. `base`, `tailscale`, `rpi-exporter`, `pi-tools`
2. `pi-firmware` + `ansible-cleanup`. This is the first reboot-causing rollout and it exercises the phases.
3. `alloy`. This is a behaviour change, so watch Grafana for gaps. Remove the NUC's static scrape lists only after every host is reporting.
4. `nut-client`, `nut-server`. Test with `upsmon -c fsd` on the canary only, or by pulling a test client's network, and confirm the early/late ordering before trusting it.
5. `ptp-server` (with the chrony-only fix) and `tsidp`.
6. `k3s-server`, then `k3s-agent`, **on the current version**. The first apply rewrites unit files and moves flags into `config.yaml`, which causes one restart per node, one node at a time.

**Phase 5: Cutover**
- Switch `rollout.trigger: auto`. Drift correction is already on by default.
- Remove `ansible-cleanup`, archive `homelab-ansible` on GitHub (don't delete it yet), revoke the old Tailscale auth key, and rotate the NUT passwords.
- Add renovate regex managers for `vars/*.yaml` versions (k3s, alloy, rpi_exporter, tsidp) and for `agents.desired_version`.

**Phase 6: Make use of the new setup**
- Upgrade k3s from 1.31 one minor at a time.
- Add OIDC for the Buckle UI via tsidp.
- Add kured to the cluster for patch reboots.
- After 1–2 stable months, delete the Ansible repo.

---

## 10. Risks and open questions

| Risk | Mitigation |
|---|---|
| Pi OS not explicitly supported for `apt.*` | Phase 2 gate: check `os.family` before writing modules |
| Single server, SQLite, no HA | Agents keep enforcing their last revision when the server is down. Nightly DB backup. The server can be rebuilt from git plus the secrets dir. |
| `command.run` `remove` fires when the rendered command changes | No destructive `remove` hooks (no k3s uninstall). Give commands stable `id`s. |
| ~~Whole-field list templating~~ | Confirmed unsupported; per-concern tasks with literal lists instead |
| Escape hatches Buckle can't see into (dotfiles installer, `tailscale set`) | Keep them small and guarded with `unless`; move packages out of the dotfiles script |
| Buckle is a young project (2.x) | Keep the Ansible repo archived until it has been stable for a while |

Still open (defaults taken, see the top of this doc):
1. Nothing blocking. `lyn`, `lyv`, `lora` and `timepi-gps` are gone; `storagepi-ceph3` was
   offline at enrolment and still needs `enrol storagepi-ceph3 pi`.
