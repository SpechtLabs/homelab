# Call the Buckle API

Use this when the UI is too slow for what you want (scripting, watching a rollout from a terminal,
running an action on several hosts) or when you need an exact field the UI doesn't show. There's
no server-side CLI: `buckle` on your Mac only validates and plans locally, so the API is curl.

**Before you start:** your Mac on the tailnet, signed in as a member of `group:admins`. tsidp
signs you in by tailnet identity, so no password prompt appears. The snippets are bash/zsh; in
fish, run `bash` first.

1. Set the base URL and a cookie jar, and sign in:

    ```sh
    B=https://buckle.sphinx-map.ts.net
    J=~/.cache/buckle-api.jar
    mkdir -p ~/.cache
    curl -s -c "$J" -b "$J" -L -o /dev/null -w '%{http_code}\n' "$B/api/v1/auth/login"
    ```

    You should see `200`: the login redirects through tsidp and back, and the jar now holds
    `buckle_session` and `buckle_refresh`.
2. Check who you are:

    ```sh
    curl -s -b "$J" "$B/api/v1/me"
    ```

    You should see `"is_admin":true`. Without it, your tsidp token lacks the `buckle-admins`
    group claim (see [Server and agents](../reference/server-and-agents.md#sign-in)).
3. A `POST` needs a CSRF token in the `x-csrf-token` header. Define a helper that fetches one
    each time (`GET /api/v1/csrf` also sets the `buckle_csrf` cookie the header has to match):

    ```sh
    bpost() {  # bpost PATH JSON, e.g. bpost rollouts/wet.left.talk/resume '{"note":"fixed"}'
      local csrf
      csrf=$(curl -s -c "$J" -b "$J" "$B/api/v1/csrf" | jq -r .token)
      curl -s -b "$J" -H "x-csrf-token: $csrf" -H 'content-type: application/json' \
        -X POST "$B/api/v1/$1" -d "$2"
    }
    ```

    The how-to pages use `bpost` for every change they make through the API.
4. Parse responses that carry commit messages (rollouts, revisions) with Python, not `jq`.
    They can contain raw control characters, which `jq` rejects:

    ```sh
    curl -s -b "$J" "$B/api/v1/rollouts" | python3 -c '
    import json, sys
    for r in json.loads(sys.stdin.read(), strict=False)["items"][:5]:
        print(r["name"], r["state"], r["revision"][:8], r["triggered_by"])'
    ```

## Check it worked

`GET /api/v1/me` answers with your name. A `POST` returns JSON describing the changed object. A
`403` saying "The request is missing its CSRF token." means the header and cookie didn't match:
fetch a new token.

## If it didn't

- `401` on any call: the session expired, or the server restarted (sessions don't survive a
  restart). Repeat step 1.
- The login lands on a tsidp error page: tsidp on isa is down. Use
  [Sign in when tsidp is down](sign-in-when-tsidp-is-down.md). Its API is on
  `http://localhost:7701` through an SSH tunnel: skip step 1, set `B=http://localhost:7701`, and
  keep step 3, because a `POST` still needs the CSRF token there.
- The endpoints this homelab uses are listed in [Buckle API](../reference/api.md).
