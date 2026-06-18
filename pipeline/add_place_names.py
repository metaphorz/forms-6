#!/usr/bin/env python3
"""Add a place name (nearest area/subarea) to each grid vertex in grid.json.

Uses the offline reverse_geocoder (GeoNames cities1000) — no network calls — to
label every one of the 840 vertices with its nearest populated place, county
(admin2), and state (admin1). The viewer shows this next to the land/water flag.

Run from a file (not stdin) and mode=1 to avoid the package's multiprocessing
issues. Rewrites outputs/web/grid.json in place (adds a "place" field).
"""
import os, json
import reverse_geocoder as rg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GRID = os.path.join(ROOT, "outputs", "web", "grid.json")


def label(r):
    name = (r.get("name") or "").strip()
    county = (r.get("admin2") or "").strip()
    state = (r.get("admin1") or "").strip()
    parts = [p for p in (name, county, state) if p]
    # de-dupe consecutive repeats (e.g. name == county)
    out = []
    for p in parts:
        if not out or out[-1] != p:
            out.append(p)
    return ", ".join(out)


def main():
    grid = json.load(open(GRID))
    pts = grid["points"]
    coords = [(p["lat"], p["lon"]) for p in pts]
    results = rg.search(coords, mode=1)        # single-threaded, offline
    for p, r in zip(pts, results):
        p["place"] = label(r)

    json.dump(grid, open(GRID, "w"))

    # quick report: sample a few + distinct count
    distinct = sorted({p["place"] for p in pts})
    print(f"Labeled {len(pts)} vertices; {len(distinct)} distinct places.")
    for p in (pts[0], pts[len(pts)//2], pts[-1]):
        print(f"  ({p['ew']},{p['ns']}) {p['lat']:.3f},{p['lon']:.3f} "
              f"[{'land' if p['land'] else 'water'}] -> {p['place']}")
    print("Sample of distinct places:", "; ".join(distinct[:12]))


if __name__ == "__main__":
    main()
