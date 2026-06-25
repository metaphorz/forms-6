# FORM S-6 — Interactive Grid + Windfields

## Goal
An interactive Leaflet web app over southern Florida that draws the official Form S-6
21×40 grid and runs selectable hurricane windfield models over it: **Powell** (PDE/slab),
**Holland**, and **Willoughby**. (An ERA5 4th option was considered and retired —
see Phase 4.) Supports the sensitivity/uncertainty analysis context of
Standard S-3 / Form S-6 in the ROA.

## Confirmed decisions (2026-06-18)
- **Scope:** Map + windfields first (phased). Loss-cost + SA/UA pipeline = later Phase 5.
- **Compute:** Hybrid. Powell (PDE) precomputed in Python → JSON. Holland +
  Willoughby computed live in the browser (analytic, instant interactivity).
- **ERA5:** Retired (2026-06-19). Originally planned as a 4th option; see Phase 4.

## Key facts (from ROA pp. 167–168, 182–191, 336–341 + Excel inputs)
- **Grid:** 21×40 = 840 vertices, ~3 statute-mile spacing.
  - E-W = 0,3,…,117 (40 columns); N-S = −15,−12,…,45 (21 rows).
  - Lat/lon for all 840 points are in the `Land-Water ID` sheet.
  - **682 land** (ID=1), 158 water (ID=0).
- **Track:** origin (0,0) = storm center at t=0, **9 mi east of landfall (25.8611 N,
  80.1196 W)**. Storm moves **due west** (0,0)→(117,0) over **12 hours**.
- **Inputs (`FormS6Input.xlsx`, 9 sheets):** CP, Rmax (st mi), VT (mph), WSP (shape),
  CF (conversion factor), FFP (mb), Quantile — 100 vectors × categories {1,3,5}.
  `FormS6InputQuantiles.xlsx` mirrors these as 0–1 quantiles. Sheet 1 = SA (all vars);
  sheets 2–8 = UA per variable; sheet 9 = Land-Water ID.
- **Pressure deficit:** dp = FFP − CP.
- **CF 3-zone radial rule (pp. 184–185):**
  - r < Rmax: CF·(r/Rmax)
  - Rmax < r < 3·Rmax: CF − [(r−Rmax)/(3Rmax−Rmax)]·0.1
  - r > 3·Rmax: CF − 0.1 (held constant)

## Reusable code
- `../storm-anim/hurricane_pde_marine.py` — implements all three models as functions:
  `pde_steady_marine` (Powell), `holland_asym_marine`, `willoughby_asym_marine`, with
  translation asymmetry + marine settings. Adapt to evaluate at the 840 grid points.
- `../era5tracks/web/` — Leaflet + canvas patterns, `start`/`stop` server scripts.

## Plan / Todo

### Phase 0 — Scaffold  ✅
- [x] Project venv + requirements (openpyxl, numpy)
- [x] Folder structure: `pipeline/`, `web/`, `outputs/web/`, `tests/auto/`
- [x] `start` / `stop` server scripts (port 8012)

### Phase 1 — Grid + map foundation  ✅
- [x] `pipeline/build_grid.py`: read `Land-Water ID` → `outputs/web/grid.json`
      (verified 840 pts, 682 land / 158 water, 40×21)
- [x] `web/index.html` + Leaflet: grid (land vs water), track (0,0)→(117,0),
      landfall marker, layer toggles, B-distribution UI control (default Uniform [1.0,2.5])

### Phase 2 — Windfield engine over the grid  (≈done)
- [x] `pipeline/read_inputs.py` → inputs.json (100×3 vectors, all variables)
- [x] `pipeline/windfield_grid.py`: Powell PDE → per-vertex 12-hr **peak** surface wind.
      Field computed once/vector (translation-invariant), sampled hourly t=0..12, CF
      3-zone conversion, dp=FFP−CP. ~2.4s/solve on MPS.
