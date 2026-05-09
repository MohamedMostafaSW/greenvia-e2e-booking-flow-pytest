"""
Reporter
========
Tracks each step of a flow and renders a single modern HTML report
(stats summary + per-step rows + screenshot lightbox).

Usage:

    reporter = Reporter(reports_dir)
    reporter.attach_driver(driver)

    with reporter.step("Open homepage"):
        home.open(...)
        reporter.attach_screenshot("homepage")

    reporter.set_outcome("PASS" | "FAIL" | "SITE_BUG")
    reporter.render(reports_dir / "main_flow_report.html")
"""
from __future__ import annotations

import html
import logging
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class StepResult:
    name: str
    status: str = "PENDING"          # PASS | FAIL | WARN | SKIP | RUNNING
    error: str = ""
    screenshot: str = ""             # path relative to report dir
    duration: float = 0.0
    started_at: float = 0.0
    notes: List[str] = field(default_factory=list)


class Reporter:
    """Step-tracker + HTML report generator."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.shot_dir = self.output_dir / "screenshots"
        self.shot_dir.mkdir(parents=True, exist_ok=True)
        self.steps: List[StepResult] = []
        self.run_started = time.time()
        self.run_ended: Optional[float] = None
        self.outcome: str = "UNKNOWN"
        self.metadata: dict = {}
        self._driver = None

    # ── Setup ─────────────────────────────────────────────────────────
    def attach_driver(self, driver) -> None:
        self._driver = driver

    def set_meta(self, **kw) -> None:
        self.metadata.update(kw)

    def set_outcome(self, value: str) -> None:
        self.outcome = value

    # ── Step recording ────────────────────────────────────────────────
    @contextmanager
    def step(self, name: str):
        s = StepResult(name=name, status="RUNNING", started_at=time.time())
        self.steps.append(s)
        try:
            yield s
            if s.status == "RUNNING":
                s.status = "PASS"
        except Exception as exc:
            s.status = "FAIL"
            s.error = f"{type(exc).__name__}: {exc}"
            s.screenshot = self.snap(f"{name}_fail")
            raise
        finally:
            s.duration = round(time.time() - s.started_at, 2)

    def snap(self, label: str) -> str:
        if self._driver is None:
            return ""
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_")[:60] or "shot"
        ts = int(time.time() * 1000)
        path = self.shot_dir / f"{safe}_{ts}.png"
        try:
            self._driver.save_screenshot(str(path))
            return path.relative_to(self.output_dir).as_posix()
        except Exception as exc:
            log.debug("screenshot failed: %s", exc)
            return ""

    def attach_screenshot(self, label: str = "") -> str:
        if not self.steps:
            return ""
        s = self.steps[-1]
        path = self.snap(label or s.name)
        if path:
            s.screenshot = path
        return path

    def note(self, text: str) -> None:
        if self.steps:
            self.steps[-1].notes.append(text)

    # ── HTML rendering ────────────────────────────────────────────────
    def render(self, output_path: Path) -> Path:
        self.run_ended = self.run_ended or time.time()
        passed = sum(1 for s in self.steps if s.status == "PASS")
        failed = sum(1 for s in self.steps if s.status == "FAIL")
        warned = sum(1 for s in self.steps if s.status == "WARN")
        total  = len(self.steps)
        total_duration = round(self.run_ended - self.run_started, 2)
        ran_at = datetime.fromtimestamp(self.run_started).strftime("%Y-%m-%d %H:%M:%S")

        banner = {
            "PASS":     ("#10b981", "All steps passed"),
            "FAIL":     ("#ef4444", "Test run failed"),
            "SITE_BUG": ("#f59e0b", "Known site bug encountered"),
            "UNKNOWN":  ("#6366f1", "Run completed"),
        }.get(self.outcome, ("#6366f1", self.outcome))
        banner_color, banner_text = banner

        meta_rows = "".join(
            f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
            for k, v in self.metadata.items()
        )
        step_rows = "".join(self._render_step_row(s) for s in self.steps)

        html_doc = _HTML_TEMPLATE.format(
            ran_at=ran_at,
            banner_color=banner_color,
            banner_text=html.escape(banner_text),
            total=total,
            passed=passed,
            failed=failed,
            warned=warned,
            total_duration=total_duration,
            meta_rows=meta_rows,
            step_rows=step_rows,
        )
        output_path.write_text(html_doc, encoding="utf-8")
        return output_path

    def _render_step_row(self, s: StepResult) -> str:
        idx = self.steps.index(s) + 1
        cls = s.status.lower()
        pill_cls = {
            "PASS": "pass", "FAIL": "fail", "WARN": "warn",
            "SKIP": "warn", "RUNNING": "warn", "PENDING": "warn",
        }.get(s.status, "warn")
        notes_html = ""
        if s.notes:
            notes_html = (
                '<div class="notes">'
                + html.escape("\n".join(s.notes))
                + "</div>"
            )
        error_html = ""
        if s.error:
            error_html = f'<div class="error">{html.escape(s.error)}</div>'
        shot_html = ""
        if s.screenshot:
            shot_html = (
                f'<div class="screenshot-wrap">'
                f'<a href="{html.escape(s.screenshot)}">'
                f'<img src="{html.escape(s.screenshot)}" alt="screenshot">'
                f"</a></div>"
            )
        return (
            f'<div class="step {cls}">'
            f'<div class="marker">{idx}</div>'
            f'<div class="body">'
            f'<div class="name">{html.escape(s.name)}'
            f'<span class="duration">· {s.duration:.2f}s</span></div>'
            f"{notes_html}{error_html}{shot_html}"
            f"</div>"
            f'<span class="pill {pill_cls}">{s.status}</span>'
            f"</div>"
        )


# ── HTML template (kept at module bottom so the class stays readable) ─
_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GreenVia E2E Report — {ran_at}</title>
<style>
:root {{
  --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #64748b;
  --border: #e2e8f0;
  --pass: #10b981; --pass-bg: #d1fae5;
  --fail: #ef4444; --fail-bg: #fee2e2;
  --warn: #f59e0b; --warn-bg: #fef3c7;
  --info: #6366f1; --info-bg: #e0e7ff;
  --shadow: 0 1px 2px rgba(15,23,42,0.04), 0 4px 16px rgba(15,23,42,0.06);
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}}
.container {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 80px; }}
h1 {{ margin: 0 0 6px; font-size: 28px; font-weight: 700; letter-spacing: -0.01em; }}
.subtitle {{ color: var(--muted); font-size: 14px; }}
.banner {{
  margin: 22px 0 28px; padding: 16px 20px; border-radius: 12px;
  background: {banner_color}; color: #fff;
  font-weight: 600; font-size: 16px; letter-spacing: 0.02em;
  box-shadow: var(--shadow);
}}
.stats {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px; margin-bottom: 28px;
}}
.stat {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 18px; box-shadow: var(--shadow);
}}
.stat .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
.stat .value {{ font-size: 32px; font-weight: 700; margin-top: 6px; line-height: 1; }}
.stat.pass .value {{ color: var(--pass); }}
.stat.fail .value {{ color: var(--fail); }}
.stat.warn .value {{ color: var(--warn); }}
.stat.total .value {{ color: var(--info); }}
.section-title {{
  font-size: 13px; font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.06em; margin: 32px 0 10px;
}}
.metadata-card, .steps-card {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; box-shadow: var(--shadow); overflow: hidden;
}}
.metadata-card table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
.metadata-card th {{ text-align: left; padding: 10px 16px; color: var(--muted); font-weight: 500; width: 200px; vertical-align: top; }}
.metadata-card td {{ padding: 10px 16px; border-left: 1px solid var(--border); word-break: break-all; }}
.metadata-card tr + tr th, .metadata-card tr + tr td {{ border-top: 1px solid var(--border); }}
.step {{
  display: grid; grid-template-columns: 36px 1fr auto; gap: 14px;
  padding: 16px 18px; align-items: center; border-bottom: 1px solid var(--border);
}}
.step:last-child {{ border-bottom: 0; }}
.step .marker {{
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px;
  background: var(--info-bg); color: var(--info);
}}
.step.pass .marker {{ background: var(--pass-bg); color: var(--pass); }}
.step.fail .marker {{ background: var(--fail-bg); color: var(--fail); }}
.step.warn .marker {{ background: var(--warn-bg); color: var(--warn); }}
.step .name {{ font-weight: 600; font-size: 15px; }}
.step .name .duration {{ color: var(--muted); font-weight: 400; font-size: 13px; margin-left: 8px; }}
.pill {{
  display: inline-block; padding: 4px 12px; border-radius: 999px;
  font-size: 12px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase;
}}
.pill.pass {{ background: var(--pass-bg); color: var(--pass); }}
.pill.fail {{ background: var(--fail-bg); color: var(--fail); }}
.pill.warn {{ background: var(--warn-bg); color: var(--warn); }}
.notes, .error {{
  margin: 10px 0 0; padding: 10px 14px; border-radius: 8px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12px; white-space: pre-wrap;
}}
.notes {{ background: #f1f5f9; color: var(--text); }}
.error {{ background: var(--fail-bg); color: #7f1d1d; }}
.screenshot-wrap {{ margin-top: 12px; }}
.screenshot-wrap a {{ display: inline-block; }}
.screenshot-wrap img {{
  max-width: 360px; max-height: 220px; border-radius: 8px;
  border: 1px solid var(--border); box-shadow: var(--shadow);
  cursor: zoom-in; transition: transform 0.15s ease;
}}
.screenshot-wrap img:hover {{ transform: translateY(-2px); }}
.step .body {{ min-width: 0; }}
.lightbox {{
  position: fixed; inset: 0; background: rgba(15,23,42,0.85);
  display: none; align-items: center; justify-content: center;
  cursor: zoom-out; z-index: 100; padding: 24px;
}}
.lightbox.open {{ display: flex; }}
.lightbox img {{ max-width: 100%; max-height: 100%; border-radius: 8px; }}
.footer {{ margin-top: 30px; color: var(--muted); font-size: 12px; text-align: center; }}
@media (max-width: 640px) {{
  .step {{ grid-template-columns: 32px 1fr; }}
  .step .pill {{ grid-column: 2 / 3; justify-self: start; margin-top: 6px; }}
}}
</style>
</head>
<body>
<div class="container">
  <h1>GreenVia Border Trip — E2E Report</h1>
  <div class="subtitle">Run started {ran_at} · duration {total_duration}s</div>

  <div class="banner">{banner_text}</div>

  <div class="stats">
    <div class="stat total"><div class="label">Total steps</div><div class="value">{total}</div></div>
    <div class="stat pass"><div class="label">Passed</div><div class="value">{passed}</div></div>
    <div class="stat fail"><div class="label">Failed</div><div class="value">{failed}</div></div>
    <div class="stat warn"><div class="label">Warnings</div><div class="value">{warned}</div></div>
  </div>

  <div class="section-title">Run details</div>
  <div class="metadata-card">
    <table>{meta_rows}</table>
  </div>

  <div class="section-title">Steps</div>
  <div class="steps-card">{step_rows}</div>

  <div class="footer">Generated by tests/main_flow.py</div>
</div>

<div class="lightbox" id="lb" onclick="this.classList.remove('open')">
  <img id="lbi" src="" alt="">
</div>
<script>
document.querySelectorAll('.screenshot-wrap a').forEach(a => {{
  a.addEventListener('click', e => {{
    e.preventDefault();
    const lb = document.getElementById('lb');
    document.getElementById('lbi').src = a.getAttribute('href');
    lb.classList.add('open');
  }});
}});
</script>
</body>
</html>
"""
