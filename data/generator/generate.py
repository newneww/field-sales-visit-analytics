"""Generate the synthetic field-sales dataset as CSV files.

The story: FieldPulse, a fictional beverage company, has sales reps who visit
stores in Bangkok. Each month a rep plans store visits, the area sales manager
(ASM) approves the plan, and the rep checks in and out at each store with GPS,
photos and (sometimes) an order. Distributors ("agents") hold the stock that
those orders draw on.

Everything is random but reproducible: the same SEED gives the same files.

Usage:
    python data/generator/generate.py            # writes data/output/*.csv
"""
import csv
import math
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from faker import Faker

import config as cfg

ROOT = Path(__file__).resolve().parents[1]
OSM_PATH = ROOT / "raw" / "osm_stores.csv"
OUT_DIR = ROOT / "output"

rng = random.Random(cfg.SEED)
fake = Faker("th_TH")
Faker.seed(cfg.SEED)

METERS_PER_DEG_LAT = 111_320


# ---------------------------------------------------------------- helpers

def working_days(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 6 and d not in cfg.HOLIDAYS:  # Mon-Sat
            days.append(d)
        d += timedelta(days=1)
    return days


def months_in_range(start: date, end: date) -> list[tuple[int, int]]:
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def offset_point(lat: float, lng: float, meters: float, bearing_deg: float) -> tuple[float, float]:
    b = math.radians(bearing_deg)
    dlat = meters * math.cos(b) / METERS_PER_DEG_LAT
    dlng = meters * math.sin(b) / (METERS_PER_DEG_LAT * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    dlat = (a[0] - b[0]) * METERS_PER_DEG_LAT
    dlng = (a[1] - b[1]) * METERS_PER_DEG_LAT * math.cos(math.radians(a[0]))
    return math.hypot(dlat, dlng)


def weighted_counts(weights: dict[str, float], total: int) -> dict[str, int]:
    """Split total into exact integer counts that follow the weights."""
    counts = {k: int(total * w) for k, w in weights.items()}
    leftover = total - sum(counts.values())
    for k in sorted(weights, key=weights.get, reverse=True)[:leftover]:
        counts[k] += 1
    return counts


def nearest_neighbour_route(stops: list[dict]) -> list[dict]:
    if not stops:
        return stops
    remaining = stops[:]
    route = [remaining.pop(rng.randrange(len(remaining)))]
    while remaining:
        here = (route[-1]["lat"], route[-1]["lng"])
        nxt = min(remaining, key=lambda s: distance_m(here, (s["lat"], s["lng"])))
        remaining.remove(nxt)
        route.append(nxt)
    return route


def store_name(channel: str) -> str:
    first = fake.first_name()
    if channel == "Grocery":
        return rng.choice([f"ร้านโชห่วย{first}", f"ร้าน{first}พาณิชย์", f"ร้านค้า{first}"])
    if channel == "Minimart":
        return rng.choice([f"{first}มินิมาร์ท", f"มินิมาร์ท {first}"])
    if channel == "Convenience":
        return f"ร้านสะดวกซื้อ {first}"
    if channel == "Restaurant":
        return rng.choice([f"ครัว{first}", f"ร้านอาหาร{first}", f"{first}หมูกระทะ"])
    return rng.choice([f"{first} Bar & Bistro", f"ร้านนั่งชิล {first}"])


def load_osm_places() -> list[dict]:
    if not OSM_PATH.exists():
        return []
    with OSM_PATH.open(encoding="utf-8") as f:
        return [
            {**row, "lat": float(row["lat"]), "lng": float(row["lng"])}
            for row in csv.DictReader(f)
        ]


# ---------------------------------------------------------------- master data

def build_people():
    territories, reps = [], []
    rep_no = 0
    for asm_id, terr_names in cfg.ASM_TERRITORIES.items():
        reps.append({
            "rep_id": asm_id,
            "rep_name": f"{fake.first_name()} {fake.last_name()}",
            "nickname": fake.first_name(),
            "role": "ASM",
            "territory_id": "",
            "manager_id": "",
            "hire_date": fake.date_between(date(2018, 1, 1), date(2022, 12, 31)),
        })
        for terr in terr_names:
            territories.append({"territory_id": terr, "asm_id": asm_id})
            for _ in range(cfg.REPS_PER_TERRITORY):
                rep_no += 1
                reps.append({
                    "rep_id": f"R{rep_no:02d}",
                    "rep_name": f"{fake.first_name()} {fake.last_name()}",
                    "nickname": fake.first_name(),
                    "role": "Sales Rep",
                    "territory_id": terr,
                    "manager_id": asm_id,
                    "hire_date": fake.date_between(date(2020, 1, 1), date(2026, 2, 28)),
                })
    return territories, reps


def build_agents(territories):
    return [
        {
            "agent_id": f"AG-{i:02d}",
            "agent_name": f"บริษัท {fake.last_name()} เทรดดิ้ง จำกัด",
            "territory_id": t["territory_id"],
        }
        for i, t in enumerate(territories, start=1)
    ]


def build_stores(reps, agents):
    osm_places = load_osm_places()
    used_osm = set()
    agent_by_terr = {a["territory_id"]: a["agent_id"] for a in agents}
    sales_reps = [r for r in reps if r["role"] == "Sales Rep"]

    stores, store_no = [], 0
    for terr, districts in cfg.TERRITORIES.items():
        terr_reps = [r for r in sales_reps if r["territory_id"] == terr]
        district_names = list(districts)
        per_rep = len(district_names) // len(terr_reps)
        for i, rep in enumerate(terr_reps):
            rep_districts = district_names[i * per_rep:(i + 1) * per_rep]
            channels = [c for c, n in weighted_counts(cfg.CHANNEL_WEIGHTS, cfg.STORES_PER_REP).items() for _ in range(n)]
            grades = [g for g, n in weighted_counts(cfg.GRADE_WEIGHTS, cfg.STORES_PER_REP).items() for _ in range(n)]
            rng.shuffle(channels)
            rng.shuffle(grades)
            for k in range(cfg.STORES_PER_REP):
                store_no += 1
                district = rep_districts[k % len(rep_districts)]
                centre = districts[district]
                channel = channels[k]

                place = None
                candidates = [
                    p for p in osm_places
                    if p["osm_id"] not in used_osm and p["channel"] == channel
                    and distance_m(centre, (p["lat"], p["lng"])) < 3000
                ]
                if candidates:
                    place = rng.choice(candidates)
                    used_osm.add(place["osm_id"])
                if place:
                    lat, lng, source = place["lat"], place["lng"], "osm"
                    name = place["name"] or store_name(channel)
                else:
                    lat, lng = offset_point(*centre, abs(rng.gauss(0, 1200)), rng.uniform(0, 360))
                    name, source = store_name(channel), "synthetic"

                # About 5% of stores are opened during the period.
                if rng.random() < 0.05:
                    created = fake.date_between(cfg.START_DATE, cfg.END_DATE - timedelta(days=30))
                else:
                    created = fake.date_between(date(2023, 1, 1), cfg.START_DATE - timedelta(days=1))

                stores.append({
                    "store_id": f"ST-{store_no:04d}",
                    "store_name": name,
                    "channel": channel,
                    "grade": grades[k],
                    "territory_id": terr,
                    "district": district,
                    "lat": round(lat, 6),
                    "lng": round(lng, 6),
                    "rep_id": rep["rep_id"],
                    "agent_id": agent_by_terr[terr],
                    "owner_name": f"คุณ{fake.first_name()}",
                    "phone": fake.phone_number(),
                    "location_source": source,
                    "created_date": created,
                })
    return stores


def build_skus():
    return [
        {"sku_id": s, "sku_name": n, "category": c, "pack": p, "unit_price_thb": price}
        for s, n, c, p, price in cfg.SKUS
    ]


# ---------------------------------------------------------------- plans

def build_plans(reps, stores):
    days = working_days(cfg.START_DATE, cfg.END_DATE)
    stores_by_rep = defaultdict(list)
    for s in stores:
        stores_by_rep[s["rep_id"]].append(s)
    manager = {r["rep_id"]: r["manager_id"] for r in reps}

    plans, plan_no = [], 0
    for y, m in months_in_range(cfg.START_DATE, cfg.END_DATE):
        month_days = [d for d in days if (d.year, d.month) == (y, m)]
        first_of_month = date(y, m, 1)
        for rep_id, rep_stores in stores_by_rep.items():
            submitted = datetime.combine(first_of_month - timedelta(days=rng.randint(3, 8)), datetime.min.time()) \
                + timedelta(hours=rng.randint(9, 20), minutes=rng.randint(0, 59))
            approved = submitted + timedelta(hours=rng.randint(4, 72))
            load = defaultdict(int)  # visits already planned per day, to keep days even
            # Most frequent stores first, so they get the pick of the days.
            rep_stores = sorted(rep_stores, key=lambda s: -cfg.VISITS_PER_MONTH[s["grade"]])
            for s in rep_stores:
                active_days = [d for d in month_days if d >= s["created_date"]]
                n = min(cfg.VISITS_PER_MONTH[s["grade"]], len(active_days))
                if n == 0:
                    continue
                # Spread the visits evenly: one random day from each slice of the month.
                size = len(active_days) / n
                for i in range(n):
                    chunk = active_days[int(i * size):max(int((i + 1) * size), int(i * size) + 1)]
                    plan_date = min(chunk, key=lambda d: (load[d], rng.random()))
                    load[plan_date] += 1
                    plan_no += 1
                    plans.append({
                        "plan_id": f"PL-{plan_no:06d}",
                        "rep_id": rep_id,
                        "store_id": s["store_id"],
                        "plan_date": plan_date,
                        "submitted_at": submitted,
                        "approved_at": approved,
                        "approved_by": manager[rep_id],
                    })
    return plans


# ---------------------------------------------------------------- visits and orders

DURATION_MEDIAN_MIN = {"Grocery": 15, "Minimart": 20, "Convenience": 15, "Restaurant": 25, "Bar": 30}
ORDER_PROB = {"A": 0.70, "B": 0.50, "C": 0.35}
CASES_SCALE = {"A": 3.0, "B": 1.8, "C": 1.0}
CATEGORY_AFFINITY = {
    "Grocery":     {"Lager": 5, "Premium": 1, "Craft": 0.3, "Draught": 0, "Soda": 4, "Water": 4},
    "Minimart":    {"Lager": 5, "Premium": 2, "Craft": 1, "Draught": 0, "Soda": 3, "Water": 3},
    "Convenience": {"Lager": 4, "Premium": 2, "Craft": 1, "Draught": 0, "Soda": 3, "Water": 3},
    "Restaurant":  {"Lager": 5, "Premium": 3, "Craft": 1, "Draught": 1, "Soda": 2, "Water": 2},
    "Bar":         {"Lager": 4, "Premium": 3, "Craft": 3, "Draught": 3, "Soda": 1, "Water": 1},
}
# Craft beer grows month by month: a trend for the analysis to find.
CRAFT_GROWTH_PER_MONTH = 0.15


def pick_order_lines(store, visit_day, skus):
    affinity = dict(CATEGORY_AFFINITY[store["channel"]])
    months_in = (visit_day.year - cfg.START_DATE.year) * 12 + visit_day.month - cfg.START_DATE.month
    affinity["Craft"] *= 1 + CRAFT_GROWTH_PER_MONTH * months_in
    weights = [affinity[s["category"]] for s in skus]
    n_lines = rng.choice([1, 1, 2, 2, 3, 4])
    chosen = {}
    for _ in range(n_lines):
        sku = rng.choices(skus, weights=weights)[0]
        chosen[sku["sku_id"]] = sku
    lines = []
    for sku in chosen.values():
        qty = max(1, round(rng.lognormvariate(0, 0.5) * CASES_SCALE[store["grade"]]))
        lines.append((sku, qty))
    return lines


def build_visits(reps, stores, plans, skus):
    store_by_id = {s["store_id"]: s for s in stores}
    sales_reps = [r for r in reps if r["role"] == "Sales Rep"]
    compliance = {r["rep_id"]: cfg.REP_COMPLIANCE[i] for i, r in enumerate(sales_reps)}
    stores_by_rep = defaultdict(list)
    for s in stores:
        stores_by_rep[s["rep_id"]].append(s)

    plans_by_rep_day = defaultdict(list)
    for p in plans:
        plans_by_rep_day[(p["rep_id"], p["plan_date"])].append(p)

    visits, order_lines = [], []
    visit_no = 0
    for day in working_days(cfg.START_DATE, cfg.END_DATE):
        for rep in sales_reps:
            rep_id = rep["rep_id"]
            p_done = compliance[rep_id]
            if day.weekday() == 5:
                p_done *= cfg.SATURDAY_COMPLIANCE_FACTOR
            if day.month in cfg.RAINY_MONTHS:
                p_done *= cfg.RAINY_COMPLIANCE_FACTOR

            stops = []
            for p in plans_by_rep_day.get((rep_id, day), []):
                if rng.random() < p_done:
                    stops.append({**store_by_id[p["store_id"]], "plan_id": p["plan_id"]})
            # Unplanned drop-in visits.
            active = [s for s in stores_by_rep[rep_id] if s["created_date"] <= day]
            n_unplanned = sum(rng.random() < cfg.UNPLANNED_VISIT_RATE for _ in range(8))
            for s in rng.sample(active, min(n_unplanned, len(active))):
                stops.append({**s, "plan_id": ""})
            if not stops:
                continue

            clock = datetime.combine(day, datetime.min.time()) + timedelta(
                hours=9, minutes=rng.gauss(0, 20))
            for stop in nearest_neighbour_route(stops):
                clock += timedelta(minutes=rng.uniform(8, 25))  # travel
                duration = rng.lognormvariate(math.log(DURATION_MEDIAN_MIN[stop["channel"]]), 0.4)
                lat, lng = offset_point(stop["lat"], stop["lng"], abs(rng.gauss(0, 20)), rng.uniform(0, 360))
                checkout_missing = False

                roll = rng.random()
                if roll < cfg.ANOMALY_RATES["gps_far"]:
                    lat, lng = offset_point(stop["lat"], stop["lng"], rng.uniform(300, 2000), rng.uniform(0, 360))
                elif roll < cfg.ANOMALY_RATES["gps_far"] + cfg.ANOMALY_RATES["missing_checkout"]:
                    checkout_missing = True
                elif roll < (cfg.ANOMALY_RATES["gps_far"] + cfg.ANOMALY_RATES["missing_checkout"]
                             + cfg.ANOMALY_RATES["too_short"]):
                    duration = rng.uniform(0.5, 1.8)

                checkin = clock
                checkout = checkin + timedelta(minutes=duration)
                clock = checkout

                visit_no += 1
                visit = {
                    "visit_id": f"V-{visit_no:07d}",
                    "rep_id": rep_id,
                    "store_id": stop["store_id"],
                    "plan_id": stop["plan_id"],
                    "checkin_at": checkin.replace(microsecond=0),
                    "checkout_at": "" if checkout_missing else checkout.replace(microsecond=0),
                    "checkin_lat": round(lat, 6),
                    "checkin_lng": round(lng, 6),
                    "photo_count": 0 if rng.random() < 0.03 else rng.randint(1, 4),
                }
                visits.append(visit)

                if rng.random() < ORDER_PROB[stop["grade"]] and duration > 3:
                    for sku, qty in pick_order_lines(stop, day, skus):
                        order_lines.append({
                            "visit_id": visit["visit_id"],
                            "sku_id": sku["sku_id"],
                            "qty_cases": qty,
                            "unit_price_thb": sku["unit_price_thb"],
                            "amount_thb": qty * sku["unit_price_thb"],
                        })

                if rng.random() < cfg.ANOMALY_RATES["duplicate"]:
                    visit_no += 1
                    dup = dict(visit)
                    dup["visit_id"] = f"V-{visit_no:07d}"
                    dup["checkin_at"] = (checkin + timedelta(seconds=rng.randint(5, 90))).replace(microsecond=0)
                    visits.append(dup)
    return visits, order_lines


# ---------------------------------------------------------------- distributor stock

# These agent/SKU pairs are under-replenished, so they run out of stock.
UNDERSTOCKED = {("AG-02", "SKU-007"), ("AG-02", "SKU-008"), ("AG-04", "SKU-006")}


def build_stock(agents, stores, skus, visits, order_lines):
    agent_of_store = {s["store_id"]: s["agent_id"] for s in stores}
    visit_info = {v["visit_id"]: v for v in visits}

    first_monday = cfg.START_DATE - timedelta(days=cfg.START_DATE.weekday())
    weeks = []
    w = first_monday
    while w <= cfg.END_DATE:
        weeks.append(w)
        w += timedelta(days=7)

    demand = defaultdict(int)  # (agent, sku, week) -> cases ordered by stores
    for line in order_lines:
        v = visit_info[line["visit_id"]]
        d = v["checkin_at"].date()
        week = d - timedelta(days=d.weekday())
        demand[(agent_of_store[v["store_id"]], line["sku_id"], week)] += line["qty_cases"]

    rows = []
    for agent in agents:
        for sku in skus:
            key = (agent["agent_id"], sku["sku_id"])
            weekly = [demand[(*key, wk)] for wk in weeks]
            avg = max(1.0, sum(weekly) / len(weekly))
            # Healthy pairs keep about three weeks of stock; understocked ones under one.
            target = math.ceil(avg * (0.8 if key in UNDERSTOCKED else 3.0))
            on_hand = math.ceil(avg * 2)
            in_transit = 0
            for wk, dem in zip(weeks, weekly):
                received = in_transit
                available = on_hand + received
                sold = min(dem, available)
                closing = available - sold
                in_transit = max(0, target - closing)  # ordered now, arrives next week
                rows.append({
                    "week_start": wk,
                    "agent_id": agent["agent_id"],
                    "sku_id": sku["sku_id"],
                    "opening_qty": on_hand,
                    "received_qty": received,
                    "demand_qty": dem,
                    "sold_qty": sold,
                    "closing_qty": closing,
                })
                on_hand = closing
    return rows


# ---------------------------------------------------------------- output

def write_csv(name: str, rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name:<14} {len(rows):>7,} rows", file=sys.stderr)


def main() -> None:
    territories, reps = build_people()
    agents = build_agents(territories)
    stores = build_stores(reps, agents)
    skus = build_skus()
    plans = build_plans(reps, stores)
    visits, order_lines = build_visits(reps, stores, plans, skus)
    stock = build_stock(agents, stores, skus, visits, order_lines)

    write_csv("territories", territories)
    write_csv("reps", reps)
    write_csv("agents", agents)
    write_csv("stores", stores)
    write_csv("skus", skus)
    write_csv("visit_plans", plans)
    write_csv("visits", visits)
    write_csv("order_lines", order_lines)
    write_csv("agent_stock", stock)


if __name__ == "__main__":
    main()
