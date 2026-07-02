"""Cào chính sách Be/Grab CHỈ để tham khảo mẫu quy trình ngành khi soạn SOP.

Output: /tmp/competitor_scrape/ — KHÔNG commit, KHÔNG đưa vào data/. Guardrail: số liệu
và liên hệ của Be/Grab TUYỆT ĐỐI không được copy vào KB xanhSM (chỉ mượn pattern quy trình).
Chạy thủ công khi cần. Tolerant với URL 404/chặn.
"""
import json
import os

from scrape_public_policy import scrape  # tái dùng client Firecrawl

OUT_DIR = "/tmp/competitor_scrape"

SEED_URLS = [
    # Be
    "https://www.be.com.vn/dieu-khoan-su-dung",
    "https://www.be.com.vn/chinh-sach-quyen-rieng-tu",
    "https://www.be.com.vn/quy-che-hoat-dong",
    # Grab
    "https://help.grab.com/passenger/vi-vn/",
    "https://www.grab.com/vn/terms-policies/",
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = []
    for i, url in enumerate(SEED_URLS, 1):
        r = scrape(url)
        md = r.get("markdown", "")
        if len(md.strip()) < 100:
            print(f"  [{i}/{len(SEED_URLS)}] SKIP (rỗng/chặn): {url}")
            continue
        slug = f"ref_{i:02d}"
        with open(os.path.join(OUT_DIR, f"{slug}.md"), "w", encoding="utf-8") as f:
            f.write(f"<!-- REFERENCE ONLY — competitor, KHÔNG copy số/liên hệ vào KB -->\n")
            f.write(f"<!-- source_url: {url} -->\n\n{md}")
        manifest.append({"url": url, "slug": slug, "chars": len(md)})
        print(f"  [{i}/{len(SEED_URLS)}] OK ({len(md)} chars): {url}")
    with open(os.path.join(OUT_DIR, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n=== XONG: {len(manifest)} trang tham khảo vào {OUT_DIR} ===")


if __name__ == "__main__":
    main()
