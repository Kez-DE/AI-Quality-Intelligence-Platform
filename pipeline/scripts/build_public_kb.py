"""Dựng bộ public KB cho khách từ data cào greensm.com (/tmp/public_scrape).
Chỉ lấy FAQ CÓ câu trả lời thật; mục trống chỉ ghi tiêu đề + hướng tới kênh hỗ trợ.
Output: data/public_kb/*.md có frontmatter (audience: public)."""
import os
import re

SCRAPE_DIR = "/tmp/public_scrape"
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT_DIR = os.path.join(REPO, "data", "public_kb")
SOURCE_URL = "https://www.greensm.com/vn-vi/helps"

FAQ_RE = re.compile(r"^(\d+)\.(\d+)\.\s+(.*)$")
# Nhóm chủ đề theo số mục đầu (khớp các section của trang helps)
SECTIONS = {
    "1": ("an_toan", "An toàn & sự cố", "Safety"),
    "2": ("dat_xe_dich_vu", "Đặt xe & dịch vụ", "Vận hành"),
    "3": ("cuoc_phi_thanh_toan", "Cước phí & thanh toán", "CSKH"),
    "4": ("khuyen_mai_uu_dai", "Khuyến mãi & ưu đãi", "Marketing"),
    "5": ("tai_khoan", "Tài khoản", "CSKH"),
    "6": ("ho_tro_phan_hoi", "Hỗ trợ & phản hồi", "CSKH"),
}


def parse_faqs(md: str):
    """Trả [(sec, sub, title, answer)] — answer='' nếu mục trống (accordion chưa load)."""
    lines = md.splitlines()
    items = []
    i = 0
    while i < len(lines):
        m = FAQ_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        sec, sub, title = m.group(1), m.group(2), m.group(3).strip()
        # gom các dòng nội dung tới khi gặp FAQ heading kế tiếp / section heading / separator
        ans_lines = []
        j = i + 1
        while j < len(lines):
            ln = lines[j].strip()
            if FAQ_RE.match(ln) or re.match(r"^\d+\.\s+\S", ln) or ln == "* * *":
                break
            if ln:
                ans_lines.append(ln)
            j += 1
        answer = " ".join(ans_lines).strip()
        # lọc câu trả lời rác (quá ngắn)
        items.append((sec, sub, title, answer if len(answer) > 50 else ""))
        i = j
    return items


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    helps = open(os.path.join(SCRAPE_DIR, "helps.md"), encoding="utf-8").read()
    faqs = parse_faqs(helps)

    # gom theo section
    by_sec = {}
    for sec, sub, title, ans in faqs:
        by_sec.setdefault(sec, []).append((sub, title, ans))

    written = []
    for sec, (slug, label, dept) in SECTIONS.items():
        rows = by_sec.get(sec, [])
        if not rows:
            continue
        answered = [(s, t, a) for s, t, a in rows if a]
        empty = [(s, t) for s, t, a in rows if not a]

        body = [
            "---",
            f"document_title: Hỏi đáp khách hàng — {label} (Green SM/xanhSM)",
            "category: faq",
            "audience: public",
            f"topic_group: {dept}",
            f"source_url: {SOURCE_URL}",
            "source: greensm_help_center",
            "---",
            "",
            f"# Hỏi đáp khách hàng — {label}",
            "",
        ]
        for sub, title, ans in answered:
            body.append(f"## {sec}.{sub}. {title}")
            body.append("")
            body.append(ans)
            body.append("")
        if empty:
            body.append("## Các chủ đề khác trong nhóm này")
            body.append("")
            body.append("Với các vấn đề sau, vui lòng xem chi tiết trong mục Trung tâm hỗ trợ "
                        "trên ứng dụng Green SM, hoặc liên hệ Hotline 1555:")
            body.append("")
            for sub, title in empty:
                body.append(f"- {title}")
            body.append("")
        fpath = os.path.join(OUT_DIR, f"{slug}.md")
        open(fpath, "w", encoding="utf-8").write("\n".join(body))
        written.append((slug, len(answered), len(empty)))
        print(f"  {slug}.md: {len(answered)} câu trả lời, {len(empty)} mục chỉ-tiêu-đề")

    # File kênh hỗ trợ + quy trình khiếu nại (nội dung thật, luôn hữu ích)
    support = """---
document_title: Kênh hỗ trợ, phản hồi & khiếu nại cho khách hàng (Green SM/xanhSM)
category: faq
audience: public
topic_group: CSKH
source_url: https://www.greensm.com/vn-vi
source: greensm_help_center
---

# Kênh hỗ trợ, phản hồi & khiếu nại

## Cách gửi phản hồi, góp ý hoặc khiếu nại

Nếu bạn muốn phản ánh chất lượng chuyến đi, góp ý về dịch vụ/ứng dụng, hoặc khiếu nại,
bạn có thể dùng một trong các kênh chính thức sau:

- **Gửi yêu cầu hỗ trợ ngay trong ứng dụng Green SM** (mục Hỗ trợ / Trung tâm hỗ trợ).
- **Hotline 1555** — tổng đài chăm sóc khách hàng (đặt xe: 1555).
- **Email:** support.vn@greensm.com
- **Đánh giá sao cho tài xế** sau mỗi chuyến đi để phản hồi nhanh về chất lượng.

## Quy trình tiếp nhận & giải quyết khiếu nại

Theo Quy tắc bảo vệ quyền lợi người tiêu dùng của Green SM:

- Công ty áp dụng cơ chế giải quyết khiếu nại, tranh chấp theo quy định pháp luật.
- Yêu cầu của khách hàng được chuyển đến đúng cấp có thẩm quyền để giải quyết trong
  thời gian sớm nhất có thể.
- Khách hàng là người tiêu dùng dễ bị tổn thương (người cao tuổi, người khuyết tật,
  phụ nữ mang thai, trẻ em…) được **ưu tiên** tiếp nhận và xử lý trước.
- Trường hợp từ chối giải quyết, công ty sẽ phản hồi bằng văn bản, nêu rõ căn cứ.

## Quyền của khách hàng về dữ liệu cá nhân

Bạn có quyền: được biết về việc xử lý thông tin của mình; đồng ý/không đồng ý cho phép
xử lý; truy cập, chỉnh sửa; rút lại sự đồng ý; xóa thông tin; khiếu nại, tố cáo, khởi kiện
theo quy định pháp luật. Liên hệ các kênh trên để thực hiện các quyền này.
"""
    open(os.path.join(OUT_DIR, "ho_tro_khieu_nai.md"), "w", encoding="utf-8").write(support)
    written.append(("ho_tro_khieu_nai", "manual", 0))
    print("  ho_tro_khieu_nai.md: nội dung thật (kênh hỗ trợ + quy trình khiếu nại)")

    print(f"\n=== XONG: {len(written)} file public KB vào data/public_kb/ ===")


if __name__ == "__main__":
    build()
