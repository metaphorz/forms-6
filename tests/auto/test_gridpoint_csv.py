"""Verify the CSV button was removed and right-click grid-point CSV works.

Loads the viewer, waits for grid+inputs+vuln to load, then:
  - asserts #btnCsv is gone
  - captures the Blob produced by downloadGridPointCsv() for a land point
  - asserts 8 columns, 100 data rows, and a plausible header
"""
import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = "http://localhost:8012/web/index.html"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--window-size=1400,1000")
driver = webdriver.Chrome(options=opts)

try:
    driver.get(URL)

    # Wait for app init: grid, inputs and vulnerability curve all loaded.
    ready = False
    for _ in range(40):
        time.sleep(0.5)
        ready = driver.execute_script(
            "return (typeof state !== 'undefined') && !!(state.grid && state.inputs && state.vuln);"
        )
        if ready:
            break
    assert ready, "app did not finish loading grid/inputs/vuln"

    # 1) The CSV button must be gone.
    btn = driver.execute_script("return document.getElementById('btnCsv');")
    assert btn is None, "btnCsv still present"

    # 2) Capture the CSV for the first land grid point via right-click handler.
    csv_text = driver.execute_script(
        """
        // find a land point index
        var idx = state.grid.points.findIndex(p => p.land);
        // intercept the blob download
        var captured = null;
        var origCreate = URL.createObjectURL;
        var origRevoke = URL.revokeObjectURL;
        var clickProto = HTMLAnchorElement.prototype.click;
        return new Promise(resolve => {
          URL.createObjectURL = function(blob){
            blob.text().then(t => { captured = t; });
            return 'blob:stub';
          };
          URL.revokeObjectURL = function(){};
          HTMLAnchorElement.prototype.click = function(){};   // no real download
          downloadGridPointCsv(idx);
          // blob.text() is async; poll for it
          var tries = 0;
          var iv = setInterval(() => {
            if (captured !== null || tries++ > 40) {
              clearInterval(iv);
              URL.createObjectURL = origCreate;
              URL.revokeObjectURL = origRevoke;
              HTMLAnchorElement.prototype.click = clickProto;
              resolve(captured);
            }
          }, 50);
        });
        """
    )
    assert csv_text, "no CSV captured"

    lines = [l for l in csv_text.strip().split("\n") if l]
    header = lines[0].split(",")
    print("header:", header)
    assert header == ["CP", "Rmax", "VT", "WSP", "CF", "FFP",
                      "MaxWind_mph", "%LC", "%TLC"], header
    data = lines[1:]
    assert len(data) == 100, f"expected 100 data rows, got {len(data)}"
    for row in data:
        cells = row.split(",")
        assert len(cells) == 9, f"row has {len(cells)} cols: {row}"
    print("sample row 1:", data[0])
    print("sample row 100:", data[-1])

    # 3) No JS console errors.
    errors = [e for e in driver.get_log("browser")
              if e["level"] == "SEVERE" and "favicon.ico" not in e["message"]]
    assert not errors, f"console errors: {errors}"

    print("PASS: button removed, 9x100 CSV generated, no console errors.")
finally:
    driver.quit()