- [~] Precompute Powell all 100×3 → powell.json (running; cat1 done, peak 121 mph)
- [x] `web/windfield.js`: live Holland + Willoughby in JS — **validated** vs Python
      (Holland land-mean 76.3 mph == Powell marine 76.3 mph for cat1 v1).
- [x] **Surface roughness (rigorous)**: NLCD 2021 land cover (MRLC WCS, properly
      georeferenced) → modal class → published z0 table → **Vickery/ESDU gradient-tied
      log-law** marine→terrain ratio (`fetch_nlcd.sh` + `build_roughness.py`). Land-mean
      factor ≈0.67 (urban ~0.50, wetland ~0.70, water 1.0). Replaced the earlier
      heuristic+JPEG (whose georeferencing was wrong — sampling was spatially scrambled).
- [ ] **K&D land-effect selector**: replace roughness checkbox with 3-way
      None / Surface roughness / Kaplan–DeMaria decay (+Gulf recovery). (in progress)

### Phase 3 — Interactive viewer  ✅ (hour-animation deferred)
- [x] Controls: model, category {1,3,5}, input vector (1–100), B-distribution.
- [x] **"Color by" dropdown** (Max wind speed default; Land/Water option) + legend.
- [x] Hover vertex → tooltip: peak wind, (E-W,N-S) mi, lat/lon, land/water, **place name**
      (nearest area/county/state), input params.
- [x] **Display toggle: Points (default) / Filled contour** — banded filled contours on
      the 21×40 lattice (vendored d3-contour), matching ROA Figs 6–8.
- [x] **Light/Dark theme** toggle (dark default) — swaps basemap + sidebar.
- [x] **Place names**: `pipeline/add_place_names.py` (offline reverse_geocoder) → grid.json.
- [x] **Time-sampling fix**: peak envelope uses dt=0.1h (hourly aliased the fast westward
      storm → comb artifact in contours; fine sampling gives the true smooth peak).
- [x] `pipeline/build_all.sh` — one-command reproducible rebuild (dependency order).
- [ ] Hour slider / animate (t=0..12) — deferred (peak-wind is the agreed metric).

### Phase 4 — ERA5 4th option  ❌ RETIRED (2026-06-19)
- [x] Removed the inert "ERA5 (coming soon)" dropdown entry.
- **Rationale:** ERA5 is a *reanalysis* (fixed, already-observed field), not a
  *parametric* model. It cannot be a peer to Powell/Holland/Willoughby:
  - **Paradigm mismatch:** the 3 models are generated from tunable inputs
    (CP, Rmax, VT, WSP, CF, FFP); ERA5 has no such knobs, so category {1,3,5},
    input-vector 1–100, and the B-distribution controls would all be inert.
  - **SA/UA undefined:** SRC/EPR require perturbing the 6 inputs; a single fixed
    reanalysis field has nothing to vary.
  - **Resolution:** ERA5 ~0.25° (~28 km) under-resolves the TC inner core and
    systematically damps peak winds — the exact quantity (peak wind → loss) the
    app reports — and yields only ~8–12 cells over the southern-FL domain vs. 840
    grid vertices.
- **If revisited later**, the only coherent roles are (A) a clearly-labeled,
  per-historical-storm *validation overlay* (storm/date picker; coarse), or
  (B) using ERA5's well-resolved large scales (CP, track, translation speed) to
  *estimate* the input vector fed into the existing parametric models — a
  separate feature, not a dropdown entry.

### Phase 4.5 — Sensitivity & Uncertainty Analysis  ✅ (v1)
- [x] **SA → SRC**: standardized regression of output on the 6 inputs (CP, Rmax, VT,
      WSP, CF, FFP) over the 100 "SA all Variables" vectors, per category. (`analysis.js`)
- [x] **UA → EPR**: EPR_i = SRC_i²·100% (Option 2 variance-share approximation; valid for
      ~independent inputs). Uniform for all 3 models in v1.
- [x] Output metric: **mean peak wind over 682 land vertices** (wind proxy; → loss in P5).
- [x] UI: **Analysis** buttons (Sensitivity / Uncertainty) → SVG line chart x=cat {1,3,5},
      one line per variable + legend + R² (lightweight SVG, no new dep). ROA Figs 9/10 analog.
