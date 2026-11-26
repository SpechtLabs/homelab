# Buckle API

The server's HTTP API at `https://buckle.sphinx-map.ts.net/api/v1/`, as used in this homelab.
Routes checked against Buckle 2.22.0's source (`crates/buckle-server/src/web/routes.rs`). Sign-in
and the CSRF header: [Call the Buckle API](../how-to/call-the-buckle-api.md).

Every `POST` needs the `x-csrf-token` header matching the `buckle_csrf` cookie; most take
`{"note": "..."}` for the audit log, required where an action has `confirm: true`. Rollout paths
take the rollout's id or its three-word name.

## Session

| Method, path | Use |
|---|---|
| `GET /auth/login` | Start the OIDC sign-in (follow redirects) |
| `GET /csrf` | `{"token": ...}` and the `buckle_csrf` cookie |
| `GET /me` | Who you are, `is_admin` |
| `GET /readyz` (no `/api/v1`, no sign-in) | 200 when the server can work, 503 naming what can't |

## Hosts

| Method, path | Use |
|---|---|
| `GET /hosts` | All hosts (a JSON list): `id`, `status`, `connection`, `agent_version`, ... |
| `GET /fleet` | `hosts[].id` and fleet summary |
| `GET /hosts/{id}` | One host: `status`, `groups`, `applied_revision`, `health`, `actions`, `recent_runs` |
| `GET /hosts/{id}/facts` | The host's facts (input for `fixtures/facts/`) |
| `GET /hosts/{id}/health` | Its health readings |
| `GET /hosts/{id}/runs`, `GET /hosts/{id}/runs/{run}` | Runs (`state`, `outcome`, `changes`) |
| `POST /hosts/{id}/actions/{module}/{action}` | Run a module action now; returns `{"run_id"}` (202) |
| `POST /hosts/{id}/pause`, `/resume`, `/approve` | Pause, resume, admit a pending host |
| `POST /hosts/{id}/drift` | Run the drift check now |
| `DELETE /hosts/{id}` | Forget the host and its history |
| `GET /attention` | What the **Needs attention** bell lists |

## Rollouts

| Method, path | Use |
|---|---|
| `GET /rollouts` | `items[]`: `name`, `state`, `revision`, `revision_message`, `triggered_by`, `current_phase` |
| `GET /rollouts/{id}` | Detail: `phases[].hosts[]` with `state`, `plan_changes`, plus `plans`, `events`, `limits` |
| `GET /rollouts/{id}/plans` | Every host's plan |
| `POST /rollouts` | Start an action rollout: `{"module","action","selector","note"}` |
| `POST /rollouts/{id}/pause`, `/resume`, `/retry`, `/expedite`, `/rollback`, `/abort` | Whole-rollout decisions |
| `POST /rollouts/{id}/approve`, `/reject` | At an approval gate (no phase here asks for one) |
| `POST /rollouts/{id}/hosts/{host}/retry`, `/skip`, `/force`, `/expedite` | One host's decisions; `?workload=` for a cluster's workload |
| `POST /rollouts/{id}/hosts/{host}/continue` | `{"waive_checks": ["module/check"], "note"}` |
| `POST /rollouts/{id}/phases/{phase}/expedite` | Count a phase's baking hosts as baked |
| `GET /revisions`, `GET /revisions/{id}` | Commits the server has seen, with validation |
| `POST /revisions/{id}/rollout` | Start a rollout of a revision by hand |

## Other

| Method, path | Use |
|---|---|
| `GET /schedules`, `GET /schedules/{name}` | Schedules, next run, latest result |
| `GET /actions` | Every action the fleet offers and who offers it |
| `GET /actions/runs` | One-off action runs across the fleet |
| `GET /units/paused`, `POST /units/suspend`, `POST /units/resume` | Suspend one module on one host |
| `GET /audit` | The audit log |
| `GET /events` | Live events |

Responses carrying commit messages can contain raw control characters: parse them with
`json.loads(..., strict=False)` rather than `jq`. A `401` means the session is gone (it doesn't
survive a server restart): sign in again.
