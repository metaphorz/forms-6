/* Live Holland & Willoughby windfields over the Form S-6 grid (client-side).
   Mirrors pipeline/windfield_grid.py + hurricane_pde_marine.py physics:
   gradient wind -> inflow rotation -> translation asymmetry -> CF conversion.
   Powell (PDE) is precomputed in Python; these two are cheap enough to run live. */

const PHYS = {
  MILE_M: 1609.344,
  MS_TO_MPH: 2.2369362920544,
  RHO: 1.15,
  OMEGA: 7.2921159e-5,
  LAT0: 25.8611,          // constant-latitude due-west track
  BEARING: 270.0,         // due west
  T_MAX: 12.0, T_DT: 0.1, // fine time sampling for the 12-hr peak envelope
  BETA10: 1.0,            // gradient level; CF does surface conversion
};

function coriolis(latDeg) {
  return 2 * PHYS.OMEGA * Math.sin(latDeg * Math.PI / 180);
}

// inflow angle (radians) — matches inflow_angle_rad() in the Python model
function inflowAngle(rm, RmaxM) {
  const s = rm / RmaxM;
  const bump = 25.0 * Math.exp(-((s - 1) ** 2) / 0.4);
  const outward = 8.0 * (1 - Math.exp(-(Math.max(s - 1, 0) ** 2) / 1.2));
  const inward = 15.0 * (1 - Math.exp(-(Math.max(1 - s, 0) ** 2) / 0.2));
  return (bump + outward + inward) * Math.PI / 180;
}

// Holland gradient wind (m/s) at radius rm (m)
function hollandVg(rm, dpPa, B, RmaxM, f) {
  const ratio = Math.pow(RmaxM / rm, B);
  const expTerm = Math.exp(-ratio);
  const fr2 = f * rm / 2;
  return Math.sqrt((dpPa * B / PHYS.RHO) * ratio * expTerm + fr2 * fr2) - fr2;
}

// Willoughby axisymmetric wind (m/s); Vmax anchored to Holland gradient at Rmax
function willoughbyV(rm, dpPa, B, RmaxM, f, n = 0.6, m = 0.5) {
  const dpdrR = dpPa * Math.exp(-1) * (B / RmaxM);
  const frR = f * RmaxM;
  const VmaxR = 0.5 * (-frR + Math.sqrt(frR * frR + 4 * RmaxM * dpdrR / PHYS.RHO));
  const Vmax = Math.max(VmaxR, 0);
  const s = Math.max(rm / RmaxM, 1e-6);
  const Vin = Vmax * Math.pow(s, n);
  const Vout = Vmax * Math.pow(s, -m);
  const blend = 1 / (1 + Math.exp(-(rm - RmaxM) / (0.12 * RmaxM + 1)));
  return (1 - blend) * Vin + blend * Vout;
}

// Form S-6 CF 3-zone radial rule (ROA pp.184-185)
function cfEffective(rMiles, RmaxMiles, cfBase) {
  const rr = rMiles / RmaxMiles;
  let cf;
  if (rr < 1) cf = cfBase * rr;
  else if (rr < 3) cf = cfBase - (rr - 1) / 2 * 0.1;
  else cf = cfBase - 0.1;
  return Math.max(cf, 0);
}

/* Compute per-vertex peak (12-hr max) surface wind (mph) for one input vector.
   model: "holland" | "willoughby"
   rec:   { CP, Rmax(mi), VT(mph), CF, FFP, ... }
   B:     Holland shape parameter (from WSP quantile)
   pts:   grid points array (ordered like grid.json)            */
function computeLiveWind(model, rec, B, pts) {
  const dpPa = (rec.FFP - rec.CP) * 100;
  const RmaxMiles = rec.Rmax;
  const RmaxM = RmaxMiles * PHYS.MILE_M;
  const f = coriolis(PHYS.LAT0);
  const cMs = rec.VT * 0.44704;
  const th = PHYS.BEARING * Math.PI / 180;
  const cx = cMs * Math.sin(th), cy = cMs * Math.cos(th);  // due west: (-c, 0)

  const out = new Float32Array(pts.length);
  for (let i = 0; i < pts.length; i++) {
    const ew = pts[i].ew, ns = pts[i].ns;
    let peak = 0;
    const nT = Math.round(PHYS.T_MAX / PHYS.T_DT);
    for (let s = 0; s <= nT; s++) {
      const t = s * PHYS.T_DT;
      const ewc = rec.VT * t;
      const dx = ew - ewc;                 // +west of storm
      const rMiles = Math.hypot(dx, ns);
      const rm = Math.max(rMiles * PHYS.MILE_M, 1);
      const xEast = -dx, yNorth = ns;
      const phi = Math.atan2(yNorth, xEast);

      const Vg = model === "willoughby"
        ? willoughbyV(rm, dpPa, B, RmaxM, f)
        : hollandVg(rm, dpPa, B, RmaxM, f);
      const V10 = PHYS.BETA10 * Vg;
      const tin = inflowAngle(rm, RmaxM);
      const uRad = -V10 * Math.sin(tin);
      const vTan = V10 * Math.cos(tin);
      const cp = Math.cos(phi), sp = Math.sin(phi);
      const Ux = uRad * cp + vTan * (-sp) + cx;
      const Uy = uRad * sp + vTan * cp + cy;
      const spd = Math.hypot(Ux, Uy);
      const surf = spd * cfEffective(rMiles, RmaxMiles, rec.CF) * PHYS.MS_TO_MPH;
      if (surf > peak) peak = surf;
    }
    out[i] = peak;
  }
  return out;
}
