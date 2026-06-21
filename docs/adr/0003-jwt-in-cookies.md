# ADR-0003 — JWT in HttpOnly cookies, not localStorage

**Status:** Accepted
**Date:** 2026-05-04

## Context

The first SPA cut put the access JWT in localStorage, attached as
`Authorization: Bearer …` by the browser client. It was fast to build but
has one defining failure mode: **any XSS payload can lift the token in one
line of JS** (`localStorage.getItem("carbonizer-auth")`). For a carbon-
tracking app that connects bank credentials downstream, that's the wrong
trade.

The alternatives we considered:

* **localStorage + tight CSP**: still leaks the token to a same-origin
  injection (e.g. dependency compromise). The CSP raises the bar but
  doesn't remove the failure mode.
* **In-memory only + silent refresh from a cookie**: cookies become the
  source of truth anyway, and a hot-tab refresh flow is fiddly across
  the navigation timing of an SPA.
* **HttpOnly cookies with double-submit CSRF**: cookies are inaccessible
  to JS (the access cookie is `HttpOnly`), so XSS cannot exfiltrate. A
  separate non-HttpOnly `cb_csrf` cookie + matching `X-CSRF-Token` header
  defends against automatic cookie attach on cross-site state-changing
  requests.

## Decision

Three cookies make up a session, set by
[`core/cookies.py`](../../backend/app/core/cookies.py):

* `cb_access` — HttpOnly access JWT, 15 min TTL.
* `cb_refresh` — HttpOnly refresh JWT, 30 d TTL, `Path=/api/v1/auth` so the
  browser only ever sends it to the refresh endpoint.
* `cb_csrf` — non-HttpOnly random token, mirrored in `X-CSRF-Token` on
  every state-changing request via the double-submit pattern.

`Secure` is on in production; `SameSite=Lax` everywhere. `__Host-` prefix
is documented as an opt-in for the prod deploy (requires `Secure`, so off in
local dev). The Bearer header path stays alive for Swagger UI + machine
clients — `deps.py` reads the cookie first, falls back to `Authorization`.
[`core/csrf.py`](../../backend/app/core/csrf.py) only enforces CSRF when
the access cookie is the auth signal, so Bearer auth doesn't need it.

## Consequences

* **XSS can no longer exfiltrate the session.** It can still drive the API
  *while the user has the tab open*, but it can't pivot to another device
  or persist past the next refresh. That's the bar we needed.
* SPA refactor was load-bearing: ~10 frontend files dropped the
  `state.token` field, the `clientApi` calls dropped the token arg, every
  state-changing call gained `credentials: "include"` + `X-CSRF-Token`.
  See [Phase 2.1 in IMPROVEMENT-PLAN](../IMPROVEMENT-PLAN.md).
* Cookies don't survive `fetch` from a different origin without
  `credentials: "include"` — locked our CORS to an explicit allowlist
  + `allow_credentials=True`.
* Tests use the Bearer fallback (the access token is still returned in
  the login body for machine clients) so the seed-mode test suite didn't
  have to learn cookie jars.
* Future cost: a real OAuth callback flow (which we don't have yet) will
  need to set cookies on the callback host; `Path=/api/v1/auth` on the
  refresh keeps that surface narrow.
