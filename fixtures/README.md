# Facts fixtures

One file per host, named after its host id (the tailnet node name). `buckle validate --facts`
takes the host id from the file name and dry-plans that host: groups, module selection, vars,
templates and task specs.

The current files are **placeholders** written from the old Ansible inventory (Pi generation,
PoE HATs, Tailscale tags). Replace each with `sudo buckle facts` output from the real host once
it is enrolled (see `bootstrap/README.md`, step 5).

The repository is public, so captured facts are trimmed to the providers the config reads
(`os`, `hardware`, `tailscale` tags, `script`, `cloud`, hostname); see the `jq` filter in
`bootstrap/README.md`. Network interfaces, addresses, users and systemd units stay out.
