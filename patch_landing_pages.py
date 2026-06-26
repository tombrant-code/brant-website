#!/usr/bin/env python3
"""
patch_landing_pages.py
─────────────────────────────────────────────────────────────────────
Applies Lane 2 SEO fixes to all 61 programmatic landing pages.

What it does to each page (idempotent — safe to re-run):
  1. Adds "sameAs" to the FinancialService JSON-LD block with the
     firm's LinkedIn and Alignable profile URLs (entity confirmation
     signal for Google).
  2. Bumps / inserts a build marker comment so you can verify in
     DevTools that the deployed version is current.

What it does NOT do:
  - Touch any human-written copy (H1s, ledes, vignettes, body text).
  - Remove or modify the BreadcrumbList JSON-LD block.
  - Modify the homepage (already patched separately).

Usage:
    cd brant-website                  # repo root
    python3 patch_landing_pages.py    # patches in place

The script discovers pages by walking the repo and finding any
index.html that has the FinancialService JSON-LD signature, so it
will pick up new landing pages added later without code changes.
"""

import re
import sys
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent

SAME_AS_URLS = [
    "https://www.linkedin.com/company/brantprofessionalservices/",
    "https://www.alignable.com/wantagh-ny/brant-professional-services-inc",
]

# Build marker — bump the version when you re-run with new changes
BUILD_MARKER = "<!-- BUILD-2026-06-25-v20-landing-seo-fixes -->"

# Signature that identifies a landing page (vs. the homepage SPA or
# unrelated HTML files). Landing pages have a FinancialService JSON-LD
# block with the firm name.
LANDING_PAGE_SIGNATURE = re.compile(
    r'"@type":\s*"FinancialService".*?"Brant Professional Services Inc\."',
    re.DOTALL,
)

# Skip the homepage — it's patched separately and has a different structure
HOMEPAGE_PATH = REPO_ROOT / "index.html"


# ── PATCH FUNCTIONS ─────────────────────────────────────────────────
def add_same_as(html: str) -> tuple[str, bool]:
    """
    Insert a "sameAs" array into the FinancialService JSON-LD block.
    If sameAs already exists, replace it to ensure correct contents.
    Returns (new_html, changed).
    """
    # Find the FinancialService block
    fs_block_pattern = re.compile(
        r'(<script type="application/ld\+json">\s*\{[^<]*?"@type":\s*"FinancialService".*?\})\s*(</script>)',
        re.DOTALL,
    )
    m = fs_block_pattern.search(html)
    if not m:
        return html, False

    block = m.group(1)
    closing = m.group(2)

    # Build the sameAs JSON fragment
    same_as_json = '"sameAs": [\n    ' + ",\n    ".join(
        f'"{url}"' for url in SAME_AS_URLS
    ) + "\n  ]"

    if '"sameAs"' in block:
        # Replace existing sameAs (handles both array and string forms)
        new_block = re.sub(
            r'"sameAs"\s*:\s*(\[[^\]]*\]|"[^"]*")',
            same_as_json,
            block,
            count=1,
        )
        if new_block == block:
            return html, False
    else:
        # Insert sameAs before the closing brace of the JSON object.
        # Find the last `}` of the JSON block specifically.
        # Strategy: find the position of the final } in the captured block
        # and insert ",\n  <sameAs>" before it.
        last_brace = block.rfind("}")
        if last_brace == -1:
            return html, False
        # Ensure we have a comma after the prior field
        before = block[:last_brace].rstrip()
        if not before.endswith(","):
            before = before + ","
        new_block = before + "\n  " + same_as_json + "\n}"

    new_html = html[:m.start()] + new_block + "\n" + closing + html[m.end():]
    return new_html, new_html != html


def bump_build_marker(html: str) -> tuple[str, bool]:
    """Insert or update the build marker comment in <head>."""
    marker_pattern = re.compile(r"<!--\s*BUILD-[^>]*-->")
    if marker_pattern.search(html):
        new_html = marker_pattern.sub(BUILD_MARKER, html, count=1)
        return new_html, new_html != html
    # Insert after <head>
    head_open = re.search(r"<head[^>]*>", html)
    if not head_open:
        return html, False
    insert_at = head_open.end()
    new_html = html[:insert_at] + "\n" + BUILD_MARKER + html[insert_at:]
    return new_html, True


# ── DISCOVERY ───────────────────────────────────────────────────────
def find_landing_pages(root: Path) -> list[Path]:
    """Walk repo, return all index.html files that match the landing-page signature."""
    pages = []
    for path in root.rglob("index.html"):
        # Skip vendored / node_modules / .git / homepage
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
        print(f"  (Searched: {REPO_ROOT})")
        return 1

    print(f"Found {len(pages)} landing page(s).")
    if dry_run:
        print("DRY RUN — no files will be written.\n")

    changed_count = 0
    skipped_count = 0
    errors = []

    for page in pages:
        rel = page.relative_to(REPO_ROOT)
        try:
            original = page.read_text(encoding="utf-8")
        except OSError as e:
            errors.append((rel, str(e)))
            continue

        html = original
        html, c1 = add_same_as(html)
        html, c2 = bump_build_marker(html)

        if html == original:
            print(f"  · {rel}  (already up to date)")
            skipped_count += 1
            continue

        changes = []
        if c1: changes.append("sameAs")
        if c2: changes.append("build-marker")
        print(f"  ✓ {rel}  [{', '.join(changes)}]")

        if not dry_run:
            page.write_text(html, encoding="utf-8")
        changed_count += 1

    print()
    print(f"Updated: {changed_count}")
    print(f"Skipped (already current): {skipped_count}")
    if errors:
        print(f"Errors:  {len(errors)}")
        for rel, msg in errors:
            print(f"  ! {rel}: {msg}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
