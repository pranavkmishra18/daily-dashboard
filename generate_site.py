#!/usr/bin/env python3
"""Run daily.py and publish its terminal output as a responsive HTML dashboard."""
from datetime import datetime
from html import escape
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "docs" / "index.html"


def main():
    result = subprocess.run(
        [sys.executable, str(ROOT / "daily.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        details = (result.stdout or "") + "\n" + (result.stderr or "")
        raise SystemExit("daily.py failed; no new page was published.\n" + details[-6000:])

    dashboard_text = result.stdout.strip()
    if not dashboard_text:
        raise SystemExit("daily.py returned no output.")

    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M %p IST")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#101827">
<meta name="description" content="Personal daily markets, portfolio and global indicators dashboard.">
<title>Pranav | Daily Dashboard</title>
<style>
:root{{--bg:#0b1220;--panel:#111c2e;--line:#263750;--text:#e8eef8;--muted:#9aabc2;--accent:#86b1ff}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(ellipse at 12% 0%,#1b3151 0,transparent 42%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh}}
.wrap{{width:min(1500px,calc(100% - 36px));margin:auto;padding:38px 0 56px}}
.top{{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-bottom:25px}}
.eyebrow{{color:var(--accent);text-transform:uppercase;letter-spacing:.16em;font-size:11px;font-weight:750}}
h1{{margin:7px 0 5px;font-size:clamp(28px,4vw,42px);letter-spacing:-.04em}}
.sub{{color:var(--muted);font-size:14px}}
.stamp{{border:1px solid var(--line);background:#111c2ecc;padding:11px 14px;border-radius:12px;color:var(--muted);font-size:11px;letter-spacing:.08em}}
.stamp strong{{color:var(--text);display:block;font-size:13px;letter-spacing:0;margin-top:4px}}
.notice{{border:1px solid #344b6c;background:#14243a;border-radius:12px;padding:13px 15px;color:#c5d5ec;font-size:13px;line-height:1.55;margin-bottom:18px}}
.panel{{border:1px solid var(--line);background:linear-gradient(145deg,#121f32,#0f1929);border-radius:17px;overflow:hidden;box-shadow:0 18px 55px #0003}}
.panel-head{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 20px;border-bottom:1px solid var(--line)}}
.panel-head h2{{margin:0;font-size:13px;letter-spacing:.08em}}
.status{{color:#8fe0b2;font-size:11px;font-weight:700;letter-spacing:.1em}}
.scroll{{overflow-x:auto;padding:18px 20px 22px}}
pre{{margin:0;color:#dce7f7;font:12.5px/1.72 ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;white-space:pre}}
footer{{color:var(--muted);font-size:12px;margin-top:18px;line-height:1.6}}
@media(max-width:650px){{.wrap{{width:calc(100% - 22px);padding-top:24px}}.scroll{{padding:14px 12px 18px}}pre{{font-size:11px}}.panel-head{{padding:14px}}}}
</style>
</head>
<body>
<main class="wrap">
<header class="top">
<div><div class="eyebrow">Personal intelligence</div><h1>Daily Dashboard</h1><div class="sub">Markets · Portfolio · Commodities · Global indicators</div></div>
<div class="stamp">LAST GENERATED<strong>{escape(timestamp)}</strong></div>
</header>
<div class="notice">This is a manually refreshed daily snapshot, not a real-time trading terminal. Quotes and indicators depend on third-party data providers and may be delayed or unavailable.</div>
<section class="panel">
<div class="panel-head"><h2>DAILY MARKET &amp; WORLD BRIEFING</h2><span class="status">● GENERATED</span></div>
<div class="scroll"><pre>{escape(dashboard_text)}</pre></div>
</section>
<footer>Refresh manually from the GitHub Actions tab. Verify prices with your broker before making investment decisions.</footer>
</main>
</body>
</html>
"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
