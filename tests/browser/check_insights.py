"""Insights browser check against the running local frontend and API.

Uses the frontend's configured dashboard login. No jobs, model calls, publication,
or database writes. Run with python tests/browser/check_insights.py.
"""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5173")
    args = parser.parse_args()
    csv = "seconds,retention\n0,100\n15,92\n30,80\n60,74\n90,60"
    srt = "1\n00:00:00,000 --> 00:00:30,000\nThe opening promise.\n\n2\n00:00:30,000 --> 00:01:30,000\nThe payoff."
    screenshots = Path("out/dev-services")
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        options = {"headless": True}
        if edge.exists():
            options["executable_path"] = str(edge)
        browser = playwright.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="en-US")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/jobs", lambda route: route.fulfill(status=200, content_type="application/json", body="[]"))
        page.goto(args.url)
        page.get_by_role("button", name="Workspace", exact=True).first.click()
        page.get_by_role("button", name="Insights", exact=True).click()
        page.get_by_label("Retention CSV").set_input_files({"name": "retention.csv", "mimeType": "text/csv", "buffer": csv.encode()})
        page.get_by_label("Video duration in seconds").fill("90")
        page.get_by_label("Video position units", exact=True).select_option("seconds")
        page.get_by_label("Audience retention units", exact=True).select_option("percent")
        page.get_by_label("Timed subtitles").set_input_files({"name": "captions.srt", "mimeType": "text/plain", "buffer": srt.encode()})
        page.get_by_role("button", name="Analyze retention", exact=True).click()
        expect(page.get_by_role("heading", name="Largest observed drops")).to_be_visible()
        expect(page.locator(".retention-facts")).to_contain_text("-20 pp")
        expect(page.locator("tbody")).to_contain_text("The opening promise.")
        slider = page.get_by_role("slider", name="Audience retention over time")
        slider.press("End")
        expect(slider).to_have_attribute("aria-valuetext", "90s, 60%")
        with page.expect_download() as download:
            page.get_by_role("button", name="Download report", exact=True).click()
        assert download.value.suggested_filename == "brainrot-retention-report.json"
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(screenshots / "insights-desktop.png"), full_page=True)
        page.get_by_role("button", name="Queue", exact=True).click()
        page.get_by_role("button", name="Insights", exact=True).click()
        expect(page.get_by_role("heading", name="Largest observed drops")).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("button", name="Edit import", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(screenshots / "insights-mobile.png"), full_page=True)
        page.locator(".lang-btn").click()
        expect(page.get_by_role("heading", name="Mayores caídas observadas")).to_be_visible()
        expect(page.get_by_role("button", name="Descargar informe", exact=True)).to_be_visible()
        page.locator(".lang-btn").click()
        page.get_by_role("button", name="Edit import", exact=True).click()
        page.get_by_label("Retention CSV").set_input_files({"name": "invalid.csv", "mimeType": "text/csv", "buffer": b"0,100\n30,80\n30,60"})
        expect(page.get_by_text("invalid.csv", exact=True)).to_be_visible()
        page.get_by_role("button", name="Analyze retention", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("without duplicate timestamps")
        assert not errors, errors
        browser.close()
    print("Insights: live authenticated API, CSV/SRT import, report, curve, export, tab persistence, mobile, Spanish, validation passed.")


if __name__ == "__main__":
    main()
