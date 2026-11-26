# Add a tsidp relying party

Use this when an app should let people sign in with their tailnet login
through tsidp (`https://idp.sphinx-map.ts.net`), the way Buckle, DSM, both
Argo CDs, Backstage and Grafana do.

**Before you start:** you're in `group:admins` (only admins get tsidp's admin
UI and dynamic client registration), and you know the app's redirect URI.

1. Register the client. Either open `https://idp.sphinx-map.ts.net` from a
   tailnet device and add the client in tsidp's admin UI, or use dynamic
   registration at `https://idp.sphinx-map.ts.net/register` (Buckle's client
   `buckle` was registered that way). Spell the redirect URI exactly as the
   app sends it: DSM's `https://nas.sphinx-map.ts.net` has to match with no
   trailing slash, and Buckle's is `https://buckle.sphinx-map.ts.net/api/v1/auth/callback`.
2. Store the client ID and secret where the app reads secrets: for Buckle
   that's `/etc/buckle/server.env` on isa (`OIDC_CLIENT_ID`,
   `OIDC_CLIENT_SECRET`); for a Kubernetes app, its SOPS secret in
   SpechtLabs/k8s-deployment. Never in a doc or a catalog file.
3. Configure the app with issuer `https://idp.sphinx-map.ts.net`. Clients
   authenticate at `/token` with `client_secret_post` or
   `client_secret_basic`; ID tokens are RS256. The `email` claim is the
   tailnet login with the issuer's host appended
   (`cedi@github.idp.sphinx-map.ts.net`).
4. Give the app's backend a path to tsidp. Where it runs decides how:
   - On a homelab host or the NAS (calls tsidp over the tailnet): the device
     needs `tag:tsidp-client` ([Retag a device](retag-a-device.md)).
   - On labk3s: through the egress proxy `k3s-idp-egress`, which carries
     `tag:tsidp-client` ([`apps/tailscale/cluster/labk3s/ts-egress-idp.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/tailscale/cluster/labk3s/ts-egress-idp.yaml)).
   - Off the tailnet (specht-labs' Argo CD, Backstage, Grafana): over Funnel,
     tsidp's public address. The policy doesn't apply.
5. Record it in the catalog: the app's Component gets
   `consumesApis: [api:tsidp-oidc]`. The API carries
   `specht-labs.de/tailnet-client-tag: tag:tsidp-client`, so every consumer
   lands in the one grant `tag:tsidp-client -> tag:tsidp tcp:443`; there's no
   per-app grant to write.
6. If the app maps roles from a `groups` claim, add a capability grant in
   [`tailscale/policy/grants.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/grants.yaml),
   modelled on `grant-tsidp-grafana-admins`
   ([Change a grant annotations can't express](change-a-grant-annotations-cant-express.md)).
   Keep `ip: ['tcp:443']`.
7. Push, then [merge Backstage's pull request](review-and-merge-the-policy-pull-request.md)
   if the policy changed.

## Check it worked

```sh
curl -s https://idp.sphinx-map.ts.net/.well-known/openid-configuration | jq .issuer
```

prints `"https://idp.sphinx-map.ts.net"`. Sign in to the app as a user who
should get in, and as one who shouldn't (if the app restricts by claim).
For a backend on the tailnet, `tailscale whois <its-ip>` shows
`tag:tsidp-client`.

## If it didn't

- tsidp refuses the redirect: compare the URI in the app and in tsidp's
  client character by character.
- The browser part works but the app can't finish the sign-in (its own
  calls to `/token`, the JWKS or `/userinfo` fail): the backend can't reach
  tsidp, usually because its device lacks `tag:tsidp-client`
  ([Debug "I can't reach X"](debug-cant-reach-a-service.md)).
- Dex (both Argo CDs) gave up for good when idp was unreachable at its
  start; since k8s-deployment `abc2dc6c` it has startup and liveness probes
  on `/healthz/live` (port 5558), so kubelet restarts it.
