"""Browser smoke against a running Vite server; no live jobs or paid providers.

Install playwright, then run this file with --url http://127.0.0.1:5189.
Uses installed Edge on Windows; elsewhere install Playwright Chromium first.
"""

import argparse
import json
import os
from pathlib import Path
import tempfile

from playwright.sync_api import Error, expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5189")
    args = parser.parse_args()
    job_id = "00000000-0000-0000-0000-000000000001"
    stamp = "2026-10-21T17:00:00+00:00"
    job = {
        "id": job_id, "kind": "brainrot", "status": "running", "attempts": 2, "max_attempts": 3,
        "params": {"topic": "The octopus escape", "llm_provider": "codex", "brainrot_level": 100}, "created_at": stamp, "started_at": stamp,
        "finished_at": None, "run_after": stamp, "duration_seconds": 12.5,
        "current_stage": {"stage": "render"}, "error_summary": "RuntimeError: raw-job-diagnostic",
    }
    detail = {"job": job, "stages": [
        {"id": "stage-1", "stage": "render", "scope": "chapter:1", "attempt": 1, "status": "failed",
         "started_at": stamp, "completed_at": stamp, "duration_seconds": 3.5, "error": "TimeoutError: renderer interrupted"},
        {"id": "stage-2", "stage": "render", "scope": "chapter:1", "attempt": 2, "status": "running",
         "started_at": stamp, "completed_at": None, "duration_seconds": None, "error": None},
    ], "publications": [
        {"id": "pub-1", "platform": "youtube", "status": "published", "scheduled_at": stamp, "published_at": stamp},
        {"id": "pub-2", "platform": "instagram", "status": "failed", "scheduled_at": stamp, "published_at": None,
         "error": "RuntimeError: raw-publication-diagnostic"},
    ]}
    failed = {**job, "id": "00000000-0000-0000-0000-000000000002", "status": "failed",
              "params": {"topic": "A failed story"}, "error": "aiohttp.WSServerHandshakeError: 403 url=wss://speech.platform.bing.com/private-diagnostic", "current_stage": None}
    completed = {**job, "id": "00000000-0000-0000-0000-000000000003", "status": "done", "params": {"topic": "A finished story"}, "current_stage": None}
    unavailable = False
    submitted = []
    deleted = set()
    delete_conflict = {"enabled": False}
    hanging = {"enabled": False}
    held_requests = []
    retried = []
    retry_conflict = {"enabled": False}
    failed_error = failed["error"]
    gallery_unavailable = {"enabled": True}
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
            if route.request.url.split("?")[0].endswith("/outputs"):
                route.fulfill(status=200, content_type="application/json", body="[]")
                return
            if route.request.url.split("?")[0].endswith("/gallery"):
                if gallery_unavailable["enabled"]:
                    route.fulfill(status=503, body="raw-storage-error")
                else:
                    route.fulfill(status=200, content_type="application/json", body="[]")
                return
            if hanging["enabled"]:
                held_requests.append(route)
                return  # Hold the request until the browser deadline aborts it.
            if route.request.method == "DELETE":
                if delete_conflict["enabled"]:
                    route.fulfill(status=409, content_type="application/json", body=json.dumps({"detail": "A video is being published."}))
                else:
                    deleted.add(route.request.url.rsplit("/", 1)[-1])
                    route.fulfill(status=204)
            elif route.request.method == "POST" and route.request.url.endswith("/retry"):
                if retry_conflict["enabled"]:
                    route.fulfill(status=409, content_type="application/json", body=json.dumps({"detail": "raw-retry-conflict"}))
                else:
                    target = job if route.request.url.endswith("/" + job_id + "/retry") else failed
                    retried.append(target["id"])
                    target.update(status="pending", error=None, error_summary=None)
                    route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": target["id"], "status": "pending"}))
            elif route.request.method == "POST":
                submitted.append(route.request.post_data_json)
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": job_id}))
            elif unavailable:
                route.fulfill(status=503, body="Temporary outage")
            else:
                body = detail if route.request.url.split("?")[0].endswith("/" + job_id) else [row for row in [job, failed, completed] if row["id"] not in deleted]
                route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

        page.route("**/jobs*", respond)
        page.route("**/jobs/**", respond)
        page.route("**/gallery*", respond)
        page.route("**/youtube/status", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps({"connected": True, "channel_title": "Test channel", "channel_id": "channel"})))
        page.goto(args.url)
        page.get_by_role("button", name="Workspace", exact=True).first.click()
        page.locator(".choice").filter(has_text="From a topic").click()
        model = page.get_by_role("combobox", name="Model", exact=True)
        expect(model).to_have_value("codex")
        model.focus()
        model.press("ArrowUp")
        expect(model).to_have_value("claude-code")
        model.press("ArrowDown")
        expect(model).to_have_value("codex")
        intensity = page.get_by_role("slider", name="Brainrot level", exact=True)
        expect(intensity).to_have_value("1")
        expect(intensity).to_have_attribute("max", "4")
        expect(intensity).to_have_attribute("step", "1")
        expect(intensity).to_have_attribute("aria-valuetext", "Playful")
        expect(page.locator(".brainrot-stop")).to_have_count(5)
        intensity.press("Home")
        expect(intensity).to_have_value("0")
        expect(intensity).to_have_attribute("aria-valuetext", "Grounded")
        expect(page.locator("#brainrot-description")).to_have_text("No internet slang. Clear, straightforward storytelling.")
        for index, name in enumerate(["Playful", "Chaotic", "Unhinged", "Max brainrot"], start=1):
            intensity.press("ArrowRight")
            expect(intensity).to_have_value(str(index))
            expect(intensity).to_have_attribute("aria-valuetext", name)
        intensity.press("End")
        expect(intensity).to_have_value("4")
        expect(intensity).to_have_attribute("aria-valuetext", "Max brainrot")
        expect(page.locator("#brainrot-description")).to_have_text("Internet slang throughout. Real topics stay factual; invented premises get wildly absurd.")
        page.get_by_label("Topic", exact=True).fill("The octopus escape")
        page.screenshot(path=str(screenshots / "model-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="Hablar español", exact=False).click()
        expect(page.get_by_role("combobox", name="Modelo", exact=True)).to_have_value("codex")
        expect(page.get_by_role("slider", name="Nivel de brainrot", exact=True)).to_have_value("4")
        expect(page.locator("#brainrot-description")).to_contain_text("Jerga de internet por todos lados.")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "model form overflows on mobile"
        page.screenshot(path=str(screenshots / "model-mobile.png"), full_page=True)
        page.get_by_role("button", name="Hablar gringo", exact=False).click()
        page.set_viewport_size({"width": 1440, "height": 1000})
        expect(page.get_by_role("combobox", name="When the video is ready", exact=True)).to_have_value("review")
        page.get_by_role("combobox", name="When the video is ready", exact=True).select_option("auto")
        page.get_by_role("combobox", name="YouTube visibility", exact=True).select_option("unlisted")
        page.get_by_label("Contains realistic altered or synthetic content", exact=False).check()
        page.get_by_role("button", name="Review →", exact=True).click()
        expect(page.locator(".review").get_by_text("Chat GPT", exact=True)).to_be_visible()
        expect(page.locator(".review").get_by_text("Max brainrot", exact=True)).to_be_visible()
        page.get_by_role("button", name="← Edit", exact=True).click()
        expect(page.get_by_role("combobox", name="Model", exact=True)).to_have_value("codex")
        expect(page.get_by_role("slider", name="Brainrot level", exact=True)).to_have_value("4")
        page.get_by_role("button", name="Review →", exact=True).click()
        page.get_by_role("button", name="Queue it", exact=True).click()
        expect(page.get_by_role("heading", name="Live queue", exact=True)).to_be_visible()
        assert submitted == [{"kind": "brainrot", "topic": "The octopus escape", "llm_provider": "codex", "brainrot_level": 100,
                              "youtube_publishing": {"mode": "auto", "privacy_status": "unlisted", "made_for_kids": False, "contains_synthetic_media": True}}]
        page.get_by_role("button", name="New job", exact=True).click()
        page.locator(".choice").filter(has_text="From a YouTube link").click()
        page.get_by_label("Source URL", exact=True).fill("https://youtube.com/watch?v=example")
        assert page.get_by_role("slider").count() == 0, "repurposing does not rewrite the source script"
        expect(page.get_by_role("combobox", name="Model", exact=True)).to_have_value("codex")
        page.get_by_role("button", name="Review →", exact=True).click()
        expect(page.locator(".review").get_by_text("Chat GPT", exact=True)).to_be_visible()
        page.get_by_role("button", name="Queue it", exact=True).click()
        expect(page.get_by_role("heading", name="Live queue", exact=True)).to_be_visible()
        assert submitted[1] == {"kind": "repurpose", "youtube_url": "https://youtube.com/watch?v=example", "llm_provider": "codex",
                                "youtube_publishing": {"mode": "review", "privacy_status": "private", "made_for_kids": False, "contains_synthetic_media": False}}
        expect(page.get_by_role("row").filter(has_text="The octopus escape")).to_be_visible()
        running_row = page.get_by_role("row").filter(has_text="The octopus escape")
        running_row.get_by_role("button", name="Delete", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("heading", name="Delete running job?", exact=True)).to_be_visible()
        expect(dialog.get_by_text("Permanently delete this job, its history and all output files? This cannot be undone.", exact=True)).to_be_visible()
        dialog.press("Escape")
        expect(dialog).not_to_be_visible()
        assert not deleted, "cancel must not delete the job"
        failed_row = page.get_by_role("row").filter(has_text="A failed story")
        expect(failed_row.get_by_text("Narration couldn’t be generated. Please try again later.", exact=True)).to_be_visible()
        assert "WSServerHandshakeError" not in page.locator("body").inner_text()
        assert "speech.platform.bing.com" not in page.locator("body").inner_text()
        tops = failed_row.locator(".job-actions button").evaluate_all("buttons => buttons.map(b => b.getBoundingClientRect().top)")
        assert len(tops) == 3 and max(tops) - min(tops) < 1, "queue actions must share one row"
        assert running_row.get_by_role("button", name="Retry", exact=True).count() == 0
        retry_conflict["enabled"] = True
        failed_row.get_by_role("button", name="Retry", exact=True).click()
        expect(page.get_by_role("alert")).to_have_text("This job can’t be retried right now. Check its latest status.")
        assert "raw-retry-conflict" not in page.locator("body").inner_text()
        retry_conflict["enabled"] = False
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="Hablar español", exact=False).click()
        tops = failed_row.locator(".job-actions button").evaluate_all("buttons => buttons.map(b => b.getBoundingClientRect().top)")
        assert max(tops) - min(tops) < 1, "mobile actions must stay side by side"
        failed_row.get_by_role("button", name="Reintentar", exact=True).click()
        expect(failed_row.locator(".status")).to_have_text("pending", timeout=10000)
        expect(page.get_by_text("Encolado de nuevo. Se reutilizará el progreso guardado.", exact=True)).to_be_visible()
        assert retried == [failed["id"]] and len(submitted) == 2, "retry must reuse the job rather than submit another"
        assert failed_row.get_by_role("button", name="Reintentar", exact=True).count() == 0
        failed.update(status="failed", error=failed_error)
        page.get_by_role("button", name="Hablar gringo", exact=False).click()
        page.set_viewport_size({"width": 1440, "height": 1000})
        expect(failed_row.get_by_role("button", name="Retry", exact=True)).to_be_visible(timeout=10000)
        failed_row.get_by_role("button", name="Delete", exact=True).click()
        dialog.get_by_role("button", name="Confirm delete", exact=True).click()
        expect(failed_row).not_to_be_visible()
        delete_conflict["enabled"] = True
        page.get_by_role("row").filter(has_text="A finished story").get_by_role("button", name="Delete", exact=True).click()
        dialog.get_by_role("button", name="Confirm delete", exact=True).click()
        expect(dialog.get_by_role("alert")).to_have_text("This video is still being published. Please wait before deleting it.")
        dialog.get_by_role("button", name="Cancel", exact=True).click()
        delete_conflict["enabled"] = False
        page.get_by_role("button", name="Inspect", exact=True).first.click()
        region = page.locator("#execution-" + job_id)
        expect(region.get_by_role("heading", name="Current stages")).to_be_visible()
        stage_table = region.get_by_role("table", name="Current stages", exact=True)
        expect(stage_table.locator("tbody tr")).to_have_count(1)
        expect(stage_table.locator("tbody tr td").nth(1)).to_have_text("2")
        expect(region.get_by_role("heading", name="Publication queue")).to_be_visible()
        expect(region.get_by_text("Chat GPT", exact=True)).to_be_visible()
        expect(region.get_by_text("Max brainrot", exact=True)).to_be_visible()
        expect(region.get_by_text("This took longer than expected. Please try again.", exact=True)).not_to_be_visible()
        expect(region.get_by_text("The video couldn’t be published. Check the connected account before trying again.", exact=True)).to_be_visible()
        visible = page.locator("body").inner_text()
        for diagnostic in ("TimeoutError", "renderer interrupted", "raw-job-diagnostic", "raw-publication-diagnostic"):
            assert diagnostic not in visible, f"technical diagnostic leaked into UI: {diagnostic}"
        page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
        job["status"] = "failed"
        expect(running_row.get_by_role("button", name="Retry", exact=True)).to_be_visible(timeout=10000)
        running_row.get_by_role("button", name="Retry", exact=True).click()
        expect(region.get_by_text("Stages will appear when this attempt starts.", exact=True)).to_be_visible(timeout=10000)
        expect(stage_table).not_to_be_visible()
        assert len(detail["stages"]) == 2, "prior diagnostics must be retained"
        job.update(status="running", attempts=3)
        active_stage = {"id": "stage-3", "stage": "render", "scope": "chapter:1", "attempt": 3, "status": "running",
                        "started_at": stamp, "completed_at": None, "duration_seconds": None, "error": None}
        detail["stages"].append(active_stage)
        expect(stage_table.locator("tbody tr")).to_have_count(1, timeout=10000)
        expect(stage_table.locator("tbody tr td").nth(1)).to_have_text("3")
        job["status"] = "done"
        job.update(current_stage=None, finished_at=stamp)
        active_stage.update(status="done", duration_seconds=12.5, completed_at=stamp)
        expect(region.locator(".execution-heading .status")).to_have_text("done", timeout=10000)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "page overflows on mobile"
        page.get_by_role("button", name="Hablar español", exact=False).click()
        expect(region.get_by_role("heading", name="Etapas actuales")).to_be_visible()
        expect(region.get_by_role("table", name="Etapas actuales", exact=True).locator("tbody tr")).to_have_count(1)
        expect(region.get_by_text("Esto tardó más de lo esperado. Inténtalo de nuevo.", exact=True)).not_to_be_visible()
        running_row.get_by_role("button", name="Eliminar", exact=True).click()
        expect(dialog.get_by_role("button", name="Confirmar eliminación", exact=True)).to_be_visible()
        assert page.evaluate("document.querySelector('dialog').getBoundingClientRect().width <= innerWidth"), "dialog overflows on mobile"
        dialog.get_by_role("button", name="Cancelar", exact=True).click()
        page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
        page.get_by_role("button", name="Hablar gringo", exact=False).click()
        unavailable = True
        expect(region.get_by_text("Showing the last update; connection interrupted.", exact=False)).to_be_visible(timeout=10000)
        expect(region.get_by_role("heading", name="Current stages")).to_be_visible()
        assert "Temporary outage" not in page.locator("body").inner_text()
        unavailable = False
        expect(region.get_by_text("Showing the last update; connection interrupted.", exact=False)).not_to_be_visible(timeout=10000)
        hanging["enabled"] = True
        expect(region.get_by_text("Showing the last update; connection interrupted.", exact=False)).to_be_visible(timeout=22000)
        expect(region.get_by_role("heading", name="Current stages")).to_be_visible()
        hanging["enabled"] = False
        for route in held_requests:
            try:
                route.abort()
            except Error:
                pass  # The browser may have already discarded an aborted request.
        held_requests.clear()
        expect(region.get_by_text("Showing the last update; connection interrupted.", exact=False)).not_to_be_visible(timeout=10000)
        page.get_by_role("button", name="Output", exact=True).click()
        expect(page.get_by_text("Connection interrupted", exact=True)).to_be_visible()
        assert "raw-storage-error" not in page.locator("body").inner_text()
        gallery_unavailable["enabled"] = False
        expect(page.get_by_text("Nothing rendered", exact=True)).to_be_visible(timeout=10000)
        assert not errors, errors
        browser.close()
    print("Desktop/mobile model selection, deletion dialogs/cancellation/conflicts, execution inspector, polling and stale-data checks passed")
    print("Screenshots:", screenshots)


if __name__ == "__main__":
    main()
