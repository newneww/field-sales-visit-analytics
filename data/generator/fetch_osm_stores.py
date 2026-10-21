"""Download real shop and restaurant locations in Bangkok from OpenStreetMap.

Optional step. When data/raw/osm_stores.csv exists, generate.py places the
simulated stores at these real locations; without it, generate.py scatters
stores around the district centres in config.py instead.

Data (c) OpenStreetMap contributors, available under the Open Database
License (ODbL): https://www.openstreetmap.org/copyright

Usage:
    python data/generator/fetch_osm_stores.py
"""
import csv
import sys
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OUT_PATH = Path(__file__).resolve().parents[1] / "raw" / "osm_stores.csv"

# Bounding box roughly covering the districts in config.TERRITORIES.
SOUTH, WEST, NORTH, EAST = 13.64, 100.40, 13.95, 100.73

# OSM tag -> channel used in this project.
CHANNELS = {
    ("shop", "convenience"): "Convenience",
    ("shop", "supermarket"): "Minimart",
    ("shop", "general"): "Grocery",
    ("shop", "kiosk"): "Grocery",
    ("amenity", "restaurant"): "Restaurant",
    ("amenity", "bar"): "Bar",
    ("amenity", "pub"): "Bar",
}

QUERY = f"""
[out:json][timeout:120];
(
  node["shop"~"^(convenience|supermarket|general|kiosk)$"]({SOUTH},{WEST},{NORTH},{EAST});
  node["amenity"~"^(restaurant|bar|pub)$"]({SOUTH},{WEST},{NORTH},{EAST});
);
out body;
"""


def channel_of(tags: dict) -> str | None:
    for (key, value), channel in CHANNELS.items():
        if tags.get(key) == value:
            return channel
    return None


def main() -> None:
    resp = requests.post(OVERPASS_URL, data={"data": QUERY}, timeout=180)
    resp.raise_for_status()
    elements = resp.json()["elements"]

    rows = []
    for el in elements:
        tags = el.get("tags", {})
        channel = channel_of(tags)
        if channel is None:
            continue
        name = tags.get("name:th") or tags.get("name") or ""
        rows.append({
            "osm_id": el["id"],
            "name": name,
            "channel": channel,
            "lat": el["lat"],
            "lng": el["lon"],
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["osm_id", "name", "channel", "lat", "lng"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} places to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
