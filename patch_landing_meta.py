#!/usr/bin/env python3
"""
patch_landing_meta.py
─────────────────────────────────────────────────────────────────────
Lane 3 — landing-page metadata fixes.

Repairs systemic generator bugs found across the 60 programmatic
landing pages:

  1. og:title and og:description still contain "Long Island" copy on
     every non-Long-Island page (master template was not parameterized
     for these fields). Patcher rewrites them from each page's actual
     <title> and <meta name="description">.

  2. Meta descriptions truncated mid-word at ~300 chars. Patcher
     trims to ~155 chars at the nearest sentence boundary (preferred)
     or word boundary (fallback). Never cuts mid-word.

  3. twitter:title / twitter:description (if present) get the same
     treatment as their og: equivalents.

  4. Build-marker comment refreshed so deploy can be verified.

What it does NOT do:
  - Touch any human-written body copy.
  - Add new pages, links, or sections.
  - Modify the homepage (which has its own metadata, already correct).
  - Modify <title> tags (those are already correct per page).

Usage:
    cd brant-website
    python3 patch_landing_meta.py --dry-run    # preview
    python3 patch_landing_meta.py              # apply
"""

import re
import sys
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
HOMEPAGE_PATH = REPO_ROOT / "index.html"

BUILD_MARKER = "<!-- BUILD-2026-06-26-v21-landing-meta-fixes -->"

# Target lengths
META_DESC_MAX = 158   # safe under Google's ~160 char display limit
OG_DESC_MAX   = 200   # OG can be longer; LinkedIn shows ~200

# Signature identifying a landing page
LANDING_PAGE_SIGNATURE = re.compile(
    r'"@type":\s*"FinancialService".*?"Brant Professional Services Inc\."',
    re.DOTALL,
)

# Indicators that a field still contains the unfixed Long Island master copy
LONG_ISLAND_LEAKAGE = re.compile(r"long[- ]?island", re.IGNORECASE)


# ── HELPERS ─────────────────────────────────────────────────────────
def trim_smart(text: str, max_len: int) -> str:
    """
    Trim text to <= max_len chars without cutting mid-word.
    Prefers ending at a sentence boundary. Falls back to last
    complete word. Strips trailing whitespace and punctuation
    that looks like a fragment.
    """
    text = text.strip()
    if len(text) <= max_len:
        return text

    # Try sentence boundary
    candidate = text[:max_len]
    last_period = max(
        candidate.rfind(". "),
        candidate.rfind("! "),
        candidate.rfind("? "),
    )
    if last_period > max_len * 0.6:  # accept only if not too aggressive
        return candidate[: last_period + 1].strip()

    # Fall back to last word boundary
    last_space = candidate.rfind(" ")
    if last_space > 0:
        result = candidate[:last_space].rstrip(",;:—-– ").strip()
        # Strip trailing conjunctions/prepositions that read as fragments
        TRAILING_FRAGMENTS = {"and", "or", "but", "with", "for", "to", "of", "in",
                              "on", "at", "by", "from", "as", "the", "a", "an"}
        words = result.split()
        while words and words[-1].lower().rstrip(",.;:") in TRAILING_FRAGMENTS:
            words.pop()
        result = " ".join(words).rstrip(",;:—-– ").strip()
        # Add a period if it ends mid-sentence
        if result and result[-1] not in ".!?":
            result += "."
        return result

    # No spaces (pathological) — hard cut, never happens in practice
    return candidate.rstrip()


def get_tag_content(html: str, pattern: str) -> str | None:
    """Extract the content attribute of a meta tag matching pattern."""
    m = re.search(pattern, html)
    return m.group(1) if m else None


def replace_tag_content(html: str, tag_pattern: str, new_content: str) -> tuple[str, bool]:
    """
    Replace the content="..." attribute of a meta tag.
    tag_pattern must have one capture group for the OLD content.
    Returns (new_html, changed).
    """
    new_content_escaped = new_content.replace("&", "&amp;").replace('"', "&quot;")
    def _sub(m):
        full = m.group(0)
        old = m.group(1)
        return full.replace(f'content="{old}"', f'content="{new_content_escaped}"')
    new_html, n = re.subn(tag_pattern, _sub, html, count=1)
    return new_html, n > 0 and new_html != html


def derive_og_title_from_page_title(page_title: str) -> str:
    """
    From <title>Financial Leadership for X | Brant Professional Services</title>
    produce an og:title. We keep the full title — it's already well-formed
    and under 90 chars on every observed page.
    """
    return page_title.strip()


