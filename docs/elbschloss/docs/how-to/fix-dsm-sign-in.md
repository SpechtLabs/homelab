# Fix DSM sign-in

Use this when signing in to DSM at `https://nas.sphinx-map.ts.net` through SSO (tsidp) fails
for someone who should get in.

**Before you start:** an admin account on DSM that signs in without SSO, admin access to
tsidp's admin UI at `https://idp.sphinx-map.ts.net` (group:admins has it), and
`ssh -J cedi@nyx king@nas.local`.

1. Check the NAS reaches tsidp:

    ```sh
    ssh -J cedi@nyx king@nas.local 'curl -s -o /dev/null -w "%{http_code}\n" https://idp.sphinx-map.ts.net/.well-known/openid-configuration'
    ```

    `200`. Anything else: check the NAS still carries `tag:tsidp-client` (`tailscale status
    --json` or the admin console). Without it the policy won't let the NAS reach tsidp; that's
    how sign-in broke on 2026-11-25, when the NAS lost its old `tag:core-infra`.

2. Check tsidp itself is up:

    ```sh
    ssh cedi@isa "bash -c 'systemctl is-active tsidp'"
    ```

    `active`. If not, see the [Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/)
    for tsidp.

3. Compare the redirect URI on both sides. It has to be exactly `https://nas.sphinx-map.ts.net`,
    without a trailing slash, in both places:
    - DSM: Control Panel > Domain/LDAP > SSO Client.
    - tsidp's admin UI: the `synology` client.

4. Check the person is in `group:synology-users`. The tsidp capability grant for the
    `synology` resource is for that group, and it's also the group that may reach `svc:nas` at
    all. Members are Backstage Users and Groups in SpechtLabs/backstage_resources; adding someone
    is in the [Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/).

## Check it worked

Open `https://nas.sphinx-map.ts.net` in a private window and sign in with SSO. DSM's desktop
should load as the user.

## If it didn't

- `http://nas.sphinx-map.ts.net` (plain HTTP) never answers: `svc:nas` has no port 80. Use
  `https://`.
- DSM itself down: [Respond to an availability alert](respond-to-an-availability-alert.md).