- [x] SRC + EPR open as **independent floating windows** — both viewable at once,
      **draggable** (title bar) and **resizable** (corner handle); bring-to-front on click.
- [x] **Validated**: SRC signs/ranking match ROA Fig 9 (WSP dominant cat1, CP negative,
      CF/FFP/Rmax positive).
- [ ] Option 1 (faithful Powell EPR via 1800-solve UA-sheet precompute) — optional, later.
- [ ] ASCII/PDF export of SA/UA (XXX25SA, XXX25UA) — Phase 5.

### Phase 5 — Full Form S-6 analysis (later)
- [ ] Loss costs at 682 land points; 300-row + 2,046-row ASCII/PDF outputs;
      CDF (Fig 5), contour (Figs 6–8), SRC (Fig 9), EPR (Fig 10).

## Resolved (2026-06-18)
- **Output metric:** per-vertex **peak (12-hr max) surface wind speed** is sufficient for
  now. Loss costs deferred to Phase 5.
- **Powell precompute:** all 100 vectors × 3 categories (300 PDE solves).
- **WSP → B (shape parameter):** WSP is a quantile p∈[0,1]; convert via inverse-CDF of a
  user-chosen distribution for Holland's B (shared shape knob across all 3 models).
  **UI control** lets the user pick the family + parameters:
    - Uniform: [Bmin, Bmax]  — **default Uniform [1.0, 2.5]**  → B = Bmin + p·(Bmax−Bmin)
    - Triangular: [Bmin, Bmode, Bmax]
    - Normal: [mean, std] (clamped to a sane range)
  Powell precompute uses the default; Holland/Willoughby recompute live in JS when the
  user changes the distribution.

## Conventions
- **Selenium** is used to (a) analyze/verify the web interface during development and
  (b) generate all figures when `docs/` is built later (as in other ~/code projects).

## Open questions for later
- (ERA5 4th-option resolved — retired; see Phase 4.)

## Mean / CSV buttons (2026-06-23) — DONE
Two buttons below the Input-vector slider.

Decisions confirmed with user:
- **CSV scope:** all 3 categories (300 rows + header). `Category` column is the bare
  number (1/3/5), per follow-up request.
- **Mean mode:** persistent toggle that overrides the slider (slider greyed while active);
  mean is over all 100 input vectors.

Done:
- [x] `index.html`: `<div class="vec-actions">` with `#btnMean` + `#btnCsv` under the slider.
- [x] `style.css`: `.vec-actions` / `.vec-btn` (+ `.active` green) styles; greyed disabled slider.
- [x] `viewer.js`: `state.meanMode`; `computeMeanWind(model,cat)` averages per-point wind
      over all 100 vectors (respects current model/category/land-effect/B); `computeWind()`
      returns the mean field when `meanMode`.
- [x] `viewer.js`: wired `#btnMean` (toggle, disable slider, deferred "Computing…" status)
      and `#btnCsv` (`downloadInputsCsv()` builds CP,Rmax,VT,WSP,CF,FFP for all 3 cats).
- [x] `viewer.js`: `pointInfoHTML` + info `tag` read "mean (100 vectors)" in mean mode.
- [x] Selenium test `tests/auto/test_mean_csv_buttons.py` — Powell + Holland mean, toggle,
      slider-disable, and 300-row CSV download. **ALL CHECKS PASSED.**

## Metamodel + Interaction Profiler — Phase A (2026-06-23) — DONE
From the chris/ deck (Mark Johnson / "Other Chris", 6/5/26): upgrade SA from a
first-order linear regression to an interactive **metamodel** with an **interaction
profiler**, and allow the response Y to be either mean peak wind or loss cost %TLC.
Phase A is pure JS (no new deps / no Python precompute); GPR + neural-net
metamodels are Phase B.

Confirmed with user:
- Start with **Phase A** (pure JS).
- Response Y is **user-toggleable**: mean peak wind (current) OR loss cost %TLC(i).

