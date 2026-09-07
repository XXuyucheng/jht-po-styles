#!/usr/bin/env python3
"""Extract 款号 from Jushuitan (聚水潭) H5 purchase-order detail pages.

Uses Playwright to render the uni-app SPA (hash-route URLs). Do not use
requests/curl — the server never receives the #fragment and returns an empty shell.

Examples:
  python jht_po_styles.py "https://jhtwechat.erp321.com/jht/h5/wx/#/pages/wx/purchaseorder/detail/index?po_id=..."
  python jht_po_styles.py "URL" --until 6047 --inclusive
  python jht_po_styles.py "URL" --skip 2780,2763 --strike 2234,2275,5507 --md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, unquote, urlparse

# C310-1-2231, C301-1-6464, C310-1-2267+2268, C310-1-2963/6033, C310-2402 / C310-T001
# Prefix is C + 3 digits (not only C310) — first rows can be other series like C301.
STYLE_RE = re.compile(r"^C\d{3}-(?:1-)?[\dA-Za-z]+(?:[+/][\dA-Za-z]+)*$")
# Some rows render with a leading colon, e.g. ":C310-1-6123"
STYLE_FIND_RE = re.compile(r"C\d{3}-(?:1-)?[\dA-Za-z]+(?:[+/][\dA-Za-z]+)*")

EXTRACT_JS = """
async () => {
  // Virtual lists unmount off-screen rows. Collect WHILE scrolling, not only at bottom.
  // Normalize leading junk (e.g. ":C310-1-6123") before matching.
  // Prefix is C + 3 digits (C310, C301, …) — do not hardcode C310 only.
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const findRe = /C\\d{3}-(?:1-)?[\\dA-Za-z]+(?:[+\\/][\\dA-Za-z]+)*/;
  const ordered = [];
  const seen = new Set();
  const scrollY = () =>
    window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;

  const normalizeStyle = (raw) => {
    const t = String(raw || '').trim().replace(/^[:：\\s]+/, '').trim();
    const m = t.match(findRe);
    return m ? m[0] : null;
  };

  const harvest = () => {
    const batch = [];
    const nodes = document.querySelectorAll(
      '.weight-600.justify-center.text-2-lines, .weight-600.justify-center, *'
    );
    for (const el of Array.from(nodes)) {
      if (el.children.length !== 0) continue;
      const style = normalizeStyle(el.textContent || '');
      if (!style || seen.has(style)) continue;
      const top = el.getBoundingClientRect().top + scrollY();
      batch.push({ t: style, top });
    }
    batch.sort((a, b) => a.top - b.top || a.t.localeCompare(b.t));
    for (const { t } of batch) {
      if (seen.has(t)) continue;
      seen.add(t);
      ordered.push(t);
    }
  };

  const findScrollers = () => {
    const out = [];
    const root = document.scrollingElement || document.documentElement;
    if (root) out.push(root);
    for (const el of Array.from(document.querySelectorAll('*'))) {
      const st = window.getComputedStyle(el);
      const oy = st.overflowY;
      if ((oy === 'auto' || oy === 'scroll' || oy === 'overlay') &&
          el.scrollHeight > el.clientHeight + 40) {
        out.push(el);
      }
    }
    out.sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
    return out;
  };

  const scrollOne = async (scroller) => {
    scroller.scrollTop = 0;
    await sleep(400);
    harvest();
    let last = -1, same = 0, stagnantHarvest = 0, prevCount = ordered.length;
    for (let i = 0; i < 400; i++) {
      const step = Math.max(240, Math.floor(scroller.clientHeight * 0.7) || 480);
      scroller.scrollTop += step;
      await sleep(140);
      harvest();
      if (ordered.length === prevCount) stagnantHarvest++;
      else { stagnantHarvest = 0; prevCount = ordered.length; }
      const y = scroller.scrollTop;
      if (y === last) {
        if (++same > 10) break;
      } else {
        same = 0;
        last = y;
      }
      if (same > 3 && stagnantHarvest > 8) break;
    }
    scroller.scrollTop = scroller.scrollHeight;
    await sleep(600);
    harvest();
    scroller.scrollTop = 0;
    await sleep(400);
    harvest();
  };

  await sleep(800);
  harvest();
  const scrollers = findScrollers();
  if (scrollers.length === 0) {
    const el = document.scrollingElement || document.documentElement;
    await scrollOne(el);
  } else {
    const used = new Set();
    for (const s of scrollers.slice(0, 3)) {
      if (used.has(s)) continue;
      used.add(s);
      await scrollOne(s);
    }
  }
  harvest();
  return { total: ordered.length, styles: ordered, title: document.title };
}
"""


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_data_dir() -> Path:
    """Per-user data dir for Chromium downloads (Windows installer / portable)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "jht-po-styles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_playwright_browsers_path() -> Path:
    """Point Playwright at a writable browsers directory."""
    browsers = app_data_dir() / "ms-playwright"
    browsers.mkdir(parents=True, exist_ok=True)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
    return browsers


