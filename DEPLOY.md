# Brant SEO Restructure — Deploy Guide

## What's in this drop

```
regions/              4 NY regional pages (Long Island, NYC, Capital Region, Adirondacks)
states/               51 state pages (all 50 + DC)
verticals/            4 industry pages (Construction, Law Firms, Cannabis, Business Financial Services)
national/             1 US national page
global/               1 international page
_redirects            301s for all old /services/* URLs → nearest new page
sitemap.xml           68 URLs (homepage + key SPA anchors + 61 new pages)
```

**Total: 61 new pages.** Your existing `index.html` is not touched.

---

## Deploy in 4 steps (GitHub Desktop)

1. **Unzip this archive into your local repo folder** (the same folder where `index.html` lives).
   The folders `regions/`, `states/`, `verticals/`, `national/`, `global/` will land alongside `index.html`,
   and `_redirects` + `sitemap.xml` will land at the root.

2. **Open GitHub Desktop.** You'll see ~63 new/changed files in the left panel:
   - 61 new `index.html` files (one per new page)
   - `_redirects` (new at repo root)
   - `sitemap.xml` (replaces existing if present)

3. **Commit:**
   - Summary: `SEO restructure: replace 1,440 location pages with 61 strong pages`
   - Description (optional): `4 regions + 51 states + 4 verticals + national + global. Redirects all old /services/* URLs.`
   - Click **Commit to main**.

4. **Push origin.** Cloudflare Pages auto-deploys in 1–3 minutes.

---

## Verify after deploy

Open these in a browser and confirm they load:

- `https://brantprofessionalservices.com/regions/long-island/` ← your master template
- `https://brantprofessionalservices.com/regions/nyc/`
- `https://brantprofessionalservices.com/states/texas/`
- `https://brantprofessionalservices.com/verticals/construction/`
- `https://brantprofessionalservices.com/verticals/cannabis/` ← should show the cannabis disclaimer
- `https://brantprofessionalservices.com/national/`
- `https://brantprofessionalservices.com/global/`

Test one old URL redirect:
- Open `https://brantprofessionalservices.com/services/compliance-plainview/`
- Should 301 to `/regions/long-island/`

---

## Old `/services/*` folder — what to do

**You can delete the entire `/services/` folder from the repo** in a follow-up commit. The `_redirects` file catches every URL pattern there, so even if someone visits a deleted page, they're redirected before Cloudflare looks for the file.

But it's not required. Cloudflare evaluates `_redirects` before serving files, so the redirects work whether the old files exist or not. Cleaner to delete them eventually.

---

## Google Search Console — after deploy

1. **Submit the new sitemap.**
   - Search Console → Sitemaps → Add new sitemap → `sitemap.xml` → Submit.
   - If your old sitemap (with the 1,440 URLs) is still listed, remove it.

2. **Don't manually request removal of the old URLs.** Google will see the 301s on its own crawl and update. Manual removal can hurt; let the redirects do the work.

3. **Index Coverage report** will show "Page with redirect" status climbing over the next 2–4 weeks. That's expected and healthy.

---

## LinkedIn / social cache

If you've shared any of the old `/services/*` URLs on LinkedIn or anywhere else, the LinkedIn Post Inspector will cache the old preview. To refresh:

- LinkedIn: `https://www.linkedin.com/post-inspector/` → paste the URL → Inspect.
- The new pages each have a proper `<title>` and meta description, so previews will look clean.

---

## Homepage update (separate, flagged in handoff)

The live homepage (`index.html`) still shows outdated track-record numbers in the "Demonstrated Track Record" / "Why Brant" section ($25M / $4.5M from older copy). For site-wide consistency, those should be updated to match the locked stat set on the new pages:

- **$200M** — Largest enterprise valuation supported
- **$50M** — Largest capital transaction facilitated
- **100+** — Lenders and capital partners in our network
- **10+** — Years of underwriting and private lending experience

Out of scope for this deploy per your instruction (no `index.html` edits), but flagged for a future session.

---

## If something doesn't work

- **A page returns 404:** the `index.html` inside that page's folder may not have made it into the commit. Check GitHub Desktop's history.
- **An old URL doesn't redirect:** the `_redirects` file needs to be at the **root** of the repo (same level as `index.html`), not inside a subfolder.
- **Cloudflare didn't deploy:** check the Pages dashboard → Deployments tab. The build log will show errors if any.