Definitions:
- %TLC(i) = TLC(i)/total_exposure, TLC(i)=Σ_land LC(i,x,y), LC=MDR(wind)·$100k,
  total_exposure = 682·$100k = $68.2M  ⇒  %TLC(i) = 100·mean(MDR over 682 land pts).
  (Needs state.vuln — loaded. Equivalent to the ROA definition.)
- Second-order response-surface metamodel (lets the profiler bend / show interactions):
  Ŷ = b0 + Σ bᵢxᵢ + Σ bᵢᵢxᵢ² + Σ_{i<j} bᵢⱼxᵢxⱼ   (standardized inputs; 28 terms, n=100).
  Fit by least squares via the existing solve() on the normal equations XᵀX β = Xᵀy.

Done:
- [x] `index.html`: Response selector (Mean peak wind / Loss cost %TLC) + buttons
      **Interaction Profiler** and **%TLC CDF** in the Analysis section.
- [x] `analysis.js`: `responseVar()`, `pctTLC()`, `outputMetric()`; computeSRC routed
      through outputMetric; getData cache key includes `resp`; faithful-EPR guarded to
      wind response; SRC/EPR footnote is response-aware.
- [x] `analysis.js`: `rsmFeatures` + `fitRSM` (standardized 2nd-order RSM, 28 terms,
      ridge-stabilized normal equations via existing `solve`) + `rsmPredict`.
- [x] `analysis.js`: **Interaction Profiler** panel (`drawProfiler`/`buildProfilerDOM`/
      `updateProfilerPlots`) — 6 colour-coded partial-dependence subplots + 6 sliders;
      slider drag redraws only the curves (sliders stay live); category-aware.
- [x] `analysis.js`: **%TLC empirical CDF** panel (`drawCDF`) — sorted step plot, 100 vectors.
- [x] `analysis.js`: panel dispatch (`renderPanel`) + `redrawOpenPanels`; category change
      redraws prof/cdf only.
- [x] `style.css`: `.prof-grid` / `.prof-cell` / `.prof-sliders` styles.
- [x] Selenium test `tests/auto/test_profiler_cdf.py` — 6 subplots+sliders, moving CP
      changed 5/6 curves (interactions visible), %TLC re-render, CDF renders. **PASSED.**
      No regression: `test_mean_csv_buttons.py` still passes; SRC works for wind + %TLC.

## Metamodels Phase B (machine-learning metamodels) — DONE (2026-06-23)
Built and Selenium-tested. GPR + NN fit offline (scikit-learn) → metamodels.json;
browser evaluates only. Defaults unchanged (Metamodel=Linear (RSM), Color-by=wind,
Response=wind) — verified by the Phase A regression test still passing.

Implemented:
- `pipeline/fit_metamodels.py`: fits GPR (ARD) + MLP (tanh, 5-fold CV) per
  category × response for the DEFAULT config (Powell+roughness, Option A); exports
  θ/weights/scalers/R²/CV + Sobol S1/ST. In-process parity checks vs sklearn
  predict: GPR max|Δ|=9e-10, MLP max|Δ|=0. Needs scikit-learn (added to venv).
- `web/analysis.js`: `gprPredictRaw`/`mlpPredictRaw` evaluators; `buildMetamodel`
  dispatcher; profiler now metamodel-driven; `Compare metamodels` panel (overlaid
  Linear/GPR/NN + R²/CV table); EPR shows Sobol total-effect when GPR selected;
  `computeGridSensitivity` (per-vertex dominant input).
- `web/viewer.js`: loads metamodels.json; `Sensitivity (dominant input)` colour mode.
- `index.html`/`style.css`: +1 Metamodel dropdown, +1 Compare button, +1 colour-by
  option, compare-table styles.
- Tests: `tests/auto/test_metamodels.py` (GPR/NN switch, compare 3-series+table,
  Sobol EPR, grid sensitivity colours+legend) — PASSED. Phase A test still PASSES.
- Figures added to `docs/capture_figures.py`: analysis_compare, grid_sensitivity.

