"""Shared Output/Queue inspector and per-video analytics; all API data simulated."""
import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


def main():
    job_id = "00000000-0000-0000-0000-000000000001"
    asset = {"id": "chapter-one", "source": "chapter", "job_id": job_id, "title": "The silver crisis", "url": "data:video/mp4;base64,", "created_at": "2026-10-22T12:00:00Z",
        "narration": "The silver coins changed.", "publications": [{"id": "publication", "platform": "youtube", "status": "published", "video_id": "abcdefghijk", "url": "https://youtube.com/shorts/abcdefghijk",
        "metadata": {"title": "Where Did Rome's Silver Go?", "description": "A history short. #Shorts", "tags": ["Rome"], "privacy_status": "private"}, "analytics": {"views": 42, "engagedViews": 30, "averageViewPercentage": 65}}]}
    job = {"id": job_id, "kind": "brainrot", "status": "done", "params": {"topic": "Roman silver", "llm_provider": "codex"}, "attempts": 1, "max_attempts": 3, "created_at": "2026-10-22T12:00:00Z"}
    report = {"duration_seconds": 120, "points": [{"seconds": 1.2, "retention": 100}, {"seconds": 30, "retention": 80}, {"seconds": 120, "retention": 60}], "opening_seconds": 30, "opening_start_seconds": 1.2, "opening_loss_pp": 20, "last_observed_seconds": 120, "last_observed_retention": 60, "drops": []}
    with sync_playwright() as p:
        options = {"headless": True}
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if edge.exists(): options["executable_path"] = str(edge)
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="en-US")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        def respond(route):
            path = route.request.url.split(":8001")[-1]
            if path == "/gallery": data = [asset]
            elif path.endswith("/outputs"): data = [asset]
            elif path == "/jobs": data = [job]
            elif path == "/jobs/" + job_id: data = {"job": job, "stages": [], "publications": []}
            elif path.startswith("/youtube/retention/"): data = report
            elif path == "/youtube/status": data = {"connected": True, "channel_title": "Test channel"}
            else: raise AssertionError(path)
            route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
        page.route("http://127.0.0.1:8001/**", respond)
        page.goto("http://localhost:5173")
        page.get_by_role("button", name="Workspace", exact=True).first.click()
        expect(page.get_by_role("button", name="Insights", exact=True)).to_have_count(0)
        page.get_by_role("button", name="Output", exact=True).click()
        page.get_by_role("button", name="Inspect: The silver crisis", exact=True).click()
        details = page.get_by_role("region", name="Video details", exact=True)
        expect(details.get_by_text("Where Did Rome's Silver Go?", exact=True)).to_be_visible()
        expect(details.get_by_text("65.0%", exact=True)).to_be_visible()
        details.get_by_text("Script / transcript", exact=True).click()
        expect(details.get_by_text("The silver coins changed.", exact=True)).to_be_visible()
        details.get_by_role("button", name="Load YouTube retention", exact=True).click()
        expect(details.get_by_role("heading", name="Largest observed drops")).to_be_visible()
        page.get_by_role("button", name="Queue", exact=True).click()
        page.get_by_role("button", name="Inspect", exact=True).click()
        expect(page.get_by_role("region", name="Video details").get_by_role("heading", name="Largest observed drops")).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator(".lang-btn").click()
        expect(page.get_by_role("region", name="Detalles del video")).to_be_visible()
        assert not errors, errors
        browser.close()
    print("Video details passed: clickable output, shared Queue inspector, metadata, performance, transcript, retention, session continuity, mobile, Spanish.")


if __name__ == "__main__": main()
