#!/usr/bin/env python3
"""Download Shape Up chapter images and source snapshots for translation work."""

from __future__ import annotations

import json
import posixpath
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SNAPSHOTS = ROOT / "source_snapshots" / "shapeup"
BASE_URL = "https://basecamp.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) ShapeUpTranslation/1.0"


@dataclass(frozen=True)
class Page:
    url_path: str
    md_path: str
    title: str


PAGES = [
    Page("/shapeup/0.1-foreword", "preface/foreword.md", "Foreword"),
    Page("/shapeup/0.2-acknowledgements", "preface/acknowledgements.md", "Acknowledgements"),
    Page("/shapeup/0.3-chapter-01", "abstraction/abstraction.md", "Introduction"),
    Page("/shapeup/1.1-chapter-02", "partone/principles_of_shaping.md", "Principles of Shaping"),
    Page("/shapeup/1.2-chapter-03", "partone/set_boundaries.md", "Set Boundaries"),
    Page("/shapeup/1.3-chapter-04", "partone/find_the_elements.md", "Find the Elements"),
    Page("/shapeup/1.4-chapter-05", "partone/risks_and_rabbit_holes.md", "Risks and Rabbit Holes"),
    Page("/shapeup/1.5-chapter-06", "partone/write_the_pitch.md", "Write the Pitch"),
    Page("/shapeup/2.1-chapter-07", "parttwo/bets_not_backlogs.md", "Bets, Not Backlogs"),
    Page("/shapeup/2.2-chapter-08", "parttwo/the_betting_table.md", "The Betting Table"),
    Page("/shapeup/2.3-chapter-09", "parttwo/place_your_bets.md", "Place Your Bets"),
    Page("/shapeup/3.1-chapter-10", "partthree/hand_over_responsibility.md", "Hand Over Responsibility"),
    Page("/shapeup/3.2-chapter-11", "partthree/get_one_piece_done.md", "Get One Piece Done"),
    Page("/shapeup/3.3-chapter-12", "partthree/map_the_scopes.md", "Map the Scopes"),
    Page("/shapeup/3.4-chapter-13", "partthree/show_progress.md", "Show Progress"),
    Page("/shapeup/3.5-chapter-14", "partthree/decide_when_to_stop.md", "Decide When to Stop"),
    Page("/shapeup/3.6-chapter-15", "partthree/move_on.md", "Move On"),
    Page("/shapeup/3.7-conclusion", "partthree/conclusion.md", "Conclusion"),
    Page("/shapeup/4.0-appendix-01", "appendices/implement_shapeup_in_basecamp.md", "How to Implement Shape Up in Basecamp"),
    Page("/shapeup/4.1-appendix-02", "appendices/adjust_to_your_size.md", "Adjust to Your Size"),
    Page("/shapeup/4.2-appendix-03", "appendices/how_to_begin.md", "How to Begin to Shape Up"),
    Page("/shapeup/4.5-appendix-06", "appendices/glossary.md", "Glossary"),
    Page("/shapeup/4.6-appendix-07", "appendices/about_author.md", "About the Author"),
]


def request_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def page_slug(page: Page) -> str:
    return page.url_path.rsplit("/", 1)[-1]


def localize_image(src: str, page: Page, md_path: str) -> str:
    url = urllib.parse.urljoin(BASE_URL, src)
    parsed = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name or "image.png"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")
    dest_dir = DOCS / "assets" / "images" / "shapeup" / page_slug(page)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / safe_name
    if not dest.exists():
        dest.write_bytes(request_bytes(url))
    src_parent = (DOCS / md_path).parent.relative_to(DOCS).as_posix()
    return posixpath.relpath(dest.relative_to(DOCS).as_posix(), src_parent or ".")


def extract_page(page: Page) -> dict[str, object]:
    html = request_bytes(urllib.parse.urljoin(BASE_URL, page.url_path))
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("div.content")
    if content is None:
        raise RuntimeError(f"No content found for {page.url_path}")

    for tag in content.select("template, nav.pagination, footer.footer, script, style"):
        tag.decompose()

    images = []
    for img in content.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        local_src = localize_image(src, page, page.md_path)
        images.append({"source": urllib.parse.urljoin(BASE_URL, src), "local": local_src})
        img["src"] = local_src

    markdown = markdownify(str(content), heading_style="ATX", bullets="-")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return {
        "title": page.title,
        "url": urllib.parse.urljoin(BASE_URL, page.url_path),
        "target": page.md_path,
        "images": images,
        "markdown": markdown,
    }


def main() -> int:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    manifest = []
    for page in PAGES:
        print(f"Syncing {page.url_path}", flush=True)
        data = extract_page(page)
        snapshot_path = SNAPSHOTS / f"{page_slug(page)}.md"
        snapshot_path.write_text(str(data["markdown"]) + "\n", encoding="utf-8")
        manifest.append({k: data[k] for k in ("title", "url", "target", "images")})
    (SNAPSHOTS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