Note: all metamodels hit R²≈1 (smooth deterministic simulator) as predicted — the
value is diagnostic (ARD ranking, Sobol indices, 3-way agreement), not accuracy.
Sobol ST top variable: WSP (Cat 1/3) → Rmax (Cat 5), matching the ROA finding.

### (historical) original Phase B plan
Upgrade the metamodel backend from the second-order response surface to
machine-learning metamodels, per the 6/5/26 deck. Preserves the app's existing
hybrid pattern: **train offline in Python → export JSON → the browser only
evaluates** (identical to how Powell already works). The deployed site stays a
zero-backend static page (GitHub Pages unaffected).

### Training / execution model (decided 2026-06-23)
Training runs **offline, in the dev/precompute step** (like Powell) — NOT on a
button press. The UI only *evaluates* pre-fit models loaded from JSON (kernel
dot-product for GPR, forward pass for the NN); instant, and the deployed site
stays a zero-backend static page. A button that trained would need in-browser
training (awkward) or a live server (breaks GitHub Pages) — rejected.

**Config scope = Option A (chosen).** GPR/NN are precomputed for ONE canonical
configuration per (category × response) — default model + land effect
(Powell + roughness). Changing land-effect or B-distribution leaves GPR/NN
fixed to that default (gray out / "default config" note); **Linear/RSM stays
live for every config** as the always-available baseline. Option B (precompute
the full model × land × response × category grid so GPR/NN track every toggle)
is a later expansion if needed.

### Reality check (decide before building)
With Powell the simulator is smooth + deterministic, so the linear/RSM metamodel
already gives R²≈1.0. GPR/NN will NOT predict better — their value here is
**diagnostic**: ARD length-scales as a sensitivity ranking, variance-based
(Sobol) total/interaction indices, and confirming the interaction structure three
independent ways (Linear vs GPR vs NN). Build Phase B for the diagnostics, not
for accuracy.

### Pieces
1. **GPR metamodel** — scikit-learn `GaussianProcessRegressor`, ARD kernel, per
   category, per response (wind / %TLC). Export length-scales θ (= sensitivity),
   kernel hyperparameters, training points + α, and R²/CV.
2. **Neural-net metamodel** — `MLPRegressor` (~2 layers × 6 nodes, 5-fold CV).
   Export weights/biases + activation + input scaling + R²/CV.
3. **Comparison** — Linear vs GPR vs NN: R²/CV table + overlaid profiler curves.
4. **Variance-based indices** — Sobol total + two-factor interaction indices from
   GPR (slide 26); feeds the existing EPR panel when Metamodel = GPR.
