"""Project integration UI smoke with simulated external accounts; never uploads."""
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    connected = False
    saved = False
    active = False
    submitted = []
    uploads = []
    settings_submitted = []
    asset = {"id": "asset-one", "provider": "nasa", "title": "Moon footage", "credit": "NASA", "source_url": "https://images.nasa.gov/details/asset-one", "license_url": "https://www.nasa.gov", "storage_path": "backgrounds/nasa-asset-one.mp4", "url": "data:video/mp4;base64,", "duration_seconds": 20}
    report = {"duration_seconds": 120, "points": [{"seconds": 1.2, "retention": 100}, {"seconds": 30, "retention": 80}, {"seconds": 120, "retention": 60}],
              "opening_seconds": 30, "opening_start_seconds": 1.2, "opening_loss_pp": 20, "last_observed_seconds": 120, "last_observed_retention": 60, "drops": []}
    with sync_playwright() as playwright:
        options = {"headless": True}
        edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if edge.exists():
            options["executable_path"] = str(edge)
        browser = playwright.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="en-US")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        def respond(route):
            nonlocal connected, saved, active, uploads
            path = route.request.url.split(":8001")[-1]
            if path.startswith("/research/search"):
                result = [{"id": "Q2277", "label": "Roman Empire", "description": "Historical state"}]
            elif path == "/research/Q2277":
                result = {"id": "Q2277", "label": "Roman Empire", "description": "Historical state", "url": "https://www.wikidata.org/wiki/Q2277", "facts": []}
            elif path.startswith("/library/search"):
                result = [asset]
            elif path == "/library/nasa/asset-one/activate":
                active = True; result = asset
            elif path == "/library/nasa/asset-one":
                saved = True; result = asset
            elif path == "/library":
                result = [{**asset, "active": active}] if saved else []
            elif path == "/youtube/status":
                result = {"configured": False, "connected": connected, "channel_title": "Test channel", "redirect_uri": "http://127.0.0.1:8001/youtube/callback"}
            elif path == "/youtube/uploads":
                result = uploads
            elif path == "/youtube/performance":
                result = [{"id": "publication-one", "title": "Test Short", "url": "https://youtube.com/shorts/abcdefghijk", "metrics": {"views": 42, "engagedViews": 30, "averageViewPercentage": 65, "likes": 4, "comments": 1}}]
            elif path == "/youtube/sync":
                result = {"updated": 1, "waiting": 0, "failed": 0}
            elif path == "/youtube/settings":
                settings_submitted.append(route.request.post_data_json)
                result = {"connected": True}
            elif path == "/youtube/metadata":
                result = {"title": "The Moon Has a Loading Screen", "description": "A fictional lunar story. #Moon #Shorts", "tags": ["moon", "space story", "shorts"]}
            elif path == "/youtube/upload":
                submitted.append(route.request.post_data_json)
                uploads = [{"id": "publication-one", "title": submitted[-1]["title"], "status": "published", "url": "https://www.youtube.com/shorts/abcdefghijk"}]
                result = {"id": "publication-one", "status": "uploading"}
            elif path == "/youtube/videos":
                result = [{"id": "abcdefghijk", "title": "Test Short"}]
            elif path.startswith("/youtube/retention/"):
                result = report
            elif path.startswith("/gallery"):
                result = [{"id": "00000000-0000-0000-0000-000000000001", "source": "chapter", "title": "A portable video", "url": "data:video/mp4;base64,"}]
            elif path == "/jobs" and route.request.method == "POST":
                submitted.append(route.request.post_data_json); result = {"id": "job-one"}
            elif path.startswith("/jobs"):
                result = []
            else:
                raise AssertionError("Unexpected API request: " + path)
            route.fulfill(status=200, content_type="application/json", body=json.dumps(result))
        page.route("http://127.0.0.1:8001/**", respond)
        page.goto("http://localhost:5173")
        page.get_by_role("button", name="Workspace", exact=True).first.click()
        page.get_by_text("Tools", exact=True).click()
        page.get_by_role("button", name="Research", exact=True).click()
        page.get_by_label("Search topic").fill("Roman Empire")
        page.get_by_role("button", name="Search", exact=True).click()
        page.get_by_role("button", name="Roman Empire", exact=False).click()
        page.get_by_role("button", name="Use for a new story", exact=True).click()
        expect(page.get_by_role("link", name="Roman Empire", exact=True)).to_be_visible()
        page.get_by_text("Tools", exact=True).click()
        page.get_by_role("button", name="Media library", exact=True).click()
        page.get_by_label("Search topic").fill("moon")
        page.get_by_role("button", name="Search", exact=True).click()
        page.get_by_role("button", name="Save locally", exact=True).click()
        page.get_by_role("button", name="Add to rotation", exact=True).click()
        expect(page.get_by_role("button", name="In rotation", exact=True)).to_be_disabled()
        page.get_by_role("button", name="YouTube", exact=True).click()
        expect(page.get_by_role("button", name="Connect YouTube", exact=True)).to_be_disabled()
        expect(page.get_by_text("http://127.0.0.1:8001/youtube/callback", exact=True)).to_be_visible()
        screenshots = Path("out/dev-services"); screenshots.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshots / "youtube-setup.png"), full_page=True)
        connected = True
        page.get_by_role("button", name="Refresh status", exact=True).click()
        page.get_by_text("Automatic uploads", exact=True).click()
        page.get_by_label("Enable automatic YouTube uploads", exact=True).check()
        page.get_by_label("Automatic upload visibility", exact=True).select_option("unlisted")
        page.get_by_role("button", name="Save upload settings", exact=True).click()
        expect(page.get_by_text("Upload settings saved.", exact=True)).to_be_visible()
        assert settings_submitted == [{"auto_publish": True, "privacy_status": "unlisted", "include_queued": False}]
        page.get_by_role("button", name="Continue", exact=True).click()
        expect(page.get_by_label("YouTube title")).to_have_value("The Moon Has a Loading Screen")
        expect(page.get_by_role("textbox", name="Description", exact=True)).to_have_value("A fictional lunar story. #Moon #Shorts")
        page.get_by_label("YouTube title").fill("Earth Is Downloadable Content")
        expect(page.get_by_label("Visibility", exact=True)).to_have_value("private")
        page.get_by_role("textbox", name="Description", exact=True).fill("A fictional story.")
        page.get_by_role("button", name="Review upload", exact=True).click()
        page.get_by_role("button", name="Upload to YouTube", exact=True).click()
        expect(page.get_by_text("Upload started.", exact=False)).to_be_visible()
        assert submitted[-1]["privacy_status"] == "private" and submitted[-1]["title"] == "Earth Is Downloadable Content"
        assert len(submitted) == 1
        page.get_by_role("button", name="Load channel videos", exact=True).click()
        page.get_by_role("button", name="Sync video performance", exact=True).click()
        expect(page.get_by_role("cell", name="65.0%", exact=True)).to_be_visible()
        page.get_by_role("button", name="Open retention in Output", exact=True).click()
        expect(page.get_by_text("YouTube · Test Short", exact=True)).to_be_visible()
        expect(page.locator(".retention-facts")).to_contain_text("1.2–30s")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.locator(".lang-btn").click()
        page.get_by_role("button", name="YouTube", exact=True).click()
        expect(page.get_by_text("Canal conectado: Test channel", exact=True)).to_be_visible()
        assert not errors, errors
        browser.close()
    print("Integration UI passed: references, media import/activation, Google setup, reviewed private upload, channel retention, mobile, Spanish. External writes were simulated.")


if __name__ == "__main__":
    main()
