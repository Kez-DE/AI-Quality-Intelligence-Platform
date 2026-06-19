"""Cào chính sách/hỗ trợ công khai greensm.com bằng Firecrawl docker (localhost:3002).
Output: file .md thô vào /tmp/public_scrape/ để bước sau dựng thành public KB.
Chỉ chạy thủ công khi cần refresh data — KHÔNG phải module runtime."""
import json
import os
import re
import time
import urllib.request

FIRECRAWL = "http://localhost:3002"
OUT_DIR = "/tmp/public_scrape"

# Trang chính sách/hỗ trợ công khai (nguồn: greensm.com/vn-vi).
SEED_URLS = [
    "https://www.greensm.com/vn-vi/helps",
    "https://www.greensm.com/vn-vi/terms-policies",
    "https://www.greensm.com/vn-vi/terms-policies/consumer-protection-policy",
    "https://www.greensm.com/vn-vi/terms-policies/privacy-notice",
]


def _post(path: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{FIRECRAWL}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def scrape(url: str) -> dict:
    """Scrape 1 URL -> {markdown, links, title}."""
    try:
        res = _post("/v1/scrape", {
            "url": url,
            "formats": ["markdown", "links"],
            "onlyMainContent": True,
        })
        d = res.get("data", {})
        return {
            "url": url,
            "markdown": d.get("markdown", ""),
            "links": d.get("links", []),
            "title": (d.get("metadata") or {}).get("title", url),
        }
    except Exception as e:
        print(f"  [ERR] {url}: {str(e)[:150]}")
        return {"url": url, "markdown": "", "links": [], "title": url}


def discover_help_links(seed_result: dict) -> list[str]:
    """Lọc các link FAQ/help/policy con từ trang helps."""
    found = set()
    for link in seed_result.get("links", []):
        if not isinstance(link, str):
            continue
        # chỉ giữ link nội bộ greensm vn-vi thuộc help/terms
        if "greensm.com/vn-vi" in link and re.search(r"/(helps|terms-policies)(/|$|\?)", link):
            # bỏ query, fragment
            clean = link.split("#")[0].split("?")[0].rstrip("/")
            found.add(clean)
    return sorted(found)


def _slug(url: str) -> str:
    tail = url.rstrip("/").split("/vn-vi/")[-1]
    return re.sub(r"[^a-z0-9]+", "_", tail.lower()).strip("_") or "index"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_urls = list(SEED_URLS)

    # B1: cào seed + khám phá link con từ trang helps
    print("=== B1: cào seed + khám phá link con ===")
    help_seed = scrape(SEED_URLS[0])
    discovered = discover_help_links(help_seed)
    print(f"  Phát hiện {len(discovered)} link con từ /helps")
    for u in discovered:
        if u not in all_urls:
            all_urls.append(u)

    # B2: cào toàn bộ
    print(f"\n=== B2: cào {len(all_urls)} trang ===")
    manifest = []
    for i, url in enumerate(all_urls, 1):
        # seed[0] đã cào rồi
        r = help_seed if url == SEED_URLS[0] else scrape(url)
        md = r.get("markdown", "")
        if len(md.strip()) < 100:
            print(f"  [{i}/{len(all_urls)}] SKIP (rỗng): {url}")
            continue
        slug = _slug(url)
        fpath = os.path.join(OUT_DIR, f"{slug}.md")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"<!-- source_url: {url} -->\n")
            f.write(f"<!-- title: {r.get('title','')} -->\n\n")
            f.write(md)
        manifest.append({"url": url, "slug": slug, "title": r.get("title", ""), "chars": len(md)})
        print(f"  [{i}/{len(all_urls)}] OK ({len(md)} chars): {slug}")
        if url != SEED_URLS[0]:
            time.sleep(1)  # nhẹ tay với server

    with open(os.path.join(OUT_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n=== XONG: {len(manifest)} file vào {OUT_DIR} ===")


if __name__ == "__main__":
    main()
