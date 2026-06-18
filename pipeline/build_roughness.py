#!/usr/bin/env python3
"""Per-grid-point surface-roughness reduction factor → roughness.json.

Source: NLCD 2021 Land Cover (30 m), fetched as a properly georeferenced GeoTIFF
clip for the grid bbox via the MRLC WCS (see pipeline/fetch_nlcd.sh). For each of
the 840 grid vertices we take the modal NLCD class in a small window, map it to an
aerodynamic roughness length z0 via a published land-cover->z0 table, then convert
the marine-exposure wind to terrain with the gradient-tied LOG-LAW
(Vickery et al. 2009 / ESDU exposure model):

    factor = [ln(z_ref/z0_land)/ln(z_g/z0_land)] / [ln(z_ref/z0_marine)/ln(z_g/z0_marine)]

i.e. tie the wind at gradient height z_g (same upper wind over both exposures),
then take the ratio of 10 m mean winds. Water/ocean -> ~1.0 (already marine).

The factor is per-location and wind-speed-independent, so the viewer applies it as
a client-side multiplier on the final (marine-surface) wind for ALL models — the
toggle is instant and the marine Powell precompute is reused as-is.

NLCD 2021 is the latest per-year land-cover raster on the MRLC WCS (the 2023
Annual NLCD is distributed elsewhere); the 2021->2023 difference is negligible for
surface roughness.

Inputs : outputs/web/grid.json, data/nlcd_grid.tif
Output : outputs/web/roughness.json  { factors: [840], ... }
"""
import os, json
import numpy as np
import rasterio
from rasterio.transform import rowcol

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "outputs", "web")
GRID = os.path.join(WEB, "grid.json")
NLCD = os.path.join(ROOT, "data", "nlcd_grid.tif")
OUT = os.path.join(WEB, "roughness.json")

# NLCD land-cover class -> aerodynamic roughness length z0 (m).
# Representative values from Vickery et al. (2009) / EPA AERSURFACE / WRF tables.
Z0_BY_CLASS = {
    0: 2e-4,    # NoData / open ocean -> marine
    11: 2e-4,   # open water
    12: 1e-3,   # perennial ice/snow
    21: 0.05,   # developed, open space
    22: 0.30,   # developed, low intensity (suburban)
    23: 0.70,   # developed, medium intensity
    24: 1.00,   # developed, high intensity (urban core)
    31: 0.01,   # barren
    41: 0.65, 42: 0.65, 43: 0.65,   # forest (decid/everg/mixed)
    51: 0.10, 52: 0.10,             # shrub/scrub
    71: 0.04, 72: 0.04, 73: 0.04, 74: 0.04,   # herbaceous
    81: 0.05, 82: 0.05,             # pasture / crops
    90: 0.50,   # woody wetland (mangrove/cypress)
    95: 0.15,   # emergent herbaceous wetland (sawgrass marsh)
}

# log-law terrain-conversion parameters
Z0_MARINE = 2e-4
Z_REF = 10.0
Z_G = 500.0
_MARINE_TERM = np.log(Z_REF / Z0_MARINE) / np.log(Z_G / Z0_MARINE)
WIN_PX = 8          # half-window (px) for modal class (~500 m @ 30 m)


def factor_from_z0(z0v):
    """Gradient-tied log-law marine->terrain 10 m wind ratio (<= 1.0)."""
    z0_land = max(float(z0v), Z0_MARINE)
    land_term = np.log(Z_REF / z0_land) / np.log(Z_G / z0_land)
    return float(min(land_term / _MARINE_TERM, 1.0))


def main():
    grid = json.load(open(GRID))
    ds = rasterio.open(NLCD)
    band = ds.read(1)
    H, W = band.shape

    factors, classes = [], []
    for p in grid["points"]:
        r, c = rowcol(ds.transform, p["lon"], p["lat"])
        r0, r1 = max(0, r - WIN_PX), min(H, r + WIN_PX + 1)
        c0, c1 = max(0, c - WIN_PX), min(W, c + WIN_PX + 1)
        win = band[r0:r1, c0:c1].ravel()
        cls = int(np.bincount(win).argmax()) if win.size else 0   # modal class
        z0 = Z0_BY_CLASS.get(cls, 0.05)
        classes.append(cls)
        factors.append(round(factor_from_z0(z0), 4))

    out = {
        "factors": factors,
        "note": "NLCD-2021 z0 + gradient-tied log-law (Vickery/ESDU) marine->terrain 10m ratio",
        "method": {"model": "log-law gradient-tied", "z0_marine": Z0_MARINE,
                   "z_ref": Z_REF, "z_g": Z_G, "win_px": WIN_PX},
        "source": "NLCD 2021 Land Cover (MRLC WCS)",
    }
    json.dump(out, open(OUT, "w"))

    arr = np.array(factors)
    land = [f for q, f in zip(grid["points"], factors) if q["land"]]
    from collections import Counter
    print(f"Wrote {OUT}")
    print(f"  factors: {len(factors)}  range [{arr.min():.3f}, {arr.max():.3f}]")
    print(f"  land mean factor: {np.mean(land):.3f}")
    top = Counter(classes).most_common(8)
    print(f"  modal classes (class:count): {top}")


if __name__ == "__main__":
    main()