5. **Grid-point-level SA map** — sensitivity computed at every vertex (not the
   land-mean), surfaced as a map colour mode (dominant input per vertex, or a
   chosen variable's importance).

### UI footprint (small — mostly reuse)
- `index.html` Analysis section: **+1 dropdown** `Metamodel: Linear (RSM) / GPR /
  Neural net` (drives the existing Interaction Profiler + SRC), **+1 button**
  `Compare metamodels` (new overlay panel).
- Existing **EPR panel** gains Sobol total/interaction indices when GPR selected
  (no new button; maybe a tiny main/total toggle).
- Existing **Color grid by** dropdown: **+1 option** `Sensitivity (dominant input)`
  (+ optional per-variable picker) for the grid-point SA map.
- Interaction Profiler, %TLC CDF, Response toggle: unchanged, reused as-is.

### Build outline
- [ ] `pipeline/`: Python script fits GPR + MLP per (category × response) for the
      default config only (Powell + roughness, Option A) over the 100 LHC vectors;
      writes `outputs/web/metamodels.json` (θ, weights, R²/CV, Sobol indices).
      Mirrors the Powell precompute step; runnable via a shell script.
      (Linear/RSM is NOT precomputed — it stays live in the browser.)
- [ ] `web/analysis.js`: JS predictors `gprPredict()` (kernel eval vs training pts)
      and `mlpPredict()` (forward pass); route `fitRSM`→ a metamodel dispatcher
      keyed by the new dropdown.
- [ ] `web/analysis.js`: `Compare metamodels` panel (R²/CV + overlaid profiles);
      EPR panel reads Sobol indices for GPR.
- [ ] `web/viewer.js` + `analysis.js`: grid-point SA colour mode in `updateField`.
- [ ] `index.html` / `style.css`: the +1 dropdown, +1 button, +1 colour-by option.
- [ ] Selenium tests in `tests/auto/`: metamodel switch re-renders profiler;
      compare panel shows 3 series; grid-point SA colours the map.
- [ ] Docs: extend §5 with GPR/NN, ARD, Sobol indices; new Selenium figures.

### Open question for later
- Separate interactive *training/DOE bench* (live refit, CNNDOE designs) — if
  wanted, that is a distinct Python/notebook companion, NOT this static viewer.
  This app only ever *evaluates* pre-fit models.

## Powell wind-vs-time cliff fix (2026-06-23)
The Powell popup's "wind vs time" curve dropped abruptly to 0 (unlike Holland/
Willoughby's smooth decay). Cause: the stored storm-relative field spanned only
+/-90 km, where Powell winds are still ~66-69 mph; the popup sampler returns a
hard 0 outside that box, so the curve cliffs once the storm-relative track exits
+/-90 km. The PDE itself and the peak-wind map are correct (the map samples the
PDE directly out to 250 km).

Fix (Option 1): widen the stored field to +/-250 km (the PDE solver's rmax_km),
keeping N=81. Winds reach 0 at the 250 km solver boundary, so the curve now
decays smoothly. No JS change needed (popup reads halfKm from the JSON).

- [x] windfield_grid.py: FIELD_HALF_KM 90 -> 250 (N=81, step 2.25 -> 6.25 km)
- [x] Re-run windfield_grid.py to regenerate powell_field.json (779s, 300 solves)
- [x] Verify the field edge now decays toward 0

Result: cat3 center-row now reads 0 (eye) -> ~56 mph at +/-125 km -> ~32 mph at
the +/-250 km solver boundary -> 0 in the corners. The old +/-90 km edge was
~66-69 mph clipped straight to 0; now the curve decays smoothly across the full
storm extent. powell.json / powell_kd.json peak winds unchanged (those already
sampled the PDE to 250 km). No JS change needed.

## Per-grid-point loss-cost CSV (2026-06-24) — DONE
Replaced the global **CSV** button (exported all 100 input vectors x 3 categories)
with a **right-click any grid vertex** action that exports a per-point loss-cost
CSV, per the statistician's spec.

- [x] `index.html`: removed `#btnCsv` from the vec-actions div (only `#btnMean` remains).
- [x] `viewer.js`: removed `downloadInputsCsv()` + its listener; added
      `downloadGridPointCsv(idx)` and a `contextmenu` handler on the nearest dot.
- [x] CSV: 100 rows (one per input vector i) x 8 columns for the current
      model/category/land-effect:
      `CP, Rmax, VT, WSP, CF, FFP, %LC, %TLC` where
      `%LC(i,x,y) = LC(i,x,y)/$100,000` (loss cost at that vertex; 0 on water) and
      `%TLC(i) = TLC(i)/(total exposure)`, `TLC(i) = sum_x sum_y LC(i,x,y)` over all
      land vertices. Total exposure = `n_land * $100,000` (= $68.2M), not hardcoded.
      Filename: `formS6_losscost_<cat>_x<ew>_y<ns>.csv`.
- [x] Selenium test `tests/auto/test_gridpoint_csv.py` — button gone, 8x100 CSV
      captured from the right-click handler, no console errors. **PASSED.**
- [x] Docs: updated `docs/FormS6.tex` interface paragraph; regenerated
      `docs/figures/grid_sensitivity.png` (the only figure showing the old CSV
      button) via the canonical settings in `docs/capture_figures.py`; rebuilt
      `docs/FormS6.pdf`.

## Contour-mode info readout fix (2026-06-24) — DONE
The bottom-left status line showed `Peak wind 0.0 mph · land mean – mph` (and
`$0.00M` loss) whenever Display = Filled contour. Cause: peak/land-mean/loss were
tallied inside the per-vertex marker-styling loop, which early-`return`s on hidden
markers — and in contour mode every dot is hidden. The contour overlay itself was
always correct (drawn from a separate copy of the wind array); only the text was wrong.

- [x] `web/viewer.js`: in `updateField`, accumulate the summary stats from the
      `wind` field before the visibility gate, so the readout is correct in both
      points and contour modes. Marker styling unchanged.
- [x] Verified via Selenium: Powell CAT5 v1 now reads Peak 148.7 / land mean 78.2
      (wind) and $19.28M = 28.27% (loss) identically in points and contour modes;
      `test_gridpoint_csv.py` still passes; no console errors.

## Points of Interest panel + printable detail page (2026-06-24) — DONE
Built and Selenium-tested. Lower-right map panel lists user grid points by
`(ew,ns)`; insert/delete with validation; gold-star markers on the map; click a
point for a draggable detail panel combining the hover summary + windfield
isotach/time-series, with a **Print / Save PDF** button (opens a clean print
window → browser print dialog → printer or PDF). POIs persist in `localStorage`
(reset link restores the 5 defaults). Approved options: localStorage + markers.
- `web/popup.js`: extracted `windfieldBodyHTML(idx)` (shared by left-click popup
  and POI detail — left-click popup verified still rendering 2 SVGs).
- `web/poi.js` (new): POI state/UI/markers/detail/print.
- `index.html`: `#poiPanel` map overlay + `poi.js`; `style.css`: panel/marker/print.
- `web/viewer.js`: `setupPoi()` in `init()`.
- Test `tests/auto/test_poi.py`: defaults=5, add→6, bad coord errors, detail has
  hover text + 2 SVGs + Print btn, delete→5, no console errors. **PASSED.**
- Docs: `docs/FormS6.tex` Points-of-Interest paragraph + figure
  `points_of_interest.png` (added to `capture_figures.py` with a new `_js` hook);
  rebuilt `docs/FormS6.pdf`.

### Original plan (for reference)

### Goal
A **Points of Interest** area in the lower-right of the map where the user can
insert/delete grid points by `(ew,ns)` coordinate. Clicking a POI opens an in-app
detail panel that combines BOTH the hover details and the left-click windfield
image for that point, and the panel is **savable / printable to printer or PDF**.

### Coordinate system (confirmed from grid.json)
Points are addressed by `(ew, ns)` in miles on a 3-mile grid:
`ew ∈ {0,3,…,117}` (40 values), `ns ∈ {-15,-12,…,45}` (21 values), 840 vertices.
Insert validation = both multiples of 3 in range AND an existing grid vertex.

### Initial POIs (5, per your answer)
`(9,15) (15,0) (60,0) (12,-12) (6,45)` — all land points (Dania Beach, Pinewood,
Kendall West, Key Biscayne, Boynton Beach).

### Design decisions (from your answers)
- Detail view = **in-app draggable panel** (like the existing windfield/analysis
  panels), stacking hover details over the isotach + wind-vs-time plots.
- **Print / Save PDF**: a button in the detail panel opens a clean print view and
  calls `window.print()`, so the OS dialog can print or "Save as PDF".

### To do
- [ ] `web/popup.js`: extract the windfield body builder into a reusable
      `windfieldBodyHTML(idx)` returning `{title, html}` (or `null` if no field).
      `openWindfieldPopup` calls it; the POI detail panel reuses it (DRY, no
      behavior change to the existing left-click popup).
- [ ] `web/poi.js` (new): POI state + UI.
      - defaults + `localStorage` persistence (so inserts/deletes survive reload;
        a small "reset" link restores the 5 defaults).
      - `gridIdx(ew,ns)` lookup; `addPoi`/`removePoi` with validation + a clear
        inline error for bad/duplicate/off-grid coordinates.
      - `renderPoiPanel()`: list of `(ew,ns) — place`, each row with a **view**
        action and a **×** delete; an `ew,ns` input + **Add** button on top.
      - `openPoiDetail(idx)`: combined panel = `pointInfoHTML(idx)` (hover details)
        + `windfieldBodyHTML(idx)` (isotach + time series) + a **Print / Save PDF**
        button; draggable/closable like the windfield panel.
      - `printPoiDetail(idx)`: opens a minimal print window with the same content
        and the app title/coords as a header, then `window.print()`.
      - small POI markers on the map (so points are findable); toggle with the
        existing Layers section is optional — default on.
- [ ] `index.html`: `#poiPanel` map overlay (lower-right) + load `web/poi.js`.
- [ ] `web/style.css`: styles for `#poiPanel`, the detail panel, the POI markers,
      and an `@media print` block so the print view is clean (no map/sidebar).
- [ ] `web/viewer.js`: call `setupPoi()` from `init()` after the map is built.
- [ ] Selenium test `tests/auto/test_poi.py`: 5 defaults present; add (30,-6) →
      6 rows; delete one → 5; open a detail → has hover text + 2 SVG plots +
      Print button; bad coord shows error; no console errors.
- [ ] Docs: add a short Points-of-Interest paragraph to `docs/FormS6.tex`; capture
      one figure of the panel + open detail page; rebuild the PDF.

### Open question
- Persist POIs in `localStorage` (survive reload) vs session-only? Plan assumes
  **localStorage + a reset link**. Say the word if you'd rather they reset each load.

## Max button + MaxWind CSV column (2026-06-25) — DONE
Added a **Max** aggregation toggle to the right of **Mean**, and a 9th column to
the right-click per-point CSV.
- `web/viewer.js`: `state.maxMode`; `computeMaxWind()` (per-vertex max — worst-case
  envelope over the 100 vectors, mirroring `computeMeanWind`); `aggLabel()` helper;
  `computeWind()`/`pointInfoHTML`/info-tag now mean/max-aware; `setAggMode()` makes
  Mean and Max mutually exclusive (either disables the vector slider; clearing both
  re-enables it). Default unchanged (Mean on).
- `index.html`: `#btnMax` next to `#btnMean`.
- Right-click CSV now 9 cols: `…,FFP,MaxWind_mph,%LC,%TLC` — `MaxWind_mph` = peak
  wind at the clicked vertex for input vector i (the driver of `%LC`; distinct from
  the VT input, which is the storm's forward speed).
- Tests: new `tests/auto/test_mean_max_buttons.py` (Mean default, Max exclusive,
  envelope peak ≥ mean peak, slider re-enable, Holland live max) replaces the
  obsolete `test_mean_csv_buttons.py`; `test_gridpoint_csv.py` updated to 9 cols.
  Both **PASS**, no console errors.
- Docs: `docs/FormS6.tex` interface paragraph (Mean/Max + 9-col CSV); rebuilt PDF.

## Axis titles on all analysis plots (2026-06-25) — DONE
The analysis charts had tick numbers but no axis titles. Added them:
- `web/analysis.js` `drawChart` (SRC/EPR): rotated y-title ("SRC (standardized
  regression coeff.)" / "EPR (% of output variance)") + x-title "Hurricane
  category" (margins widened to fit).
- `drawCDF`: y-title "cumulative probability F(x)" + x-title "%TLC (loss cost,
  % of $68.2M exposure)".
- `drawProfiler`/`drawCompare` small-multiples: a shared `.prof-axis` caption
  ("Each panel — y: <metric> · x: the named input over its range"); each cell keeps
  its variable name as the x label. `web/style.css`: `.prof-axis`.
- Windfield popup plots already carried axis labels (isotach: km E / km N;
  time series: "wind (mph) vs time" + hour ticks) — left as-is.
- `docs/capture_figures.py`: added an optional name filter so a change can refresh
  just its figures. Regenerated analysis_src/epr/profiler/tlc_cdf/compare; rebuilt PDF.

## Review
_(to be filled in as work proceeds)_
