"""Print docs/guide/guide.html to docs/SmartWaste_AI_Setup_and_User_Guide.pdf (Chromium/Edge via Playwright).

The cover is printed full-bleed (no margins) and the body with margins, page numbers and a footer; PyMuPDF merges them.
Edit the HTML (and regenerate screenshots in docs/guide/ if the UI changed), then run:
    python scripts/make_guide_pdf.py
"""
import tempfile
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "guide" / "guide.html"
OUT = ROOT / "docs" / "SmartWaste_AI_Setup_and_User_Guide.pdf"

FOOTER = (
    '<div style="font-size:8px;width:100%;text-align:center;color:#64748b;font-family:Segoe UI,Arial,sans-serif">'
    'SmartWaste AI &middot; Setup and User Guide &middot; Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
)
COVER_ONLY = """
@page { size: A4; margin: 0; }
body > :not(.cover) { display: none !important; }
.cover { margin: 0 !important; width: 210mm !important; height: 297mm !important; padding: 85mm 22mm 0 !important; page-break-after: auto !important; }
.cover .for { left: 22mm !important; right: 22mm !important; bottom: 26mm !important; }
"""
NO_COVER = ".cover { display: none !important; }"

tmp = Path(tempfile.mkdtemp())
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(channel="msedge", headless=True)
    except Exception:
        browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(SRC.as_uri())
    page.wait_for_load_state("networkidle")
    broken = page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src'))")
    if broken:
        raise SystemExit(f"Missing images: {broken}")

    page.add_style_tag(content=COVER_ONLY)
    page.pdf(path=str(tmp / "cover.pdf"), prefer_css_page_size=True, print_background=True)

    page.reload(); page.wait_for_load_state("networkidle")
    page.add_style_tag(content=NO_COVER)
    page.pdf(
        path=str(tmp / "body.pdf"), format="A4", print_background=True, display_header_footer=True,
        header_template="<span></span>", footer_template=FOOTER,
        margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
    )
    browser.close()

cover, body = pymupdf.open(str(tmp / "cover.pdf")), pymupdf.open(str(tmp / "body.pdf"))
if len(cover) != 1:
    raise SystemExit(f"Cover should be exactly 1 page, got {len(cover)}")
out = pymupdf.open()
out.insert_pdf(cover)
out.insert_pdf(body)
out.set_metadata({"title": "SmartWaste AI - Setup and User Guide", "subject": "Installation, user guide and administrator guide"})
out.save(str(OUT), garbage=3, deflate=True)
print(f"Wrote {OUT} ({out.page_count} pages, {OUT.stat().st_size / 1e6:.1f} MB)")
