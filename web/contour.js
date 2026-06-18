/* Filled contour rendering of the windfield on the 21x40 grid lattice.
   Uses vendored d3-contour (marching squares) to build banded polygons, then
   maps grid-index coordinates -> lat/lon via bilinear interp over the lattice.
   Produces a Leaflet layerGroup styled like ROA Figs 6-8. */

let LATTICE = null;   // { width, height, ewAsc, nsAsc, pointAt[y][x] }

function buildLattice(grid) {
  const ewAsc = [...grid.ew_values].sort((a, b) => a - b);  // east(0)->west(117)
  const nsAsc = [...grid.ns_values].sort((a, b) => a - b);  // south(-15)->north(45)
  const width = ewAsc.length, height = nsAsc.length;
  const ewIdx = new Map(ewAsc.map((v, i) => [v, i]));
  const nsIdx = new Map(nsAsc.map((v, i) => [v, i]));
  const pointAt = Array.from({ length: height }, () => new Array(width));
  const order = new Int32Array(width * height);  // data index -> grid.points index
  grid.points.forEach((p, i) => {
    const x = ewIdx.get(p.ew), y = nsIdx.get(p.ns);
    pointAt[y][x] = p;
    order[y * width + x] = i;
  });
  LATTICE = { width, height, ewAsc, nsAsc, pointAt, order };
}

// fractional grid coords (x=col, y=row, d3 space) -> [lat, lon]
function gridToLatLng(x, y) {
  const { width, height, pointAt } = LATTICE;
  const x0 = Math.max(0, Math.min(width - 1, Math.floor(x)));
  const y0 = Math.max(0, Math.min(height - 1, Math.floor(y)));
  const x1 = Math.min(width - 1, x0 + 1), y1 = Math.min(height - 1, y0 + 1);
  const fx = Math.max(0, Math.min(1, x - x0)), fy = Math.max(0, Math.min(1, y - y0));
  const p00 = pointAt[y0][x0], p10 = pointAt[y0][x1];
  const p01 = pointAt[y1][x0], p11 = pointAt[y1][x1];
  const lat = (1 - fy) * ((1 - fx) * p00.lat + fx * p10.lat) +
                    fy  * ((1 - fx) * p01.lat + fx * p11.lat);
  const lon = (1 - fy) * ((1 - fx) * p00.lon + fx * p10.lon) +
                    fy  * ((1 - fx) * p01.lon + fx * p11.lon);
  return [lat, lon];
}

/* Build the filled-contour layer.
   wind: per-point array (grid.json order), thresholds + colorFn from viewer. */
function buildContourLayer(grid, wind, thresholds, colorFn) {
  if (!LATTICE) buildLattice(grid);
  const { width, height, order } = LATTICE;

  // data array in d3 order (index = y*width + x)
  const data = new Float64Array(width * height);
  for (let k = 0; k < order.length; k++) data[k] = wind[order[k]];

  const contours = window.d3.contours().size([width, height]).thresholds(thresholds)(data);

  const group = L.layerGroup();
  // draw low->high so higher bands sit on top (filled-band look)
  contours.forEach(c => {
    if (!c.coordinates.length) return;
    const col = colorFn(c.value);
    c.coordinates.forEach(poly => {            // poly = [outerRing, ...holes]
      const rings = poly.map(ring => ring.map(([x, y]) => gridToLatLng(x - 0.5, y - 0.5)));
      L.polygon(rings, {
        stroke: false, fillColor: col, fillOpacity: 0.78, interactive: false,
      }).addTo(group);
    });
  });
  return group;
}
