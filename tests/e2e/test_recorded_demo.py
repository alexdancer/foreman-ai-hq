from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

from foreman_ai_hq import db, task_launch

from tests.e2e.recorded_demo import (
    DEMO_MODEL,
    DEMO_SENTINEL,
    DEMO_SESSION_ID,
    RecordedDemo,
)


def test_recorded_demo_health() -> None:
    with RecordedDemo() as demo:
        response = httpx.get(f"{demo.base_url}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_recorded_demo_stream_service(request: pytest.FixtureRequest) -> None:
    with RecordedDemo() as demo:
        result = task_launch.launch_task(
            demo.database_path,
            demo.task_id,
            adapter_id=None,
            model=None,
            proxy_url=task_launch.DEFAULT_PROXY_URL,
            project_id=demo.project_id,
        )
        assert result.task["status"] == "Running"

        assert demo.entered.wait(timeout=15)

        events = db.list_worker_run_events(
            demo.database_path,
            session_id=result.session["id"],
            limit=50,
        )
        kinds = [e["kind"] for e in events]
        assert "agent_message" in kinds
        # The provisional usage line is still gated, so no token event exists yet.
        assert "token" not in kinds

        demo.stream_more.set()
        assert demo.provisional_emitted.wait(timeout=15)

        events = db.list_worker_run_events(
            demo.database_path,
            session_id=result.session["id"],
            limit=50,
        )
        assert "token" in [e["kind"] for e in events]

        demo.release.set()
        assert demo.outcome_done.wait(timeout=30)

        task = db.get_task(demo.database_path, demo.task_id)
        assert task["status"] == "Review"
        assert task["actual_tokens"] == 15

        artifact = db.build_session_artifact(demo.database_path, result.session["id"])
        worker_kinds = [e["kind"] for e in artifact["worker_run_events"]]
        # Claude maps both the provisional and the final `result` line to token
        # events, so the ordered shape is message -> provisional -> final.
        idx_agent = worker_kinds.index("agent_message")
        idx_provisional = worker_kinds.index("token", idx_agent)
        idx_final = worker_kinds.index("token", idx_provisional + 1)
        assert idx_agent < idx_provisional < idx_final

        token_turns = [t for t in artifact["token_log"] if t["usage_kind"] == "task_execution"]
        assert len(token_turns) == 1
        assert token_turns[0]["total_tokens"] == 15
        # Provenance, not just the count: the authoritative total must come from
        # the session-bound completion event, never the unbound provisional line.
        source = token_turns[0]["raw_usage"]["source"]
        assert source["type"] == "result"
        assert source["session_id"] == DEMO_SESSION_ID
        assert token_turns[0]["raw_usage"]["model"] == DEMO_MODEL


def test_recorded_demo_browser(request: pytest.FixtureRequest) -> None:
    results_dir = Path("test-results") / request.node.name
    results_dir.mkdir(parents=True, exist_ok=True)
    trace_path = results_dir / "trace.zip"
    screenshot_path = results_dir / "failure.png"

    with RecordedDemo() as demo:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            try:
                page.goto(f"{demo.base_url}/login")
                page.locator('input[name="token"]').fill(demo.portal_token)
                page.locator('button[type="submit"]').click()
                page.wait_for_url("**/dashboard", timeout=15000)

                page.goto(
                    f"{demo.base_url}/projects/{demo.project_id}",
                    wait_until="networkidle",
                )
                page.locator("h1.page-title").wait_for(timeout=30000)

                # Drive intake through the sole public task-creation surface.
                intake = page.get_by_placeholder("Describe the task or goal…")
                expect(intake).to_be_visible()
                input_layout = intake.evaluate(
                    """element => {
                        const control = element.getBoundingClientRect();
                        const track = element.parentElement.getBoundingClientRect();
                        const style = getComputedStyle(element);
                        return {
                            controlLeft: control.left,
                            controlRight: control.right,
                            trackLeft: track.left,
                            trackRight: track.right,
                            minWidth: style.minWidth,
                            maxWidth: style.maxWidth,
                        };
                    }"""
                )
                assert input_layout["controlLeft"] >= input_layout["trackLeft"] - 0.5
                assert input_layout["controlRight"] <= input_layout["trackRight"] + 0.5
                assert input_layout["minWidth"] == "0px"
                assert input_layout["maxWidth"] == "100%"

                intake.focus()
                assert intake.evaluate("element => element.matches(':focus-visible')")
                focus_style = intake.evaluate(
                    """element => {
                        const style = getComputedStyle(element);
                        return {
                            color: style.outlineColor,
                            style: style.outlineStyle,
                            width: style.outlineWidth,
                        };
                    }"""
                )
                assert focus_style == {
                    "color": "rgb(92, 242, 196)",
                    "style": "solid",
                    "width": "2px",
                }
                assert page.locator(".panel .panel").count() == 0

                intake.fill(
                    "DEMO 999 read-only md link check fixture"
                )
                with page.expect_response(
                    lambda response: "/planning/intake" in response.url and response.status == 200
                ) as response_info:
                    page.locator('form.planning-chat-form button[type="submit"]').click()
                outcome = response_info.value.json()["outcome"]
                task_id = outcome["task_id"]
                assert task_id

                # The chat creates an implementation task by default; flip it to the
                # read-only demo kind without another full run through the UI.
                demo.set_task_kind_acceptance_verification(task_id)

                # Wait for the new card to appear after the board refreshes.
                card = page.locator("article.task").filter(has_text=task_id)
                card.wait_for(timeout=30000)
                card.locator("button:has-text('Launch')").click()

                assert demo.entered.wait(timeout=15), "runner did not reach gate"

                # Record incremental event-feed requests so the provisional token
                # assertion below can prove which path delivered it.
                event_feed_requests: list[str] = []
                page.on(
                    "request",
                    lambda request: event_feed_requests.append(request.url)
                    if "/events" in request.url and "since_id=" in request.url
                    else None,
                )

                page.goto(
                    f"{demo.base_url}/projects/{demo.project_id}/floor",
                    wait_until="networkidle",
                )

                running_card = page.locator(
                    "section.floor-section:has(h3:has-text('Active Worker Runs')) article.task"
                ).filter(has_text=task_id)
                running_card.wait_for(timeout=30000)

                page.emulate_media(reduced_motion="reduce")
                live_indicator = running_card.locator(".live-pulse-dot")
                expect(live_indicator).to_have_attribute("aria-label", "Running live")
                reduced_style = live_indicator.evaluate(
                    """element => {
                        const style = getComputedStyle(element);
                        return { animationName: style.animationName, opacity: style.opacity };
                    }"""
                )
                assert reduced_style == {"animationName": "none", "opacity": "1"}
                assert page.locator(".panel .panel").count() == 0

                # Live evidence lands in the always-visible Live runs dock above
                # the columns, so no disclosure has to be opened to see it.
                dock = page.locator("section.live-run-dock")
                dock.wait_for(timeout=30000)
                expect(dock).to_contain_text(task_id)

                dock.get_by_text(DEMO_SENTINEL).wait_for(timeout=15000)

                # Only now release the provisional usage line. No board reload
                # happens in this window, so the incremental since_id feed is the
                # only way it can reach the browser.
                demo.stream_more.set()
                assert demo.provisional_emitted.wait(timeout=15), "provisional line not emitted"

                dock.get_by_text("input_tokens=12; output_tokens=3").wait_for(timeout=30000)
                dock.get_by_text(
                    "provisional; final total recorded on completion."
                ).first.wait_for(timeout=30000)
                assert event_feed_requests, "live event feed was never polled with since_id"

                # The task must still be Running while this evidence is on screen.
                expect(running_card).to_have_count(1)

                # No reply/ack affordance should appear while the run is live.
                expect(running_card.locator("textarea")).to_have_count(0)

                demo.release.set()
                assert demo.outcome_done.wait(timeout=30), "worker run outcome was not applied"

                # Reload the Execution Floor so the completed task state is visible.
                page.goto(
                    f"{demo.base_url}/projects/{demo.project_id}/floor",
                    wait_until="networkidle",
                )
                page.locator("h1.page-title").wait_for(timeout=30000)

                card = page.locator("article.task").filter(has_text=task_id)
                page.get_by_text("Actual 15").wait_for(timeout=30000)

                # Open the shared Evidence Drawer, then follow its full-report permalink.
                card.locator("button:has-text('View evidence')").click()
                drawer = page.locator("aside.evidence-drawer")
                drawer.wait_for(timeout=15000)
                drawer.get_by_text("Token log").wait_for(timeout=15000)
                drawer.locator("a:has-text('Full Session Report')").click()
                page.wait_for_url("**/sessions/**", timeout=15000)
                page.get_by_text("Native usage evidence recorded").wait_for(timeout=15000)
                page.get_by_text("native_usage").first.wait_for(timeout=15000)
                page.get_by_text(DEMO_MODEL).first.wait_for(timeout=15000)

                # Automated synthetic disposition: the unattended scenario
                # finishes itself through the normal Mark Done control. This is
                # not human acceptance or review, and no backend auto-transition
                # is involved.
                page.goto(
                    f"{demo.base_url}/projects/{demo.project_id}/floor",
                    wait_until="networkidle",
                )
                card = page.locator("article.task").filter(has_text=task_id)
                card.locator("button:has-text('View evidence')").click()
                drawer = page.locator("aside.evidence-drawer")
                drawer.locator("button:has-text('Mark Done')").click()
                drawer.locator("button:has-text('Close')").click()

                page.locator("div.floor-finished-trail article.task").filter(
                    has_text=task_id
                ).wait_for(timeout=15000)

                context.tracing.stop()
            except Exception:
                context.tracing.stop(path=str(trace_path))
                page.screenshot(path=str(screenshot_path))
                raise
            finally:
                context.close()
                browser.close()