def chromium_installed(browsers_path: Path | None = None) -> bool:
    root = browsers_path or Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", app_data_dir() / "ms-playwright")
    )
    if not root.exists():
        return False
    return any(root.glob("chromium*")) or any(root.glob("chromium_headless_shell*"))


def ensure_chromium() -> None:
    """Download Chromium into PLAYWRIGHT_BROWSERS_PATH if missing (first run)."""
    browsers = configure_playwright_browsers_path()
    if chromium_installed(browsers):
        return
    try:
        from playwright.__main__ import main as pw_main
    except ImportError as e:
        raise RuntimeError(
            "playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        ) from e

    old_argv = sys.argv
    try:
        sys.argv = ["playwright", "install", "chromium"]
        try:
            pw_main()
        except SystemExit as se:
            if se.code not in (0, None):
                raise RuntimeError(
                    f"Chromium install failed (exit {se.code}). Check network, then retry."
                ) from se
    finally:
        sys.argv = old_argv

    if not chromium_installed(browsers):
        raise RuntimeError(
            "Chromium install finished but browser files were not found.\n"
            f"Expected under: {browsers}\n"
            "Try running: python -m playwright install chromium"
        )


def parse_suffix_list(raw: str | None) -> set[str]:
    """Parse comma/dot/space-separated suffixes; strip trailing separators."""
    if not raw:
        return set()
    parts = re.split(r"[,.\s]+", raw.strip("., \t\n"))
    return {p.strip() for p in parts if p.strip()}


def normalize_style(text: str) -> str | None:
    """Strip leading junk (e.g. ':C310-1-6123') and return canonical style or None."""
    t = (text or "").strip().lstrip(":：").strip()
    m = STYLE_FIND_RE.search(t)
    if not m:
        return None
    style = m.group(0)
    return style if STYLE_RE.match(style) else None


def get_primary_suffix(style: str) -> str:
    return style.split("-").pop().split("/")[0].split("+")[0]


def all_suffixes(style: str) -> list[str]:
    tail = style.split("-", 2)[-1]
    out: list[str] = []
    for chunk in tail.split("/"):
        out.extend(p for p in chunk.split("+") if p)
    return out


def unicode_strike(text: str) -> str:
    return "".join(ch + "\u0336" for ch in text)


def po_id_from_url(url: str) -> str | None:
    # Query may sit after #/path?...
    if "#" in url:
        fragment = url.split("#", 1)[1]
        if "?" in fragment:
            qs = parse_qs(fragment.split("?", 1)[1])
            if "po_id" in qs:
                return qs["po_id"][0]
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "po_id" in qs:
        return qs["po_id"][0]
    return None


@dataclass
class FilterResult:
    styles: list[str]
    struck: list[str]
    unmatched_strike: list[str]
    skipped: list[str]
    unmatched_skip: list[str]


def apply_filters(
    styles: Iterable[str],
    *,
    until: str | None,
    inclusive: bool,
    skip: set[str],
    strike: set[str],
) -> FilterResult:
    """Two-phase filter: extract/cutoff first, then traverse to skip/strike.

    1. Normalize + keep page order; apply cutoff only.
    2. Walk that full list: skip removes a row; strike marks a kept row.
       Both skip and strike match any combo segment (/, +).
    """
    # Phase 0: normalize any leftover display junk
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in styles:
        style = normalize_style(raw) or (raw if STYLE_RE.match(raw.strip()) else None)
        if not style or style in seen:
            continue
        seen.add(style)
        normalized.append(style)

    # Phase 1: cutoff only — keep every row in range
    scoped: list[str] = []
    for s in normalized:
        primary = get_primary_suffix(s)
        if until and not inclusive and primary == until:
            break
        scoped.append(s)
        if until and inclusive and primary == until:
            break

    # Phase 2: traverse and mark
    kept: list[str] = []
    skipped: list[str] = []
    struck: list[str] = []
    matched_strike: set[str] = set()
    matched_skip: set[str] = set()

    for s in scoped:
        suffixes = all_suffixes(s)
        skip_hits = [x for x in suffixes if x in skip]
        if skip_hits:
            skipped.append(s)
            matched_skip.update(skip_hits)
            continue
        kept.append(s)
        strike_hits = [x for x in suffixes if x in strike]
        if strike_hits:
            struck.append(s)
            matched_strike.update(strike_hits)

    return FilterResult(
        styles=kept,
        struck=struck,
        unmatched_strike=sorted(strike - matched_strike),
        skipped=skipped,
        unmatched_skip=sorted(skip - matched_skip),
    )


def format_output(
    styles: list[str],
    *,
    strike: set[str],
    check: set[str],
    md: bool,
    unicode_strike_mode: bool,
) -> str:
    lines: list[str] = []
    for s in styles:
        is_struck = bool(set(all_suffixes(s)) & strike)
        is_checked = get_primary_suffix(s) in check
        text = s
        if is_struck:
            text = unicode_strike(s) if unicode_strike_mode else f"~~{s}~~"
        if md:
            mark = "x" if is_checked else " "
            if is_struck and not unicode_strike_mode:
                lines.append(f"- [{mark}] ~~{s}~~")
            elif is_struck and unicode_strike_mode:
                lines.append(f"- [{mark}] {text}")
            else:
                lines.append(f"- [{mark}] {s}")
        else:
            lines.append(text)
    return "\n".join(lines)


def extract_styles(
    url: str,
    *,
    headed: bool = False,
    timeout_ms: int = 60_000,
    storage_state: str | None = None,
    user_data_dir: str | None = None,
) -> list[str]:
    configure_playwright_browsers_path()
    ensure_chromium()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        ) from e

    with sync_playwright() as p:
        if user_data_dir:
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=not headed,
                viewport={"width": 420, "height": 900},
            )
            browser = None
            page = context.new_page()
        else:
            browser = p.chromium.launch(headless=not headed)
            context = browser.new_context(
                viewport={"width": 420, "height": 900},
                storage_state=storage_state if storage_state else None,
            )
            page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # SPA route settle
            page.wait_for_timeout(2000)
            title = page.title()
            if "订单详情" not in title and "采购" not in title:
                # Give SPA a bit more time to set title
                page.wait_for_timeout(3000)
                title = page.title()
            if "订单详情" not in title:
                raise RuntimeError(
                    f"Page title is {title!r}, expected 订单详情. "
                    "Share link may require login — try --headed or --user-data-dir / --storage-state."
                )

            result = page.evaluate(EXTRACT_JS)
            if isinstance(result, str):
                result = json.loads(result)
            styles = result.get("styles") or []
            if not styles:
                raise RuntimeError(
                    "No style numbers found. Page may still be loading or layout changed."
                )
            return styles
        finally:
            context.close()
            if browser is not None:
                browser.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extract 款号 from Jushuitan H5 purchase-order pages (Playwright)."
    )
    p.add_argument(
        "url",
        help="Full purchase-order URL (quote it in the shell). Hash #fragment is required.",
    )
    p.add_argument(
        "--until",
        metavar="SUFFIX",
        help="Stop at this primary suffix (e.g. 6047). Exclusive unless --inclusive.",
    )
    p.add_argument(
        "--inclusive",
        action="store_true",
        help="Include the --until suffix row (含本号码).",
    )
    p.add_argument(
        "--skip",
        metavar="LIST",
        help="Suffixes to remove after full extract (any combo segment). e.g. 2780,2763.",
    )
    p.add_argument(
        "--strike",
        metavar="LIST",
        help="Suffixes to strikethrough (any combo segment). Keeps rows in list.",
    )
    p.add_argument(
        "--check",
        metavar="LIST",
        help="Primary suffixes to mark [x] when using --md.",
    )
    p.add_argument(
        "--md",
        action="store_true",
        help="Output markdown checkboxes (- [ ] / - [x]).",
    )
    p.add_argument(
        "--unicode-strike",
        action="store_true",
        help="Use U+0336 combining strokes (备忘录-friendly) instead of ~~markdown~~.",
    )
    p.add_argument(
        "--both-strike",
        action="store_true",
        help="When --strike is set, print unicode list then markdown ~~ list.",
    )
    p.add_argument("--headed", action="store_true", help="Show browser window.")
    p.add_argument(
        "--storage-state",
        metavar="FILE",
        help="Playwright storage_state JSON (cookies) for logged-in sessions.",
    )
    p.add_argument(
        "--user-data-dir",
        metavar="DIR",
        help="Persistent Chromium profile directory.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=60_000,
        help="Navigation timeout in ms (default 60000).",
    )
    p.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write list to file (UTF-8). Still prints summary to stderr.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    url = unquote(args.url.strip())
    skip = parse_suffix_list(args.skip)
    strike = parse_suffix_list(args.strike)
    check = parse_suffix_list(args.check)

    try:
        styles = extract_styles(
            url,
            headed=args.headed,
            timeout_ms=args.timeout,
            storage_state=args.storage_state,
            user_data_dir=args.user_data_dir,
        )
    except RuntimeError as e:
        raise SystemExit(str(e)) from e

    result = apply_filters(
        styles,
        until=args.until,
        inclusive=args.inclusive,
        skip=skip,
        strike=strike,
    )

    po_id = po_id_from_url(url) or "?"
    parts = [f"已从采购单 **{po_id}** 提取 **{len(result.styles)}** 个款号"]
    if result.struck:
        parts[0] += f"，其中 **{len(result.struck)}** 个已加删除线"
    parts[0] += "。"
    if args.until:
        parts.append(
            f"截止：{args.until}（{'含' if args.inclusive else '不含'}本号）"
        )
    if result.skipped:
        parts.append(f"已跳过 {len(result.skipped)} 个：{', '.join(result.skipped)}")
    if result.unmatched_strike:
        parts.append(
            "删除线未命中：" + ", ".join(result.unmatched_strike)
        )
    if result.unmatched_skip:
        parts.append("跳过未命中：" + ", ".join(result.unmatched_skip))
    plus = [s for s in result.styles if "+" in s]
    if plus:
        parts.append("`+` 组合款：" + "、".join(plus))

    summary = "\n".join(parts)
    print(summary, file=sys.stderr)
    print(
        "复制下面整段 → 粘贴到备忘录 → 全选 → 点「核对清单」☑️",
        file=sys.stderr,
    )
    print(file=sys.stderr)

    use_unicode = args.unicode_strike or (args.both_strike and bool(strike))
    body = format_output(
        result.styles,
        strike=strike,
        check=check,
        md=args.md,
        unicode_strike_mode=use_unicode and not args.md,
    )

    # --md with strikethrough: markdown ~~ by default unless --unicode-strike
    if args.md:
        body = format_output(
            result.styles,
            strike=strike,
            check=check,
            md=True,
            unicode_strike_mode=args.unicode_strike,
        )

    blocks = [body]
    if args.both_strike and strike and not args.md:
        md_body = format_output(
            result.styles,
            strike=strike,
            check=check,
            md=False,
            unicode_strike_mode=False,
        )
        blocks.append("")
        blocks.append("--- markdown ~~ ---")
        blocks.append(md_body)

    text = "\n".join(blocks) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
