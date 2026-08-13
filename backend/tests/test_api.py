"""Smoke tests covering the dashboard contract and auth flow (seed mode)."""

from __future__ import annotations

import re
from datetime import UTC
from typing import ClassVar

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.db import session


async def test_healthz(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_footprint_summary_shape(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/footprint/summary")
    assert resp.status_code == 200
    body = resp.json()
    # camelCase keys matching the TS FootprintSummary type
    assert body["totalTco2e"] == 4.2
    assert body["deltaPct"] == -8
    assert body["status"] == "improving"
    assert len(body["categories"]) == 4
    cat = body["categories"][0]
    assert {"category", "tco2e", "deltaPct", "trend", "method", "spark"} <= cat.keys()


async def test_summary_range_validation(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/footprint/summary", params={"range": "nope"})
    assert resp.status_code == 422


async def test_recommendations(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/recommendations")
    assert resp.status_code == 200
    nudges = resp.json()
    assert nudges[0]["kind"] == "clean-window"
    assert nudges[0]["effort"] == "1-tap"
    assert "carbonSavedTco2e" in nudges[0]


async def test_benchmark(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/community/benchmark")
    assert resp.status_code == 200
    assert resp.json()["vsAveragePct"] == -8


async def test_connections(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/connections")
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()}
    assert ids == {"bank", "telematics", "meter"}


async def test_login_and_me(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    resp = await client.get(f"{api_prefix}/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"]


async def test_me_requires_auth(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/auth/me")
    assert resp.status_code == 401


# --- onboarding ---------------------------------------------------------------


def test_estimator_math() -> None:
    """The estimator is a pure function — validate it without the API/DB."""
    from app.services import estimator

    summary = estimator.estimate(
        {
            "householdSize": 3,
            "homeType": "semi",
            "energySource": "standard",
            "diet": "average",
            "carType": "petrol",
            "carKmPerWeek": 120,
            "shortFlightsPerYear": 2,
            "longFlightsPerYear": 1,
        }
    )
    assert summary.total_tco2e > 0
    assert len(summary.categories) == 4
    assert all(c.method.value == "estimated" for c in summary.categories)
    # categories should sum to the headline total
    assert round(sum(c.tco2e for c in summary.categories), 2) == summary.total_tco2e


def test_no_car_hides_km_and_zeroes_it() -> None:
    """carType=none → carKmPerWeek is not visible and is neutralized to 0, so a
    leftover km value can't inflate transport."""
    from app.services import estimator

    car_q = next(q for q in estimator.QUESTIONS if q.id == "carKmPerWeek")
    # hidden when no car, visible otherwise
    assert estimator.is_visible(car_q, {"carType": "none"}) is False
    assert estimator.is_visible(car_q, {"carType": "petrol"}) is True

    # a stray large km answer is zeroed when there's no car
    norm = estimator.normalize_answers({"carType": "none", "carKmPerWeek": 999})
    assert norm["carKmPerWeek"] == 0

    no_car = estimator.estimate({"carType": "none", "carKmPerWeek": 999})
    has_car = estimator.estimate({"carType": "petrol", "carKmPerWeek": 200})

    def transport(summary: object) -> float:
        return next(
            c.tco2e for c in summary.categories if c.category.value == "transport"
        )

    assert transport(no_car) < transport(has_car)


# --- open banking ingestion ---------------------------------------------------


def test_carbon_mapping() -> None:
    from app.models.enums import Category
    from app.services import carbon

    assert carbon.categorize("5411") == Category.food       # groceries
    assert carbon.categorize("5541") == Category.transport  # fuel
    assert carbon.categorize("4900") == Category.energy      # utilities
    assert carbon.categorize(None) == Category.spend         # unknown → spend
    assert carbon.co2e_kg(Category.food, 100.0) > 0


def test_merchant_differentiation_same_mcc() -> None:
    """R2: same MCC, same spend, different merchant ⇒ different footprint."""
    from app.models.enums import Category
    from app.services import carbon

    # energy supplier: green tariff (Octopus) < standard (British Gas)
    green = carbon.co2e_kg(Category.energy, 100.0, "Octopus Energy")
    standard = carbon.co2e_kg(Category.energy, 100.0, "British Gas")
    assert green < standard
    # clothing: fast fashion (Zara) > more durable (Uniqlo)
    assert carbon.co2e_kg(Category.spend, 100.0, "Zara") > carbon.co2e_kg(
        Category.spend, 100.0, "Uniqlo"
    )


def test_energy_activity_factors() -> None:
    """Electricity scales with grid intensity; gas uses the combustion factor."""
    from app.services import carbon

    clean = carbon.energy_co2e_kg(10.0, "electricity", 120.0)
    dirty = carbon.energy_co2e_kg(10.0, "electricity", 260.0)
    assert clean < dirty
    assert carbon.energy_co2e_kg(10.0, "gas", None) > 0


# --- R2: price-elasticity of carbon ------------------------------------------


def test_price_elasticity() -> None:
    from app.models.enums import Category
    from app.services import carbon

    # spend is elastic (e<1): doubling £ less-than-doubles carbon
    assert carbon.co2e_kg(Category.spend, 200) < 2 * carbon.co2e_kg(Category.spend, 100)
    # transport is inelastic (e=1): fuel £ ∝ carbon
    assert carbon.co2e_kg(Category.transport, 200) == 2 * carbon.co2e_kg(
        Category.transport, 100
    )


# --- R1: bank-as-hub imputation ----------------------------------------------


def test_impute_from_bank() -> None:
    from app.services import impute

    low_v, low_c = impute.impute_from_bank(1.0, 750)
    high_v, high_c = impute.impute_from_bank(1.0, 3000)
    assert high_v > low_v  # more spend → more inferred usage
    assert low_c == high_c == impute.IMPUTED_CONFIDENCE
    # confidence ordering: measured > imputed > estimated
    from app.models.enums import CalcMethod

    assert (
        impute.CONFIDENCE[CalcMethod.activity]
        > impute.IMPUTED_CONFIDENCE
        > impute.CONFIDENCE[CalcMethod.estimated]
    )


# --- R3: reduction attribution -----------------------------------------------


async def test_attribution_requires_auth(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/footprint/attribution")
    assert resp.status_code == 401


async def test_attribution_seed_mode(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    # no DB in tests → attribution is unavailable, not an error
    resp = await client.get(
        f"{api_prefix}/footprint/attribution", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


# --- R0: value-of-information onboarding -------------------------------------


def test_r0_voi_ordering() -> None:
    from app.services import estimator

    qs = estimator.QUESTIONS
    assert all(q.voi is not None for q in qs)
    ids = [q.id for q in qs]
    # dependency respected: a question precedes any question gated on it
    assert ids.index("carType") < ids.index("carKmPerWeek")
    # ordered highest-yield first
    vois = [q.voi or 0 for q in qs]
    assert qs[0].voi == max(vois)


async def test_r0_questions_expose_voi(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.get(f"{api_prefix}/onboarding/questions")
    assert resp.status_code == 200
    assert all("voi" in q for q in resp.json()["questions"])


# --- R4: private, selection-bias-corrected benchmarking ----------------------


def test_r4_benchmark_stats() -> None:
    from app.services import benchmark_stats as bs

    # selection-bias (IPW) correction lifts the eco-skewed connector mean
    assert bs.ipw_population_mean(4.6) > 4.6
    # DP release is deterministic per cohort seed (no re-leak across reads)
    assert bs.adjusted_average(4.6, 7) == bs.adjusted_average(4.6, 7)
    # and reflects the upward correction
    assert bs.adjusted_average(4.6, 7) > 4.6


async def test_sandbox_provider_deterministic() -> None:
    import uuid
    from datetime import datetime

    from app.services.providers import SandboxBankProvider

    p = SandboxBankProvider()
    now = datetime(2026, 6, 18, tzinfo=UTC)
    uid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    a = await p.fetch_transactions(uid, now)
    b = await p.fetch_transactions(uid, now)
    assert len(a) > 10
    # deterministic per user: same external ids + amounts
    assert [t.external_id for t in a] == [t.external_id for t in b]
    assert [t.amount_minor for t in a] == [t.amount_minor for t in b]
    # different user → different history
    other = await p.fetch_transactions(
        uuid.UUID("22222222-2222-2222-2222-222222222222"), now
    )
    assert [t.amount_minor for t in a] != [t.amount_minor for t in other]


async def test_link_bank_needs_db(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    # tests run in seed mode (get_db → None) → bank linking unavailable
    resp = await client.post(f"{api_prefix}/connections/bank/link", headers=auth_headers)
    assert resp.status_code == 503


async def test_onboarding_questions_public(
    client: AsyncClient, api_prefix: str
) -> None:
    resp = await client.get(f"{api_prefix}/onboarding/questions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] >= 1
    ids = {q["id"] for q in body["questions"]}
    assert {"householdSize", "carType", "diet"} <= ids


async def test_estimate_requires_auth(client: AsyncClient, api_prefix: str) -> None:
    resp = await client.post(
        f"{api_prefix}/onboarding/estimate", json={"answers": {}}
    )
    assert resp.status_code == 401


async def test_estimate_needs_db_in_seed_mode(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    # tests run with get_db overridden to None → persistence unavailable → 503
    resp = await client.post(
        f"{api_prefix}/onboarding/estimate",
        headers=auth_headers,
        json={"answers": {"householdSize": 2}},
    )
    assert resp.status_code == 503


# --- Phase 2: security ------------------------------------------------------


async def test_security_headers_present(
    client: AsyncClient, api_prefix: str
) -> None:
    """SecurityHeadersMiddleware applies the defensive set to every response."""
    resp = await client.get(f"{api_prefix}/healthz")
    h = resp.headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in h["permissions-policy"]
    assert "default-src 'none'" in h["content-security-policy"]
    # HSTS only in production
    assert "strict-transport-security" not in h


def test_password_policy_min_length() -> None:
    from app.schemas.auth import RegisterRequest

    try:
        RegisterRequest(email="a@b.com", password="short")
    except Exception as e:
        assert "12" in str(e) or "least" in str(e).lower()
    else:  # pragma: no cover
        raise AssertionError("min-length validator did not fire")


def test_password_policy_rejects_weak() -> None:
    from pydantic import ValidationError

    from app.schemas.auth import RegisterRequest

    for pw in ("password123!", "letmein-now-1", "Carbonizer123"):
        try:
            RegisterRequest(email="alice@example.com", password=pw)
        except ValidationError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"weak password should be rejected: {pw}")


def test_password_policy_rejects_email_in_password() -> None:
    from pydantic import ValidationError

    from app.schemas.auth import RegisterRequest

    try:
        RegisterRequest(email="alice@example.com", password="alice12345xyz")
    except ValidationError as e:
        assert "email" in str(e).lower()
    else:  # pragma: no cover
        raise AssertionError("email-in-password should be rejected")


def test_password_policy_accepts_strong() -> None:
    from app.schemas.auth import RegisterRequest

    # 12+ chars, mix of letters and digits, no email overlap, not in weak list
    req = RegisterRequest(email="alice@example.com", password="r4nd0m-words-xyz")
    assert req.password == "r4nd0m-words-xyz"


def test_production_hard_fails_on_default_secret() -> None:
    """Phase 2.3 — booting prod with a default secret must abort."""
    from app.core.config import (
        DEFAULT_SECRET_KEY,
        InsecureProductionConfigError,
        Settings,
    )

    try:
        Settings(
            environment="production",
            secret_key=DEFAULT_SECRET_KEY,
            demo_password="real-not-default",
            database_url="postgresql+asyncpg://u:p@db/x",
        )
    except InsecureProductionConfigError as e:
        assert "SECRET_KEY" in str(e)
    else:  # pragma: no cover
        raise AssertionError("default SECRET_KEY in production must raise")


def test_production_accepts_real_secret() -> None:
    from app.core.config import Settings

    s = Settings(
        environment="production",
        secret_key="abc123-real-secret-that-is-long-enough",
        demo_password="real-demo-pw-not-default",
        database_url="postgresql+asyncpg://u:p@db/x",
    )
    assert s.is_production


async def test_login_rate_limit_fires(
    client: AsyncClient, api_prefix: str, with_rate_limit: None
) -> None:
    """6th login attempt within a minute → 429 with Retry-After."""
    last = None
    for _ in range(6):
        last = await client.post(
            f"{api_prefix}/auth/login",
            data={"username": "nobody@example.com", "password": "wrongpwd"},
        )
    assert last is not None
    assert last.status_code == 429
    assert "retry-after" in last.headers


# --- Phase 4: efficiency -----------------------------------------------------


async def test_summary_sets_private_cache(
    client: AsyncClient, api_prefix: str
) -> None:
    """GET /footprint/summary → Cache-Control: private, max-age=60."""
    resp = await client.get(f"{api_prefix}/footprint/summary")
    cc = resp.headers.get("cache-control", "")
    assert "private" in cc
    assert "max-age=60" in cc


async def test_benchmark_sets_private_cache(
    client: AsyncClient, api_prefix: str
) -> None:
    resp = await client.get(f"{api_prefix}/community/benchmark")
    cc = resp.headers.get("cache-control", "")
    assert "private" in cc
    assert "max-age=300" in cc


async def test_questions_sets_public_immutable_cache_and_etag(
    client: AsyncClient, api_prefix: str
) -> None:
    """The questionnaire is server-defined and version-cut; cache-aggressive."""
    resp = await client.get(f"{api_prefix}/onboarding/questions")
    cc = resp.headers.get("cache-control", "")
    assert "public" in cc
    assert "immutable" in cc
    assert "max-age=3600" in cc
    assert resp.headers.get("etag")  # ETag header present


async def test_questions_etag_returns_304_on_repeat(
    client: AsyncClient, api_prefix: str
) -> None:
    """A second request carrying ``If-None-Match`` of the first ETag → 304."""
    first = await client.get(f"{api_prefix}/onboarding/questions")
    etag = first.headers["etag"]
    second = await client.get(
        f"{api_prefix}/onboarding/questions",
        headers={"If-None-Match": etag},
    )
    assert second.status_code == 304


async def test_metrics_endpoint_is_exposed(client: AsyncClient) -> None:
    """Phase 4.3 — /metrics exposes the default prometheus_client registry."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    # The default registry always ships process_* + python_* gauges in
    # text-exposition format.
    body = resp.text
    assert "process_" in body or "python_" in body


async def test_gzip_compresses_large_responses(
    client: AsyncClient, api_prefix: str
) -> None:
    """The dashboard summary is JSON > 1KB so GZip should kick in when the
    client advertises support."""
    resp = await client.get(
        f"{api_prefix}/footprint/summary",
        headers={"Accept-Encoding": "gzip"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("content-encoding") == "gzip"


# --- Phase 7: production readiness ------------------------------------------


async def test_request_id_minted_on_response_when_absent(
    client: AsyncClient,
) -> None:
    """No inbound X-Request-Id → middleware mints one and echoes it back."""
    resp = await client.get("/api/v1/healthz")
    rid = resp.headers.get("x-request-id")
    assert rid is not None
    # uuid4 hex is 32 chars; we accept anything reasonable to avoid pinning shape.
    assert len(rid) >= 16


async def test_request_id_preserved_when_caller_sets_it(
    client: AsyncClient,
) -> None:
    """Inbound X-Request-Id flows through to the response verbatim."""
    resp = await client.get(
        "/api/v1/healthz", headers={"X-Request-Id": "deploy-test-12345"}
    )
    assert resp.headers.get("x-request-id") == "deploy-test-12345"


async def test_readyz_returns_ok_in_seed_mode(
    client: AsyncClient, api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Readyz reports healthy in seed mode, where the DB check is skipped.

    `use_db` is pinned rather than inherited: conftest overrides the `get_db`
    dependency, but readyz reads `settings.use_db` and calls `get_engine()`
    directly, so a developer .env with USE_DB=true otherwise fails this test
    against their unreachable local Postgres.
    """
    monkeypatch.setattr(settings, "use_db", False)
    resp = await client.get(f"{api_prefix}/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "skipped"


async def test_readyz_503s_without_leaking_db_details(
    client: AsyncClient, api_prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed DB probe drains traffic (503) without echoing the driver error.

    /readyz is unauthenticated (it's the platform health-check path), and
    asyncpg/SQLAlchemy exceptions carry the Postgres role, host and connection
    arguments. The detail belongs in the logs, not the response body.
    """
    monkeypatch.setattr(settings, "use_db", True)
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+asyncpg://leaky_role:hunter2@db.internal.example:5432/carbonizer",
    )
    monkeypatch.setattr(session, "_engine", None)
    monkeypatch.setattr(session, "_sessionmaker", None)

    resp = await client.get(f"{api_prefix}/readyz")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"
    assert "leaky_role" not in resp.text
    assert "hunter2" not in resp.text
    assert "db.internal.example" not in resp.text


def test_json_log_formatter_carries_request_id() -> None:
    """The structured formatter weaves the contextvar into every record."""
    import logging

    from app.core.logging import _JsonFormatter, request_id_var

    fmt = _JsonFormatter()
    token = request_id_var.set("test-rid-abcdef")
    try:
        record = logging.LogRecord(
            name="carbonizer.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        payload = fmt.format(record)
    finally:
        request_id_var.reset(token)
    import json

    parsed = json.loads(payload)
    assert parsed["level"] == "INFO"
    assert parsed["msg"] == "hello world"
    assert parsed["request_id"] == "test-rid-abcdef"
    assert parsed["name"] == "carbonizer.test"


async def test_audit_record_seed_mode_is_noop() -> None:
    """In seed mode (db=None), audit.record() must not raise."""
    from app.services import audit

    await audit.record(
        None, action="auth.login.success", actor=None, resource_type=None
    )


# --- Phase 2.1: HttpOnly cookies + CSRF -------------------------------------


async def test_login_sets_auth_cookies(client: AsyncClient, api_prefix: str) -> None:
    """Login must set HttpOnly access + refresh cookies and a readable CSRF cookie."""
    from app.core.config import settings as s

    resp = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    assert resp.status_code == 200
    cookies = resp.headers.get_list("set-cookie")
    joined = "\n".join(cookies)
    # access + refresh + csrf are all present
    assert s.access_cookie_name in joined
    assert s.refresh_cookie_name in joined
    assert s.csrf_cookie_name in joined
    # access cookie must be HttpOnly; CSRF cookie must NOT be (JS reads it)
    access_line = next(c for c in cookies if c.startswith(f"{s.access_cookie_name}="))
    csrf_line = next(c for c in cookies if c.startswith(f"{s.csrf_cookie_name}="))
    assert "HttpOnly" in access_line
    assert "HttpOnly" not in csrf_line
    # SameSite=Lax on every cookie
    assert "samesite=lax" in access_line.lower()


async def test_me_via_cookie(client: AsyncClient, api_prefix: str) -> None:
    """A logged-in client can hit /auth/me without an Authorization header — the
    cookie jar carries the access JWT."""
    from app.core.config import settings as s

    await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    # No headers — httpx auto-attaches the cookie set by the previous request.
    resp = await client.get(f"{api_prefix}/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == s.demo_email


async def test_csrf_rejects_cookie_post_without_header(
    client: AsyncClient, api_prefix: str
) -> None:
    """A cookie-authenticated POST without the X-CSRF-Token header is rejected 403."""
    from app.core.config import settings as s

    await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    # /connections/bank/link is a state-changing POST gated by require_user.
    resp = await client.post(f"{api_prefix}/connections/bank/link")
    assert resp.status_code == 403
    assert "csrf" in resp.json()["detail"].lower()


async def test_csrf_accepts_cookie_post_with_header(
    client: AsyncClient, api_prefix: str
) -> None:
    """The same POST with X-CSRF-Token matching the cb_csrf cookie passes the CSRF gate."""
    from app.core.config import settings as s

    await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    csrf = client.cookies.get(s.csrf_cookie_name)
    assert csrf  # set on login
    resp = await client.post(
        f"{api_prefix}/connections/bank/link",
        headers={"X-CSRF-Token": csrf},
    )
    # CSRF gate is passed; the actual handler returns 503 in seed mode (no DB).
    assert resp.status_code == 503


async def test_csrf_skipped_for_bearer_auth(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    """Bearer-auth requests don't need CSRF — the token isn't sent automatically by the browser."""
    # auth_headers was built from the access token in the login body, not the cookie.
    # We have to wipe the cookie jar so the request is purely Bearer-auth.
    client.cookies.clear()
    resp = await client.post(
        f"{api_prefix}/connections/bank/link", headers=auth_headers
    )
    # Reaches the handler (no CSRF gate); fails 503 because seed mode has no DB.
    assert resp.status_code == 503


async def test_csrf_skipped_when_bearer_present_alongside_cookies(
    client: AsyncClient, api_prefix: str
) -> None:
    """Bearer header alongside the session cookies still bypasses CSRF.

    Use case: an integration test or machine client that reused a logged-in
    browser's cookie jar. The bearer header is the deliberate signal — once
    it's present, we trust the caller's CSRF exposure is nil (the header
    can't be set cross-origin without a CORS preflight). Without this skip,
    the e2e ``connect-source`` test would have to manually plumb the
    X-CSRF-Token from the cookie just to no-op the check.
    """
    from app.core.config import settings as s

    login = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    assert login.status_code == 200
    token = login.json()["accessToken"]
    # cookies are still in the jar — CSRF normally fires for state-changing POSTs.
    assert s.access_cookie_name in client.cookies
    resp = await client.post(
        f"{api_prefix}/connections/bank/link",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Reaches the handler (CSRF gate skipped because of the Bearer header);
    # 503 because seed mode has no DB.
    assert resp.status_code == 503


async def test_refresh_rotates_cookies(client: AsyncClient, api_prefix: str) -> None:
    """/auth/refresh issues a fresh access + CSRF cookie using the refresh JWT."""
    from app.core.config import settings as s

    await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    old_csrf = client.cookies.get(s.csrf_cookie_name)

    resp = await client.post(f"{api_prefix}/auth/refresh")
    assert resp.status_code == 200
    new_csrf = client.cookies.get(s.csrf_cookie_name)
    # CSRF rotated, refresh cookie still present
    assert new_csrf and new_csrf != old_csrf


async def test_refresh_without_cookie_is_401(
    client: AsyncClient, api_prefix: str
) -> None:
    resp = await client.post(f"{api_prefix}/auth/refresh")
    assert resp.status_code == 401


async def test_logout_clears_cookies(client: AsyncClient, api_prefix: str) -> None:
    from app.core.config import settings as s

    await client.post(
        f"{api_prefix}/auth/login",
        data={"username": s.demo_email, "password": s.demo_password},
    )
    csrf = client.cookies.get(s.csrf_cookie_name)
    assert csrf
    resp = await client.post(
        f"{api_prefix}/auth/logout", headers={"X-CSRF-Token": csrf}
    )
    assert resp.status_code == 204
    # After clear, /me should return 401 (no auth cookie)
    me = await client.get(f"{api_prefix}/auth/me")
    assert me.status_code == 401


# --- Phase 2.7: GDPR/DPDP data-rights ---------------------------------------


async def test_privacy_export_requires_auth(
    client: AsyncClient, api_prefix: str
) -> None:
    resp = await client.post(f"{api_prefix}/privacy/export")
    assert resp.status_code == 401


async def test_privacy_export_seed_mode_503(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    """Seed mode has no DB → data export is unavailable."""
    resp = await client.post(f"{api_prefix}/privacy/export", headers=auth_headers)
    assert resp.status_code == 503


async def test_privacy_erase_requires_auth(
    client: AsyncClient, api_prefix: str
) -> None:
    resp = await client.post(f"{api_prefix}/privacy/erase")
    assert resp.status_code == 401


async def test_privacy_erase_seed_mode_503(
    client: AsyncClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(f"{api_prefix}/privacy/erase", headers=auth_headers)
    assert resp.status_code == 503


def test_dsr_erasure_grace_is_48_hours() -> None:
    """Regression: shortening the grace window is a regulator-visible change."""
    from datetime import timedelta

    from app.services.dsr import ERASURE_GRACE

    assert timedelta(hours=48) == ERASURE_GRACE


# --- Phase 2.8: envelope encryption -----------------------------------------


def test_crypto_roundtrip_dev_key() -> None:
    """Encrypt → decrypt returns the original plaintext in dev mode (derived key)."""
    from app.core import crypto

    crypto.get_fernet.cache_clear()
    ct = crypto.encrypt("provider-bearer-abc123")
    assert isinstance(ct, bytes)
    assert b"provider-bearer-abc123" not in ct  # ciphertext is opaque
    assert crypto.decrypt(ct) == "provider-bearer-abc123"


def test_crypto_decrypt_none_returns_none() -> None:
    from app.core import crypto

    assert crypto.decrypt(None) is None


def test_crypto_decrypt_rejects_wrong_key() -> None:
    """Ciphertext under one key is not decryptable under another."""
    from cryptography.fernet import Fernet, InvalidToken

    from app.core import crypto

    crypto.get_fernet.cache_clear()
    ct = crypto.encrypt("secret")
    # swap to a different Fernet key
    other = Fernet(Fernet.generate_key())
    try:
        other.decrypt(ct)
    except InvalidToken:
        pass
    else:  # pragma: no cover
        raise AssertionError("Fernet decrypt must reject a foreign ciphertext")


def test_crypto_production_requires_key_env() -> None:
    """Settings(environment=production, encryption_key="") + a fresh get_fernet
    must refuse to derive from SECRET_KEY."""
    from app.core import config, crypto

    # Build a fake production settings instance
    prod = config.Settings(
        environment="production",
        secret_key="a-real-rotation-of-the-default-key",
        demo_password="not-default-demo",
        database_url="postgresql+asyncpg://u:p@db/x",
        encryption_key="",
    )
    crypto.get_fernet.cache_clear()
    real_settings = crypto.settings
    crypto.settings = prod  # type: ignore[assignment]
    try:
        try:
            crypto.get_fernet()
        except crypto.InsecureEncryptionKeyError as e:
            assert "ENCRYPTION_KEY" in str(e)
        else:  # pragma: no cover
            raise AssertionError("missing ENCRYPTION_KEY in prod must raise")
    finally:
        crypto.settings = real_settings  # type: ignore[assignment]
        crypto.get_fernet.cache_clear()


def test_connection_set_access_token_encrypts() -> None:
    """set_access_token writes ciphertext; get_access_token round-trips."""
    from app.core import crypto
    from app.models.connection import (
        Connection,
        get_access_token,
        set_access_token,
    )
    from app.models.enums import ProviderKind

    crypto.get_fernet.cache_clear()
    conn = Connection(provider=ProviderKind.bank)
    set_access_token(conn, "real-oauth-token-xyz")

    assert conn.access_token_enc is not None
    assert b"real-oauth-token-xyz" not in conn.access_token_enc
    assert get_access_token(conn) == "real-oauth-token-xyz"

    # clearing
    set_access_token(conn, None)
    assert conn.access_token_enc is None
    assert get_access_token(conn) is None


def test_dsr_export_omits_access_tokens() -> None:
    """The export bundle must not include the encrypted-or-plaintext provider
    access token, even though the column survives the dump."""
    from app.services.dsr_export import _dump

    class _FakeConn:
        class __table__:
            class _Col:
                def __init__(self, name: str) -> None:
                    self.name = name

            columns = (_Col("id"), _Col("provider"), _Col("access_token_enc"))

        id = "abc"
        provider = "bank"
        access_token_enc = b"\x00\x01ciphertext"

    dumped = _dump(_FakeConn())
    # _safe coerces bytes → None; the privacy router additionally strips the key.
    assert dumped["access_token_enc"] is None
    assert dumped["id"] == "abc"


# --- audit/2026-08 hardening regressions -------------------------------------


def test_cors_preview_regex_rejects_unrelated_platform_projects() -> None:
    """C1 — the prod origin allowlist must not admit every *.vercel.app host.

    Both platforms hand out free subdomains on signup. With
    allow_credentials=True a matching origin is a same-trust origin: GETs are
    CSRF-exempt by design, and /auth/refresh is CSRF-exempt *and* returns a
    live access JWT in its body.
    """
    from app.main import _preview_origin_regex

    pattern = _preview_origin_regex(
        ["https://carbonizer.vercel.app", "https://carbonizer-api.onrender.com"]
    )
    assert pattern is not None
    matcher = re.compile(pattern)

    # our own preview deploys still work
    assert matcher.fullmatch("https://carbonizer-9f3ab21-harshit.vercel.app")
    assert matcher.fullmatch("https://carbonizer-git-feat-x-harshit.vercel.app")
    assert matcher.fullmatch("https://carbonizer-api-staging.onrender.com")

    # unrelated projects on the same platform do not
    assert not matcher.fullmatch("https://evil-attacker.vercel.app")
    assert not matcher.fullmatch("https://totally-not-carbonizer.onrender.com")
    assert not matcher.fullmatch("https://carbonizer.vercel.app.attacker.com")


def test_cors_preview_regex_is_none_without_platform_origins() -> None:
    """A custom-domain-only deploy gets no wildcard at all — the exact
    CORS_ORIGINS list is then the whole allowlist."""
    from app.main import _preview_origin_regex

    assert _preview_origin_regex(["https://carbonizer.app"]) is None
    assert _preview_origin_regex([]) is None


async def test_refresh_rejects_subject_with_no_live_user(
    client: AsyncClient, api_prefix: str
) -> None:
    """H1 — a refresh cookie must stop working once the user row is gone.

    JWTs are stateless with no denylist, so without a lookup an erased
    account's 30-day refresh cookie keeps minting access tokens.
    """
    from app.core.security import create_refresh_token
    from app.db.session import get_db
    from app.main import app

    class _NoUserResult:
        def scalar_one_or_none(self) -> None:
            return None

    class _NoUserSession:
        async def execute(self, *_a: object, **_kw: object) -> _NoUserResult:
            return _NoUserResult()

    async def _override():  # type: ignore[no-untyped-def]
        yield _NoUserSession()

    previous = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = _override
    try:
        erased = "1e9d1c1a-0000-4000-8000-000000000000"
        client.cookies.set("cb_refresh", create_refresh_token(erased))
        resp = await client.post(f"{api_prefix}/auth/refresh")
    finally:
        app.dependency_overrides[get_db] = previous
        client.cookies.clear()

    assert resp.status_code == 401


async def test_refresh_still_works_for_the_demo_subject(
    client: AsyncClient, api_prefix: str
) -> None:
    """H1 must not regress seed mode — the demo subject has no row to look up."""
    login = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": settings.demo_email, "password": settings.demo_password},
    )
    assert login.status_code == 200
    resp = await client.post(f"{api_prefix}/auth/refresh")
    assert resp.status_code == 200
    client.cookies.clear()


def test_audit_prefers_the_minted_request_id() -> None:
    """M3 — audit rows must carry the id the middleware minted.

    RequestIdMiddleware stores a fresh UUID in the contextvar when the caller
    sends no X-Request-Id, but never writes it onto the request headers.
    Reading only the header left request_id NULL on every direct call.
    """
    import asyncio

    from app.core.logging import request_id_var
    from app.services import audit

    captured: list[object] = []

    class _CapturingSession:
        def add(self, row: object) -> None:
            captured.append(row)

        async def flush(self) -> None:
            return None

    class _NoHeaderRequest:
        headers: ClassVar[dict[str, str]] = {}
        client = None

    token = request_id_var.set("minted-by-middleware")
    try:
        asyncio.run(
            audit.record(
                _CapturingSession(),  # type: ignore[arg-type]
                action="auth.login.success",
                actor=None,
                request=_NoHeaderRequest(),  # type: ignore[arg-type]
            )
        )
    finally:
        request_id_var.reset(token)

    assert len(captured) == 1
    assert captured[0].request_id == "minted-by-middleware"  # type: ignore[attr-defined]


def test_seed_mode_login_uses_constant_time_comparison() -> None:
    """L4 — the one credential check that wasn't constant-time now is."""
    import inspect

    from app.api.v1 import auth as auth_module

    source = inspect.getsource(auth_module._login_seed_mode)
    assert "compare_digest" in source
    assert "!=" not in source


async def test_login_rejects_non_ascii_password_with_401_not_500(
    client: AsyncClient, api_prefix: str
) -> None:
    """`hmac.compare_digest` raises TypeError on non-ASCII *str*, so the
    constant-time comparison must run over UTF-8 bytes — otherwise a wrong
    password containing an accent becomes a 500 instead of a 401."""
    resp = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": settings.demo_email, "password": "pässwörd-ünicode"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password"


async def test_login_rejects_non_ascii_email_with_401_not_500(
    client: AsyncClient, api_prefix: str
) -> None:
    """Same guard on the username side."""
    resp = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": "démo@carbonizer.app", "password": settings.demo_password},
    )
    assert resp.status_code == 401
