"""Browser smoke against a running Vite server; no live jobs or paid providers.

Install playwright, then run this file with --url http://127.0.0.1:5189.
Uses installed Edge on Windows; elsewhere install Playwright Chromium first.
"""

import argparse
import json
import os
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5189")
    args = parser.parse_args()
    job_id = "00000000-0000-0000-0000-000000000001"
    stamp = "2026-10-21T17:00:00+00:00"
    job = {
        "id": job_id, "kind": "brainrot", "status": "running", "attempts": 2, "max_attempts": 3,
        "params": {"topic": "The octopus escape"}, "created_at": stamp, "started_at": stamp,
        "finished_at": None, "run_after": stamp, "duration_seconds": 12.5,
        "current_stage": {"stage": "render"}, "error_summary": None,
    }
    detail = {"job": job, "stages": [
        {"id": "stage-1", "stage": "render", "scope": "chapter:1", "attempt": 1, "status": "failed",
         "started_at": stamp, "completed_at": stamp, "duration_seconds": 3.5, "error": "TimeoutError: renderer interrupted"},
        {"id": "stage-2", "stage": "render", "scope": "chapter:1", "attempt": 2, "status": "running",
         "started_at": stamp, "completed_at": None, "duration_seconds": None, "error": None},
    ], "publications": [
        {"id": "pub-1", "platform": "youtube", "status": "published", "scheduled_at": stamp, "published_at": stamp},
        {"id": "pub-2", "platform": "instagram", "status": "scheduled", "scheduled_at": stamp, "published_at": None},
    ]}
    failed = {**job, "id": "00000000-0000-0000-0000-000000000002", "status": "failed",
              "params": {"topic": "A failed story"}, "error": "Missing background", "current_stage": None}
    completed = {**job, "id": "00000000-0000-0000-0000-000000000003", "status": "done", "params": {"topic": "A finished story"}, "current_stage": None}
    unavailable = False
    screenshots = Path(tempfile.mkdtemp(prefix="brainrot-ui-"))
    with sync_playwright() as playwright:
        options = {"headless": True}
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if os.name == "nt" and edge.exists():
            options["executable_path"] = str(edge)
        browser = playwright.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="en-US")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def respond(route):
            if unavailable:
                route.fulfill(status=503, body="Temporary outage")
            else:
                body = detail if route.request.url.split("?")[0].endswith("/" + job_id) else [job, failed, completed]
                route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

        page.route("**/jobs*", respond)
        page.route("**/jobs/**", respond)
        page.goto(args.url)
        page.get_by_role("button", name="Workspace", exact=True).first.click()
        page.get_by_role("button", name="Queue", exact=True).click()
        expect(page.get_by_role("cell", name="The octopus escape Inspect", exact=True)).to_be_visible()
        page.get_by_role("button", name="Inspect", exact=True).first.click()
        region = page.locator("#execution-" + job_id)
        expect(region.get_by_role("heading", name="Stage history")).to_be_visible()
        expect(region.get_by_role("heading", name="Publication queue")).to_be_visible()
        expect(region.get_by_text("TimeoutError: renderer interrupted")).to_be_visible()
        page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
        job["status"] = "done"
        job.update(current_stage=None, finished_at=stamp)
        detail["stages"][1].update(status="done", duration_seconds=12.5, completed_at=stamp)
        expect(region.locator(".execution-heading .status")).to_have_text("done", timeout=10000)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "page overflows on mobile"
        page.get_by_role("button", name="Hablar español", exact=False).click()
        expect(region.get_by_role("heading", name="Historial de etapas")).to_be_visible()
        page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
        page.get_by_role("button", name="Hablar gringo", exact=False).click()
        unavailable = True
        expect(region.get_by_text("Showing the last update; connection interrupted.", exact=False)).to_be_visible(timeout=10000)
        expect(region.get_by_role("heading", name="Stage history")).to_be_visible()
        assert not errors, errors
        browser.close()
    print("Desktop/mobile execution inspector, polling and stale-data checks passed")
    print("Screenshots:", screenshots)


if __name__ == "__main__":
    main()
