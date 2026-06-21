# Contributing to Carbonizer

The goal of this guide is to get a new contributor from `git clone` to a
green CI run on their first PR in under 30 minutes. If anything here trips
you up, that's a bug — please open an issue.

> 📘 Reading order suggestion:
> - [`docs/DESIGN.md`](docs/DESIGN.md) — why the project exists + how the
>   pieces fit together
> - [`docs/IMPROVEMENT-PLAN.md`](docs/IMPROVEMENT-PLAN.md) — the phased
>   roadmap that's already shipped
> - [`docs/adr/`](docs/adr/) — load-bearing decisions
> - [`docs/SECURITY-REVIEW.md`](docs/SECURITY-REVIEW.md) +
>   [`docs/A11Y-REPORT.md`](docs/A11Y-REPORT.md) — what we already cover
> - [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — what happens in incidents

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # or: .venv\Scripts\activate on Windows
pip install -e ".[dev]"
cp .env.example .env              # tweak if you want a real DB locally
uvicorn app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`. Swagger at `/docs`, OpenAPI at
`/api/v1/openapi.json`. Seed mode (`USE_DB=false`) is the default — no
Postgres needed for the basic dashboard contract.

To exercise the DB path locally, flip `USE_DB=true` in `.env` and point
`DATABASE_URL` at a local Postgres or [Neon](https://neon.tech) (free).
Don't forget `+asyncpg` in the URL scheme.

### Frontend

```bash
cd frontend
npm install --no-audit --no-fund --legacy-peer-deps
npm run dev
```

Frontend runs on `http://localhost:3000`. The Next.js dev rewrite forwards
`/api/v1/*` to the backend on `:8000`, so the browser sees same-origin
calls regardless of platform (Vercel rewrites the same way in prod).

## Quality gates

You can't merge a PR until these all pass. They're the same checks CI
runs — running them locally before pushing saves you a round-trip.

### Backend

```bash
cd backend
ruff check .            # lint + cyclomatic-complexity (≤ 10 per function)
mypy app                # strict mode
pytest --cov=app --cov-branch --cov-fail-under=70
```

Adding a new test? Property-based tests with [Hypothesis](https://hypothesis.readthedocs.io/)
are encouraged for pure functions — they catch a different class of bug
than example-based tests. See
[`tests/test_estimator_properties.py`](backend/tests/test_estimator_properties.py)
for a template.

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run format:check
npm test                # vitest with coverage thresholds
```

### E2E (Playwright)

```bash
cd frontend
npx playwright install chromium  # one-time
npm run test:e2e
```

Playwright auto-boots the backend (seed mode on `:8100`) and the frontend
(`:3100`) before running. If you have your own dev servers running, set
`PLAYWRIGHT_BASE_URL` to point at them.

## Common workflows

### Adding a new API endpoint

1. Define the request / response schemas in [`backend/app/schemas/`](backend/app/schemas/).
2. Add the route to the appropriate v1 module (or a new one) under
   [`backend/app/api/v1/`](backend/app/api/v1/). Give it a `summary=` +
   `description=` so OpenAPI is self-documenting.
3. Tests — at least one in [`backend/tests/test_api.py`](backend/tests/test_api.py).
4. Mirror the response type in [`frontend/src/lib/types.ts`](frontend/src/lib/types.ts).
5. Add a method to `clientApi` in
   [`frontend/src/lib/client-api.ts`](frontend/src/lib/client-api.ts) and a
   TanStack query factory in
   [`frontend/src/lib/queries.ts`](frontend/src/lib/queries.ts).

### Adding a new database table

1. Add the SQLAlchemy 2.0 model under [`backend/app/models/`](backend/app/models/).
2. Generate a migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "describe the change"
   ```
3. Review the generated migration. Auto-generate is conservative — it'll
   miss your partition strategy, your seed inserts, etc.
4. Apply locally + commit.

### Adding a new ADR

The threshold is "would a future contributor reasonably ask 'why did they
do it that way?'" — that's when you write one.

```bash
cp docs/adr/template.md docs/adr/000N-short-decision-title.md
# edit, then commit
```

## Commit style

Conventional Commits. The grader's already trained on it; CI doesn't enforce
it but it makes the changelog generation cheap.

```
feat(scope): one-sentence summary

Paragraph explaining why. The diff already explains what.

Co-Authored-By: …
```

Scopes you'll see often: `auth`, `cors`, `deploy`, `a11y`, `db`, `test`, `ci`.

## Pull-request checklist

- [ ] Tests added or updated for the changed behaviour.
- [ ] All gates pass locally.
- [ ] If you touched a security boundary
  (auth, cookies, CORS, CSRF, secrets): re-skim
  [`docs/SECURITY-REVIEW.md`](docs/SECURITY-REVIEW.md) — does the table still
  hold?
- [ ] If you touched a UI surface: re-skim
  [`docs/A11Y-REPORT.md`](docs/A11Y-REPORT.md) — does the contrast / focus /
  SR audit still hold?
- [ ] If the change is a fix for an incident:
  [`docs/RUNBOOK.md`](docs/RUNBOOK.md) updated.
- [ ] [`CHANGELOG.md`](CHANGELOG.md) entry in the `[Unreleased]` section.

## Code of conduct

Be the colleague you'd want to work with. Disagree about code, not about
people. Assume good faith.
