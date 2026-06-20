"""Spend-based carbon mapping for bank transactions (docs/DATA-STRATEGY.md §3, R2).

Maps a Merchant Category Code (MCC) to a footprint Category, then applies a
spend-based emission factor (kg CO2e per GBP) — an EIO-LCA / EXIOBASE-style
intensity. R2 (docs/DATA-STRATEGY.md §9) refines the blunt baseline two ways:
merchant-level priors (eco vs conventional within the same MCC) and a per-category
price-elasticity so carbon decouples from premium pricing.
"""

from __future__ import annotations

from app.models.enums import Category

# MCC → category. Unmapped MCCs fall back to general `spend`.
_MCC_CATEGORY: dict[str, Category] = {
    # food & drink
    "5411": Category.food,   # grocery stores / supermarkets
    "5422": Category.food,   # butchers
    "5462": Category.food,   # bakeries
    "5499": Category.food,   # specialty food
    "5812": Category.food,   # eating places / restaurants
    "5814": Category.food,   # fast food
    # transport
    "5541": Category.transport,  # service stations (fuel)
    "5542": Category.transport,  # automated fuel dispensers
    "4111": Category.transport,  # commuter transport
    "4131": Category.transport,  # bus lines
    "4121": Category.transport,  # taxis / rideshare
    # energy (home utilities)
    "4900": Category.energy,  # utilities — electric/gas/water
    # general consumption → spend
    "5311": Category.spend,  # department stores
    "5651": Category.spend,  # clothing
    "5732": Category.spend,  # electronics
    "5999": Category.spend,  # misc retail
}

# spend-based emission factors, kg CO2e per GBP (rough EIO-LCA intensities).
_CATEGORY_KG_PER_GBP: dict[Category, float] = {
    Category.food: 0.40,
    Category.transport: 0.55,
    Category.energy: 0.50,
    Category.spend: 0.30,
    Category.home: 0.30,
}

# R2 (docs/DATA-STRATEGY.md §9): a curated merchant→intensity multiplier so two
# purchases at the *same MCC* aren't scored identically — the core flaw of pure
# spend-based accounting. A green energy supplier or a sustainable brand scores
# below 1.0; carbon-heavy merchants above. Default 1.0 (no signal). This is the
# hand-curated MVP of R2; the full version learns priors from population data.
_MERCHANT_MULTIPLIER: dict[str, float] = {
    # energy suppliers — green/renewable tariff vs standard grid mix
    "octopus energy": 0.45,
    "good energy": 0.40,
    "bulb": 0.50,
    "british gas": 1.0,
    # clothing — ultra-fast / fast fashion vs durable / sustainable / second-hand
    "shein": 1.55,
    "boohoo": 1.45,
    "zara": 1.35,
    "h&m": 1.35,
    "uniqlo": 1.0,
    "patagonia": 0.55,
    "vinted": 0.35,
    "ebay": 0.50,
    # grocers — discounters carry a slightly lower basket intensity on average
    "aldi": 0.92,
    "lidl": 0.92,
    # transport — rail vs road fuel handled by MCC; EV charging is low-carbon
    "trainline": 0.70,
    "pod point": 0.30,
    "tesla supercharger": 0.30,
}

# R2 — price-elasticity of carbon. Pure spend-based accounting assumes carbon ∝ £,
# which wrongly penalizes premium *low-carbon* choices (durable goods, organic).
# We apply a per-category elasticity e ≤ 1 so carbon grows sub-linearly with price:
#     co2e = factor · ref · (gbp / ref)^e · merchant_multiplier
# e = 1 → strictly linear (fuel/energy £ track litres/kWh); e < 1 → premium spend
# decouples from carbon (general goods). `ref` anchors the curve at a typical spend
# so aggregate intensity stays calibrated.
_CATEGORY_PRICE_ELASTICITY: dict[Category, float] = {
    Category.food: 0.95,       # more food ≈ more carbon (near-linear)
    Category.transport: 1.00,  # fuel £ ∝ litres ∝ carbon (linear)
    Category.energy: 1.00,     # utility £ ∝ kWh (linear; metered preferred)
    Category.spend: 0.70,      # durable/premium goods decouple most
    Category.home: 0.70,
}
_CATEGORY_REF_GBP: dict[Category, float] = {
    Category.food: 40.0,
    Category.transport: 55.0,
    Category.energy: 100.0,
    Category.spend: 35.0,
    Category.home: 35.0,
}


def categorize(mcc: str | None) -> Category:
    """Map an MCC to a footprint category; default to general spend."""
    if mcc is None:
        return Category.spend
    return _MCC_CATEGORY.get(mcc, Category.spend)


def merchant_multiplier(merchant: str | None) -> float:
    """Relative carbon intensity for a known merchant (1.0 if unknown)."""
    if not merchant:
        return 1.0
    return _MERCHANT_MULTIPLIER.get(merchant.strip().lower(), 1.0)


def co2e_kg(category: Category, gbp: float, merchant: str | None = None) -> float:
    """Spend-based CO2e (kg), refined by (R2) a merchant-level multiplier and a
    per-category price-elasticity so carbon decouples from premium pricing."""
    base: float = _CATEGORY_KG_PER_GBP.get(category, _CATEGORY_KG_PER_GBP[Category.spend])
    e: float = _CATEGORY_PRICE_ELASTICITY.get(category, 0.85)
    ref: float = _CATEGORY_REF_GBP.get(category, 35.0)
    priced: float = base * ref * (max(gbp, 0.01) / ref) ** e
    return float(priced * merchant_multiplier(merchant))


def energy_co2e_kg(kwh: float, fuel: str, grid_intensity_g: float | None) -> float:
    """Activity-based CO2e (kg) for a metered energy reading.

    Electricity uses the grid carbon intensity (gCO2/kWh) at the time of use;
    gas uses a fixed combustion factor (~0.183 kgCO2e/kWh, DEFRA).
    """
    if fuel == "gas":
        return kwh * 0.183
    intensity = grid_intensity_g if grid_intensity_g is not None else 162.0
    return kwh * intensity / 1000.0
