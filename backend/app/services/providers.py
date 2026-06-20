"""Bank data providers (docs/DATA-STRATEGY.md §3, source #2).

A `BankProvider` returns recent transactions for a connection. The MVP ships a
`SandboxBankProvider` that fabricates a realistic, deterministic UK transaction
history (so the whole ingestion → carbon → footprint pipeline is exercisable with
no external credentials). A real Open Banking adapter (GoCardless Bank Account
Data / TrueLayer) implements the same interface and drops in unchanged:

    class GoCardlessProvider:
        async def fetch_transactions(self, user_id, now): ...  # call the live API

so nothing downstream of `fetch_transactions` changes when we go live.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

WINDOW_DAYS = 84  # ~12 weeks, matching the "12w" snapshot range


@dataclass(frozen=True)
class ProviderTxn:
    external_id: str
    booked_at: datetime
    amount_minor: int  # pence, positive = outgoing spend
    currency: str
    mcc: str
    description: str
    merchant: str


class BankProvider(Protocol):
    async def fetch_transactions(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[ProviderTxn]: ...


@dataclass(frozen=True)
class EnergyRead:
    external_id: str
    interval_start: datetime
    kwh: float
    fuel: str  # "electricity" | "gas"
    grid_intensity_g: float | None  # gCO2/kWh at time of use (electricity only)


class MeterProvider(Protocol):
    async def fetch_energy(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[EnergyRead]: ...


# (mcc, merchants, weekly cadence, £ min, £ max)
_RECIPES = [
    ("5411", ["Tesco", "Sainsbury's", "Aldi", "Lidl"], 1.0, 35, 75),   # groceries
    ("5814", ["Greggs", "McDonald's", "Pret"], 0.6, 5, 14),            # fast food
    ("5812", ["The Ivy", "Pizza Express", "Wagamama"], 0.4, 22, 48),   # restaurants
    ("5541", ["Shell", "BP", "Esso"], 0.25, 45, 80),                   # fuel
    # NB: no utility/energy transactions — home energy belongs to the smart meter
    # (activity-based). With bank-only, energy is imputed from the hub (R1).
    ("4111", ["TfL", "Trainline"], 0.9, 3, 7),                         # transit
    ("5999", ["Amazon", "Argos"], 0.7, 8, 60),                         # misc retail
    ("5651", ["Zara", "H&M", "Uniqlo"], 0.15, 20, 90),                # clothing
    ("5732", ["Currys", "Apple"], 0.08, 40, 600),                     # electronics
]


class SandboxBankProvider:
    """Deterministic per-user fake transactions over the last WINDOW_DAYS."""

    name = "sandbox"

    async def fetch_transactions(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[ProviderTxn]:
        rng = random.Random(int(user_id.hex[:12], 16))  # stable per user
        weeks = WINDOW_DAYS // 7
        txns: list[ProviderTxn] = []
        seq = 0
        for mcc, merchants, per_week, lo, hi in _RECIPES:
            for week in range(weeks):
                # Bernoulli draw per week so cadence < 1 spreads naturally
                if per_week < 1.0 and rng.random() > per_week:
                    continue
                count = max(1, round(per_week)) if per_week >= 1 else 1
                for _ in range(count):
                    day = week * 7 + rng.randint(0, 6)
                    booked = (now - timedelta(days=WINDOW_DAYS - day)).replace(
                        hour=rng.randint(7, 21), minute=rng.randint(0, 59),
                        second=0, microsecond=0,
                    )
                    pounds = round(rng.uniform(lo, hi), 2)
                    merchant = rng.choice(merchants)
                    txns.append(
                        ProviderTxn(
                            external_id=f"sbx-{seq}",
                            booked_at=booked,
                            amount_minor=round(pounds * 100),
                            currency="GBP",
                            mcc=mcc,
                            description=f"{merchant} card purchase",
                            merchant=merchant,
                        )
                    )
                    seq += 1
        txns.sort(key=lambda t: t.booked_at)
        return txns


class SandboxMeterProvider:
    """Deterministic daily electricity + gas reads with a varying grid intensity.

    Daily (not half-hourly) to keep dev volume modest; the real DCC/Octopus/n3rgy
    adapter returns half-hourly and implements the same `fetch_energy` interface.
    """

    name = "sandbox"

    async def fetch_energy(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[EnergyRead]:
        rng = random.Random(int(user_id.hex[12:24], 16))  # distinct from bank seed
        reads: list[EnergyRead] = []
        for day in range(WINDOW_DAYS):
            start = (now - timedelta(days=WINDOW_DAYS - day)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            # electricity: ~8-12 kWh/day, grid intensity 120-260 gCO2/kWh
            elec = round(rng.uniform(7.0, 12.0), 2)
            intensity = round(rng.uniform(120, 260), 0)
            reads.append(
                EnergyRead(f"sbx-e-{day}", start, elec, "electricity", intensity)
            )
            # gas: ~6-16 kWh/day (hot water + cooking out of heating season)
            gas = round(rng.uniform(6.0, 16.0), 2)
            reads.append(EnergyRead(f"sbx-g-{day}", start, gas, "gas", None))
        return reads


_BANK_PROVIDERS: dict[str, BankProvider] = {"sandbox": SandboxBankProvider()}
_METER_PROVIDERS: dict[str, MeterProvider] = {"sandbox": SandboxMeterProvider()}


def get_bank_provider(name: str = "sandbox") -> BankProvider:
    return _BANK_PROVIDERS.get(name, _BANK_PROVIDERS["sandbox"])


def get_meter_provider(name: str = "sandbox") -> MeterProvider:
    return _METER_PROVIDERS.get(name, _METER_PROVIDERS["sandbox"])