# ── PATCH FUNCTIONS ─────────────────────────────────────────────────
def patch_page(html: str) -> tuple[str, list[str]]:
    """
    Apply all Lane 3 metadata fixes. Returns (new_html, list_of_changes).
    """
    changes = []
    original = html

    # Extract the canonical signals we'll rebuild from
    page_title = get_tag_content(html, r"<title>([^<]+)</title>")
    meta_desc  = get_tag_content(html, r'<meta name="description" content="([^"]*)"')

    if not page_title or not meta_desc:
        return html, []  # not a patchable landing page

    # ─── Fix 1: Meta description — trim cleanly if over limit or truncated ───
    new_meta_desc = trim_smart(meta_desc, META_DESC_MAX)
    if new_meta_desc != meta_desc:
        html, ok = replace_tag_content(
            html,
            r'<meta name="description" content="([^"]*)"',
            new_meta_desc,
        )
        if ok:
            changes.append(f"meta-desc ({len(meta_desc)}→{len(new_meta_desc)})")

    # ─── Fix 2: og:title — rebuild from page title if leakage detected ───
    og_title = get_tag_content(html, r'<meta property="og:title" content="([^"]*)"')
    if og_title is not None:
        # Rebuild from page title whenever it leaks Long Island copy on a
        # non-Long-Island page, OR when og:title doesn't match the page title.
        new_og_title = derive_og_title_from_page_title(page_title)
        page_is_long_island = "long island" in page_title.lower()
        og_leaks_long_island = bool(LONG_ISLAND_LEAKAGE.search(og_title)) and not page_is_long_island
        if og_leaks_long_island or og_title != new_og_title:
            html, ok = replace_tag_content(
                html,
                r'<meta property="og:title" content="([^"]*)"',
                new_og_title,
            )
            if ok:
                changes.append("og:title")

    # ─── Fix 3: og:description — rebuild from (now-fixed) meta desc ───
    og_desc = get_tag_content(html, r'<meta property="og:description" content="([^"]*)"')
    if og_desc is not None:
        # Read the freshly-patched meta desc
        fresh_meta_desc = get_tag_content(html, r'<meta name="description" content="([^"]*)"') or new_meta_desc
        new_og_desc = trim_smart(fresh_meta_desc, OG_DESC_MAX)
        page_is_long_island = "long island" in page_title.lower()
        og_leaks_long_island = bool(LONG_ISLAND_LEAKAGE.search(og_desc)) and not page_is_long_island
        if og_leaks_long_island or og_desc != new_og_desc:
            html, ok = replace_tag_content(
                html,
                r'<meta property="og:description" content="([^"]*)"',
                new_og_desc,
            )
            if ok:
                changes.append("og:description")

    # ─── Fix 4: twitter:title (if present) ───
    tw_title = get_tag_content(html, r'<meta name="twitter:title" content="([^"]*)"')
    if tw_title is not None:
        new_tw_title = derive_og_title_from_page_title(page_title)
        if tw_title != new_tw_title:
            html, ok = replace_tag_content(
                html,
                r'<meta name="twitter:title" content="([^"]*)"',
                new_tw_title,
            )
            if ok:
                changes.append("twitter:title")

    # ─── Fix 5: twitter:description (if present) ───
    tw_desc = get_tag_content(html, r'<meta name="twitter:description" content="([^"]*)"')
    if tw_desc is not None:
        fresh_meta_desc = get_tag_content(html, r'<meta name="description" content="([^"]*)"') or meta_desc
        new_tw_desc = trim_smart(fresh_meta_desc, OG_DESC_MAX)
        if tw_desc != new_tw_desc:
            html, ok = replace_tag_content(
                html,
                r'<meta name="twitter:description" content="([^"]*)"',
                new_tw_desc,
            )
            if ok:
                changes.append("twitter:description")

    # ─── Fix 6: Build marker ───
    marker_re = re.compile(r"<!--\s*BUILD-[^>]*-->")
    if marker_re.search(html):
        html_new = marker_re.sub(BUILD_MARKER, html, count=1)
        if html_new != html:
            changes.append("build-marker")
            html = html_new
    else:
        head_open = re.search(r"<head[^>]*>", html)
        if head_open:
            insert_at = head_open.end()
            html = html[:insert_at] + "\n" + BUILD_MARKER + html[insert_at:]
            changes.append("build-marker")

    return html, changes


# ── DISCOVERY ───────────────────────────────────────────────────────
def find_landing_pages(root: Path) -> list[Path]:
    pages = []
    for path in root.rglob("index.html"):
        parts = set(path.parts)
        if parts & {".git", "node_modules", "dist", "build", ".cache"}:
            continue
        if path == HOMEPAGE_PATH:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if LANDING_PAGE_SIGNATURE.search(content):
            pages.append(path)
    return sorted(pages)


# ── MAIN ────────────────────────────────────────────────────────────
def main() -> int:
    dry_run = "--dry-run" in sys.argv
    pages = find_landing_pages(REPO_ROOT)
    if not pages:
        print("No landing pages found. Run this from the repo root.")
        return 1

    print(f"Found {len(pages)} landing page(s).")
    if dry_run:
        print("DRY RUN — no files will be written.\n")

    changed = 0
    skipped = 0
    for page in pages:
        rel = page.relative_to(REPO_ROOT)
        original = page.read_text(encoding="utf-8")
        new_html, changes = patch_page(original)
        if new_html == original:
            print(f"  · {rel}  (no changes needed)")
            skipped += 1
            continue
        print(f"  ✓ {rel}  [{', '.join(changes)}]")
        if not dry_run:
            page.write_text(new_html, encoding="utf-8")
        changed += 1

    print(f"\nUpdated: {changed}\nSkipped: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
