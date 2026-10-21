"""Settings for the synthetic field-sales dataset.

Everything the simulator does is driven from here, so the dataset can be
regenerated identically (fixed SEED) or reshaped without touching the logic.
"""
from datetime import date

SEED = 42

START_DATE = date(2026, 4, 1)
END_DATE = date(2026, 9, 30)

# Thai public holidays inside the window: nobody visits stores on these days.
HOLIDAYS = {
    date(2026, 4, 6),   # Chakri Day
    date(2026, 4, 13), date(2026, 4, 14), date(2026, 4, 15),  # Songkran
    date(2026, 5, 1),   # Labour Day
    date(2026, 5, 4),   # Coronation Day
    date(2026, 6, 1),   # Visakha Bucha (observed)
    date(2026, 6, 3),   # Queen Suthida's Birthday
    date(2026, 7, 28),  # King's Birthday
    date(2026, 7, 29),  # Asarnha Bucha
    date(2026, 7, 30),  # Khao Phansa
    date(2026, 8, 12),  # Mother's Day
}

# Four sales territories in Bangkok, each made of a few districts.
# Coordinates are approximate district centres (lat, lng).
TERRITORIES = {
    "BKK-East": {
        "Bang Kapi": (13.7656, 100.6470),
        "Bueng Kum": (13.7850, 100.6690),
        "Saphan Sung": (13.7700, 100.6850),
        "Prawet": (13.7170, 100.6940),
    },
    "BKK-North": {
        "Chatuchak": (13.8280, 100.5600),
        "Lat Phrao": (13.8160, 100.6080),
        "Bang Khen": (13.8730, 100.5960),
        "Don Mueang": (13.9130, 100.5890),
    },
    "BKK-West": {
        "Bang Phlat": (13.7930, 100.5050),
        "Taling Chan": (13.7770, 100.4560),
        "Bangkok Noi": (13.7700, 100.4680),
        "Phasi Charoen": (13.7140, 100.4370),
    },
    "BKK-South": {
        "Khlong Toei": (13.7080, 100.5840),
        "Bang Na": (13.6680, 100.6050),
        "Yan Nawa": (13.6960, 100.5430),
        "Sathon": (13.7080, 100.5260),
    },
}

# Two area sales managers (ASM), each over two territories; two reps per territory.
ASM_TERRITORIES = {
    "ASM-01": ["BKK-East", "BKK-North"],
    "ASM-02": ["BKK-West", "BKK-South"],
}
REPS_PER_TERRITORY = 2
STORES_PER_REP = 60

# Store mix.
CHANNEL_WEIGHTS = {
    "Grocery": 0.30,
    "Minimart": 0.20,
    "Convenience": 0.10,
    "Restaurant": 0.25,
    "Bar": 0.15,
}
GRADE_WEIGHTS = {"A": 0.15, "B": 0.35, "C": 0.50}

# Required visits per store per month, by grade (the coverage target).
VISITS_PER_MONTH = {"A": 8, "B": 4, "C": 2}

# Behaviour of each rep: share of planned visits actually done.
# One rep is a deliberate under-performer so the analysis has something to find.
REP_COMPLIANCE = [0.93, 0.90, 0.88, 0.86, 0.92, 0.65, 0.89, 0.84]
SATURDAY_COMPLIANCE_FACTOR = 0.85   # Saturdays get skipped more often
RAINY_MONTHS = {8, 9}               # Aug-Sep: rain makes reps skip more
RAINY_COMPLIANCE_FACTOR = 0.92
UNPLANNED_VISIT_RATE = 0.05         # extra visits not in the plan

# Data-quality issues injected on purpose (share of visits).
ANOMALY_RATES = {
    "gps_far": 0.03,          # check-in 300 m - 2 km away from the store
    "missing_checkout": 0.02,
    "too_short": 0.01,        # visit under 2 minutes
    "duplicate": 0.005,       # same visit submitted twice
}

# Distributors ("agents") that hold stock and sell to the stores in a territory.
AGENTS_PER_TERRITORY = 1

SKUS = [
    # sku_id, name, category, pack, unit_price_thb
    ("SKU-001", "Hoppy Lager 320ml Can", "Lager", "Can 24x", 780),
    ("SKU-002", "Hoppy Lager 620ml Bottle", "Lager", "Bottle 12x", 720),
    ("SKU-003", "Hoppy Lager 490ml Can", "Lager", "Can 24x", 1080),
    ("SKU-004", "Hoppy Gold 330ml Bottle", "Premium", "Bottle 24x", 1150),
    ("SKU-005", "Hoppy Gold 490ml Can", "Premium", "Can 24x", 1290),
    ("SKU-006", "Hoppy Wheat 330ml Bottle", "Craft", "Bottle 24x", 1590),
    ("SKU-007", "Hoppy IPA 330ml Can", "Craft", "Can 24x", 1690),
    ("SKU-008", "Hoppy Draught Keg 20L", "Draught", "Keg 1x", 2900),
    ("SKU-009", "Fizz Soda 325ml Can", "Soda", "Can 24x", 290),
    ("SKU-010", "Fizz Soda 1L Bottle", "Soda", "Bottle 12x", 230),
    ("SKU-011", "Clear Water 600ml", "Water", "Bottle 12x", 85),
    ("SKU-012", "Clear Water 1.5L", "Water", "Bottle 6x", 75),
]
