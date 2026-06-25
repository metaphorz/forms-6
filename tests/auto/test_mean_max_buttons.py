#!/usr/bin/env python3
"""Selenium test: Mean / Max aggregation buttons under the Input-vector slider.

Verifies:
  1. Both buttons render under the slider.
  2. Mean is the default view: active (green), slider disabled, status "mean (100 vectors)".
  3. Max is mutually exclusive with Mean; status reads "max (100 vectors)" and the
     per-point peak (worst-case envelope) is >= the mean view's peak.
  4. Toggling the active button off re-enables the slider (single-vector view).
  5. The live-model (Holland) max path computes 100 fields in the browser.
  6. No severe console errors.

Run:  source venv/bin/activate && python tests/auto/test_mean_max_buttons.py
"""
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://localhost:8012/web/index.html"


def main():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")
    d = webdriver.Chrome(options=opts)
    failures = []
    try:
        d.get(URL)
        wait = WebDriverWait(d, 30)
        wait.until(lambda x: x.execute_script(
            "return (typeof state!=='undefined') && !!(state.grid && state.powell);"))
        time.sleep(1.0)

        def active(bid):
            return "active" in (d.find_element(By.ID, bid).get_attribute("class") or "")

        def disabled():
            return bool(d.find_element(By.ID, "vector").get_attribute("disabled"))

        def status():
            return d.find_element(By.ID, "info").text.replace("\n", " | ")

        def peak():
            return d.execute_script(
                "const w=state.wind;let mx=0;for(let i=0;i<w.length;i++)"
                "if(w[i]>mx)mx=w[i];return +mx.toFixed(1);")

        # 1 + 2: buttons present, Mean is the default
        assert d.find_element(By.ID, "btnMean").text.strip() == "Mean"
        assert d.find_element(By.ID, "btnMax").text.strip() == "Max"
        if not (active("btnMean") and not active("btnMax")):
            failures.append("default should have Mean active, Max off")
        if not disabled():
            failures.append("slider should be disabled in the default Mean view")
        if "mean (100 vectors)" not in status():
            failures.append(f"default status lacks mean tag: {status()!r}")
        mean_peak = peak()
        print("default:", status(), "peak", mean_peak)

        # 3: Max is exclusive with Mean; envelope peak >= mean peak
        d.find_element(By.ID, "btnMax").click()
        wait.until(lambda x: "max (100 vectors)" in x.find_element(By.ID, "info").text)
        if not (active("btnMax") and not active("btnMean")):
            failures.append("after Max: Max should be active, Mean off")
        max_peak = peak()
        print("max view:", status(), "peak", max_peak)
        if max_peak < mean_peak:
            failures.append(f"max peak {max_peak} < mean peak {mean_peak}")

        # back to Mean, then toggle Mean off -> single vector, slider enabled
        d.find_element(By.ID, "btnMean").click()
        wait.until(lambda x: "mean (100 vectors)" in x.find_element(By.ID, "info").text)
        if not (active("btnMean") and not active("btnMax")):
            failures.append("after Mean: Mean active, Max off")
        d.find_element(By.ID, "btnMean").click()
        wait.until(lambda x: "(100 vectors)" not in x.find_element(By.ID, "info").text)
        if active("btnMean") or active("btnMax") or disabled():
            failures.append("toggling Mean off should clear both + enable slider")
        print("single-vector:", status())

        # 5: live-model (Holland) Max path
        Select(d.find_element(By.ID, "model")).select_by_value("holland")
        time.sleep(0.5)
        d.find_element(By.ID, "btnMax").click()
        wait.until(lambda x: "max (100 vectors)" in x.find_element(By.ID, "info").text)
        if "Peak wind" not in status():
            failures.append(f"Holland max produced no wind stats: {status()!r}")
        print("Holland max:", status())

        errors = [e for e in d.get_log("browser")
                  if e["level"] == "SEVERE" and "favicon.ico" not in e["message"]]
        if errors:
            failures.append(f"console errors: {errors}")
    finally:
        d.quit()

    if failures:
        print("FAIL:\n  - " + "\n  - ".join(failures))
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
