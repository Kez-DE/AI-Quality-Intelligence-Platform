# Green SM 10-Minute Pitch Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo bộ pitch 10 phút cho AI Quality Intelligence Platform (Green SM): 1 file `.pptx` 12 slide + 1 file HTML kịch bản nói từng slide.

**Architecture:** Deck mới sinh bằng script Python (python-pptx) từ một cấu trúc dữ liệu SLIDES duy nhất; ảnh gồm screenshot UI thật trích từ deck 20-slide cũ + ảnh Green SM tải từ web. Kịch bản HTML tái dùng nguyên CSS của file v4 tham chiếu, thay phần nội dung.

**Tech Stack:** Python 3 + python-pptx (chạy qua `uv run --with python-pptx`), curl để tải ảnh, HTML/CSS tĩnh.

## Global Constraints

- Cấu trúc 10 phút: **3 phút bài toán (S1–S4) / 5 phút sản phẩm (S5–S10) / 2 phút kết (S11–S12)**. KHÔNG có slide gọi vốn.
- Khổ slide 16:9 (13.333 × 7.5 inch), tiếng Việt, mỗi slide có speaker notes.
- Thương hiệu: dùng tên **Green SM** (tên mới của Xanh SM); màu chủ đạo xanh `#0E7C55`, nền trắng `#FFFFFF`, chữ `#171D1A`, phụ `#5B655F`.
- Số liệu chỉ dùng số THẬT đã kiểm chứng: App Store VN **4.8★ / 1,5 triệu đánh giá**; ra mắt 14/04/2023; 34 tỉnh thành; 4 quốc gia (VN, Lào, Philippines, Indonesia); pipeline: **77%** topic, **94%+** sentiment, **97%** recall negative, **~5.000 review < 2 phút**, **6/6** test case.
- Ẩn dụ xuyên suốt phần sản phẩm: **phòng cấp cứu** (giữ nguyên từ kịch bản v4).
- Output: `docs/project/slides/GreenSM-Pitch-10min.pptx`, `docs/project/slides/GreenSM-pitch-script.html`, ảnh trong `docs/project/slides/assets/pitch/`.
- File tham chiếu CSS kịch bản: `/Users/kenz_de/AI_20k slide /xanhSM-presentation-script-v4.html` (chú ý dấu cách cuối tên thư mục `AI_20k slide `).

---

### Task 1: Chuẩn bị ảnh (assets)

**Files:**
- Create: `docs/project/slides/assets/pitch/` (thư mục ảnh)
- Create: `scripts/slides/fetch_pitch_assets.sh`

**Interfaces:**
- Produces: các file ảnh với tên ngữ nghĩa mà Task 3 nhúng vào pptx:
  `ui-dashboard.png`, `ui-feedback.png`, `ui-ticket.png`, `ui-report.png`, `ui-tasks.png`, `ui-chat.png`, `greensm-photo.jpg` (ảnh xe/tài xế Green SM thật, ≥1200px ngang), `appstore-rating.png` (nếu chụp được).

- [ ] **Step 1: Trích screenshot UI từ deck cũ**

```bash
mkdir -p docs/project/slides/assets/pitch /tmp/pitch-media
unzip -o -j 'docs/project/slides/AI-Quality-Intelligence-Platform-Overview.pptx' 'ppt/media/*' -d /tmp/pitch-media
ls /tmp/pitch-media
```

Expected: 15 file PNG (image-1-2, image-4-1, image-7-1 … image-19-1, Slide-1/20).

- [ ] **Step 2: Xem từng ảnh bằng tool Read và đổi tên ngữ nghĩa**

Mở lần lượt các file `/tmp/pitch-media/image-*.png` bằng tool Read (ảnh hiển thị trực quan). Đối chiếu README deck cũ (Dashboard, Phản hồi, Phân loại Ticket, Báo cáo AI, Quản lý công việc, AI Chat) rồi copy sang tên mới:

```bash
# ví dụ sau khi nhìn ảnh — chỉnh nguồn cho đúng ảnh đã nhận diện:
cp /tmp/pitch-media/image-7-1.png  docs/project/slides/assets/pitch/ui-dashboard.png
cp /tmp/pitch-media/image-8-1.png  docs/project/slides/assets/pitch/ui-feedback.png
cp /tmp/pitch-media/image-10-1.png docs/project/slides/assets/pitch/ui-ticket.png
cp /tmp/pitch-media/image-15-1.png docs/project/slides/assets/pitch/ui-report.png
cp /tmp/pitch-media/image-13-1.png docs/project/slides/assets/pitch/ui-tasks.png
cp /tmp/pitch-media/image-17-1.png docs/project/slides/assets/pitch/ui-chat.png
```

Expected: 6 file `ui-*.png` tồn tại, mỗi file đúng màn hình như tên.

- [ ] **Step 3: Tải ảnh Green SM thật từ web**

Thứ tự thử (dừng khi có ảnh đạt yêu cầu ≥1200px ngang, chụp xe taxi điện Green SM):

```bash
# 1) Ảnh og:image / hero từ trang chủ chính thức
curl -sL 'https://www.xanhsm.com/vi-EN' -o /tmp/xanhsm.html
grep -oE 'https://[^"]+\.(jpg|jpeg|png|webp)' /tmp/xanhsm.html | head -20
# tải ứng viên đầu tiên trông giống ảnh hero/xe:
curl -sL '<URL-ảnh-chọn-được>' -o docs/project/slides/assets/pitch/greensm-photo.jpg
# 2) Fallback: dùng WebSearch tìm "Green SM taxi điện ảnh báo chí press photo"
#    rồi curl ảnh từ bài báo (vnexpress/tuoitre/vinfast newsroom).
sips -g pixelWidth docs/project/slides/assets/pitch/greensm-photo.jpg
```

Expected: `pixelWidth ≥ 1200`. Mở ảnh bằng Read xác nhận đúng xe/tài xế Green SM.

- [ ] **Step 4: Tạo ảnh bằng chứng App Store**

Chụp không được trang App Store bằng CLI, nên dựng "thẻ bằng chứng" bằng chính pptx ở Task 3 (khối số 4.8★ / 1,5M có chú nguồn). Bước này chỉ cần ghi lại nguồn vào file text:

```bash
cat > docs/project/slides/assets/pitch/SOURCES.md <<'EOF'
- App Store VN (Green SM: Electric Mobility, id6446425595): 4.8★, 1.5M ratings — truy cập 2026-07-06
  https://apps.apple.com/vn/app/green-sm-electric-mobility/id6446425595
- Ra mắt 14/04/2023; 34 tỉnh thành; 4 quốc gia (VN, Lào, Philippines, Indonesia) — xanhsm.com
- greensm-photo.jpg tải từ: <URL đã dùng ở Step 3>
EOF
```

Expected: file SOURCES.md có URL thật đã dùng.

- [ ] **Step 5: Lưu script fetch để tái lập + commit**

Gom các lệnh Step 1–4 (với URL cuối cùng đã chọn) vào `scripts/slides/fetch_pitch_assets.sh`, `chmod +x`, rồi:

```bash
git add docs/project/slides/assets/pitch scripts/slides/fetch_pitch_assets.sh
git commit -m "feat(slides): assets cho pitch deck Green SM 10 phút"
```

---

### Task 2: Kịch bản nói HTML (GreenSM-pitch-script.html)

**Files:**
- Create: `docs/project/slides/GreenSM-pitch-script.html`

**Interfaces:**
- Consumes: CSS copy nguyên khối `<style>…</style>` từ `/Users/kenz_de/AI_20k slide /xanhSM-presentation-script-v4.html` (dòng 7–236).
- Produces: kịch bản 12 section khớp 1:1 với 12 slide của Task 3 (số slide + mốc thời gian phải trùng speaker notes).

- [ ] **Step 1: Tạo file HTML với CSS v4 + nội dung kịch bản đầy đủ dưới đây**

Cấu trúc file: giữ nguyên khung `<html lang="vi">`, khối `<style>` copy verbatim từ file v4, phần `<body>` gồm: tiêu đề, tagline, ẩn dụ, TOC 12 mục, phần "Chuẩn bị trước khi lên", 12 section kịch bản, mẹo trình bày, Q&A. Nội dung nói từng slide (đặt trong `<blockquote>`, mốc thời gian trong `.meta-line`) **chính xác như sau**:

**S1 · Hook (0:00–0:40)**
> **2 giờ sáng.** Một tài xế lái ẩu, gây nguy hiểm cho khách. Cùng lúc đó, hàng chục người đã viết review than phiền về đúng tài xế này — trong nhiều tuần. Không ai đọc. Không ai ghép các mảnh lại. **Không ai biết.**
> Đây không phải chuyện bịa. Trên App Store, ứng dụng Green SM — tên mới của Xanh SM — đang có **4.8 sao với 1 triệu rưỡi lượt đánh giá**. Một con số đẹp. Nhưng hãy hỏi ngược lại: **một triệu rưỡi tiếng nói — ai đọc hết?**
> Sản phẩm này được xây để ca trực 2 giờ sáng đó không bao giờ đơn độc nữa.

*Cue: im lặng 2 giây khi slide hiện, để khán giả đọc con số 1,5 triệu trước.*

**S2 · Bằng chứng thật (0:40–1:40)**
> Đây là những review thật, đang nằm công khai trên App Store, ngay dưới điểm 4.8 sao ấy: một hành khách kể bị tài xế **hành hung**; một người khác không đăng nhập nổi app trên chính chiếc điện thoại của mình. Những dòng này không nằm trong báo cáo nào cả — chúng chìm giữa một triệu rưỡi đánh giá.
> Và quy mô thì chỉ tăng lên: Green SM ra mắt tháng 4 năm 2023, nay đã phủ **34 tỉnh thành, 4 quốc gia**. Mỗi ngày, hàng nghìn review mới đổ về từ App Store và Google Play.
> Điểm trung bình cao không có nghĩa là an toàn. **Rủi ro nằm ở phần đuôi — những ca nghiêm trọng lẫn trong đám đông hài lòng.**

**S3 · Ba lỗ hổng (1:40–2:30)**
> Tại sao chuyện đó xảy ra? Không phải thiếu dữ liệu — dữ liệu thừa mứa. Vấn đề là ba lỗ hổng.
> Một: **quá tải** — hàng nghìn review mỗi ngày, không đội ngũ nào đọc xuể bằng tay.
> Hai, nguy hiểm nhất: **an toàn bị bỏ sót** — review về tài xế say rượu trông y hệt review về app lag, cho đến khi có người đọc kỹ. Mà người đọc kỹ luôn đến sau.
> Ba: **sai địa chỉ** — vấn đề rơi vào hộp thư chung, ai cũng thấy nhưng không ai chịu trách nhiệm.

**S4 · Điều cần tồn tại (2:30–3:00)**
> Ba lỗ hổng, một kết luận. Cần một hệ thống **đọc thay con người, phân loại đúng mức độ khẩn cấp, và giao đúng người xử lý**. Và thời điểm là bây giờ: AI đọc hiểu tiếng Việt đã đủ tốt và đủ rẻ để đọc một triệu rưỡi review — điều mà ba năm trước còn là bất khả thi.
> Đó chính xác là những gì chúng tôi đã xây. Và nó đang chạy thật.

**S5 · Hành trình 7 chặng (3:00–3:50)**
> Hãy hình dung mỗi review như một **bệnh nhân bước vào phòng cấp cứu**. Không phải ai cũng cần bác sĩ trưởng khoa ngay, nhưng ai cũng phải được đánh giá ngay khi bước vào cửa.
> Hệ thống làm đúng việc đó qua bảy chặng: làm sạch thông tin nhạy cảm, đo "dấu hiệu sinh tồn" bằng AI, bác sĩ trực ghi đè khi thấy dấu hiệu nguy hiểm, phát hiện khi nhiều ca giống nhau dồn về, gọi đúng chuyên khoa, tự lập hồ sơ công việc, và cuối cùng — người có chuyên môn ký xác nhận.
> Nguyên tắc vận hành: phần rẻ và nhanh xử lý mọi ca; AI ngôn ngữ lớn chỉ được gọi khi cần suy luận sâu; **an toàn luôn thắng xác suất**; và một bộ phận trục trặc thì cả hệ thống vẫn đứng vững.

**S6 · Chặng 1–3: Làm sạch → AI đọc lướt → Luật an toàn ghi đè (3:50–4:50)**
> Bắt đầu từ cửa vào. Bước một: **che thông tin riêng tư** — số điện thoại, email, biển số — trước khi bất kỳ ai hay máy nào đọc. Bước hai: một **bộ phân loại AI nhanh và rẻ** gán chủ đề, cảm xúc, mức nghiêm trọng trong chưa đầy một phần mười giây — độ chính xác đo được: 77% chủ đề, hơn 94% cảm xúc. Bước ba: **tập luật an toàn** đóng vai bác sĩ trực, sẵn sàng ghi đè AI.
> Ví dụ thật, không dàn dựng: *"Tài xế say xỉn gây tai nạn, xe tông người rồi bỏ chạy."* AI đọc lướt đoán mức trung bình. Luật an toàn bắt được "tai nạn", "bỏ chạy" — **ghi đè ngay thành mức khẩn cấp cao nhất**, bắt buộc người thật phải xem.
> Điều quan trọng nhất của cả hệ thống: **khi nghi ngờ về an toàn, máy không được phép tự tin hơn sự thận trọng.**

**S7 · Chặng 4–5: Ổ dịch → Báo động → Đúng chuyên khoa (4:50–5:40)**
> Một ca đơn lẻ là cá biệt. Nhưng nhiều ca giống nhau dồn về cùng khu vực trong thời gian ngắn — đó là một **ổ dịch**. Hệ thống theo dõi liên tục: một ca khẩn cấp là báo ngay; nhiều ca cùng lúc là báo động đỏ; và nó tự biết chờ để không báo trùng lặp làm loãng tín hiệu.
> Báo động nổi lên thì gọi ai? Một **bảng phân khoa** quyết định: an toàn về đội vận hành trong vòng một giờ, lỗi app về kỹ thuật, thanh toán về chăm sóc khách hàng — đủ **sáu phòng ban**.
> Thực dụng nhất: đổi luật phân khoa chỉ cần sửa một tệp cấu hình — **không viết lại dòng code nào.**

**S8 · Chặng 6–7: Từ báo động đến việc thật — và con người quyết định (5:40–6:40)**
> Có báo động rồi — ai biến nó thành việc phải làm? Hai con đường. Đường **tự động**: hệ thống gom báo động cùng loại, tự lập đầu việc, không trùng, không rơi rớt. Đường **có người kiểm soát**: AI viết báo cáo đề xuất, quản lý đọc, chỉnh, bấm duyệt — công việc xuất hiện ngay trên bảng theo dõi. **Máy đề xuất. Người quyết định.**
> Và bốn tình huống bắt buộc người thật phải xem: mức khẩn cấp cao nhất, AI không chắc chắn, câu mập mờ, hoặc có người chủ động yêu cầu. Mỗi lần con người sửa AI đều được ghi sổ: ai sửa, sửa gì, lúc nào. **Sai một lần, sửa một lần, hệ thống thông minh hơn một chút.**

**S9 · Ai được thấy gì (6:40–7:20)**
> Một hệ thống đọc được toàn bộ tiếng nói khách hàng thì phải cực kỳ nghiêm ngặt về chuyện ai thấy gì. Hai câu hỏi luôn đi cùng nhau: bạn là **ai** — để biết được làm gì; bạn thuộc **phòng nào** — để biết được thấy dữ liệu của ai.
> Quản lý phòng kỹ thuật đăng nhập: thấy việc phòng mình, hỏi trợ lý AI cũng chỉ nhận câu trả lời trong phạm vi phòng mình. Cố mở dữ liệu phòng khác — kể cả gọi thẳng vào hệ thống, bỏ qua giao diện — câu trả lời luôn là: **không được phép**. Sự cho phép nằm ở lõi hệ thống, không phải cái nút bị ẩn đi.

**S10 · Bằng chứng — chạy thật, đo thật (7:20–8:00)**
> Nói thì dễ, nên đây là số đo được: nhận diện chủ đề **77%**; cảm xúc **hơn 94%** — và gần như không bỏ sót phản hồi tiêu cực nào: **97%**. Gần **5.000 review xử lý trong chưa đầy 2 phút**. **6 trên 6** tình huống kiểm thử — ca an toàn, ca gian lận, ca mập mờ — đều ra đúng kết quả.
> Đây không phải số chọn lọc để trình diễn — mọi con số tái lập được bằng bộ kiểm thử nằm trong mã nguồn.

**S11 · Chúng tôi biết mình đang ở đâu (8:00–8:50)**
> Phần này chúng tôi nói thẳng, vì biết rõ giới hạn là dấu hiệu của sự nghiêm túc. Một: quyền truy cập đang được khóa ở cửa chính — tầng ứng dụng; lớp khóa sâu ở tầng dữ liệu là bước tiếp theo, chúng tôi biết chính xác cần làm gì. Hai: dữ liệu hiện là tập cố định gần 5.000 review thật từ các cửa hàng ứng dụng — bước tiếp theo là nối ống dữ liệu sống hằng ngày, giữ nguyên phần xử lý.
> Ba — và đau nhất khi nhìn lại câu chuyện mở đầu: **báo động khẩn cấp hiện chỉ hiện trên màn hình web.** Người trực không mở máy lúc 2 giờ sáng thì vẫn lỡ. Bước tiếp theo: đẩy thẳng báo động vào điện thoại.

*Cue: giọng tự tin, không xin lỗi. Nhấn chậm câu "chỉ hiện trên màn hình web" — điểm chạm cảm xúc mạnh nhất.*

**S12 · Kết — Tầm nhìn (8:50–10:00)**
> Nhớ ca trực 2 giờ sáng đầu buổi không? Với hệ thống này: review vào, AI đọc và phân loại, báo động nổi đúng lúc, quản lý duyệt, nhân viên xử lý — vòng lặp khép kín, mỗi ngày, **không ai phải thức trắng đêm dò từng dòng review.**
> Tầm nhìn của chúng tôi không dừng ở một ứng dụng gọi xe. Mọi nền tảng tiêu dùng ở Việt Nam đều đang ngồi trên hàng triệu tiếng nói khách hàng chưa được lắng nghe. Trong 3 đến 5 năm tới, chúng tôi muốn hệ thống này trở thành **tầng lắng nghe tiêu chuẩn** cho các nền tảng ấy — nơi mọi lời phàn nàn đều được đọc, được định tuyến, và trở thành hành động.
> Vì **một lời phàn nàn không được đọc là một sự cố đang chờ xảy ra lần nữa.** Với chúng tôi — nó sẽ được đọc. Cảm ơn hội đồng. Chúng tôi sẵn sàng cho phần hỏi đáp.

Phần Q&A dự phòng: giữ nguyên 6 câu hỏi/đáp từ file v4 (bảo mật tầng dữ liệu, data thật/giả, vì sao ML nhỏ + LLM, luật vs AI mâu thuẫn, LLM sập, 6 test case có đủ không).

- [ ] **Step 2: Kiểm tra file mở được và khớp cấu trúc**

```bash
python3 -c "import html.parser,sys; p=html.parser.HTMLParser(); p.feed(open('docs/project/slides/GreenSM-pitch-script.html').read()); print('parse ok')"
grep -c '<h2 id="s' docs/project/slides/GreenSM-pitch-script.html
```

Expected: `parse ok` và `12` section slide. Mở file bằng trình duyệt (open …) xem render.

- [ ] **Step 3: Commit**

```bash
git add docs/project/slides/GreenSM-pitch-script.html
git commit -m "feat(slides): kịch bản nói 12 slide cho pitch Green SM 10 phút"
```

---

### Task 3: Sinh file PPTX (GreenSM-Pitch-10min.pptx)

**Files:**
- Create: `scripts/slides/build_greensm_pitch.py`
- Create (output): `docs/project/slides/GreenSM-Pitch-10min.pptx`

**Interfaces:**
- Consumes: ảnh `docs/project/slides/assets/pitch/*.png|jpg` (Task 1); nội dung/timing khớp kịch bản Task 2.
- Produces: pptx 12 slide 16:9, mỗi slide có notes = tóm tắt lời nói + mốc thời gian.

- [ ] **Step 1: Viết script sinh pptx**

`scripts/slides/build_greensm_pitch.py` — cấu trúc: hằng màu, 4 hàm layout (`slide_hook`, `slide_bullets`, `slide_split_img`, `slide_stats`), dữ liệu SLIDES, vòng lặp build. Nội dung text từng slide:

```python
#!/usr/bin/env python3
"""Sinh GreenSM-Pitch-10min.pptx — 12 slide / 10 phút. Chạy:
uv run --with python-pptx python scripts/slides/build_greensm_pitch.py"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

GREEN = RGBColor(0x0E, 0x7C, 0x55)
INK   = RGBColor(0x17, 0x1D, 0x1A)
MUTED = RGBColor(0x5B, 0x65, 0x5F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
A = "docs/project/slides/assets/pitch"

prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def txt(slide, x, y, w, h, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line; p.alignment = align
        for r in p.runs: r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color
    return tb

def kicker(slide, label):          # nhãn phần nhỏ phía trên tiêu đề
    txt(slide, 0.6, 0.35, 8, 0.4, label, 13, GREEN, bold=True)

def title(slide, text, size=32):
    txt(slide, 0.6, 0.75, 12.1, 1.0, text, size, INK, bold=True)

def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s

def pic_fit(slide, path, x, y, w):  # ảnh giữ tỉ lệ theo bề ngang
    if os.path.exists(path): slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))

def stat(slide, x, y, big, small):
    txt(slide, x, y, 3.0, 1.0, big, 44, GREEN, bold=True)
    txt(slide, x, y+0.85, 3.0, 0.6, small, 14, MUTED)

def bullets(slide, items, x=0.7, y=1.9, w=12.0, size=20, gap=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(5.2))
    tf = tb.text_frame; tf.word_wrap = True
    for i, (head, body) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(14)
        r = p.add_run(); r.text = "▪ " + head + "  "; r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = INK
        r2 = p.add_run(); r2.text = body; r2.font.size = Pt(size - 2); r2.font.color.rgb = MUTED

# ---- S1 HOOK ----
s = prs.slides.add_slide(BLANK)
pic_fit(s, f"{A}/greensm-photo.jpg", 6.9, 0, 6.45)          # ảnh phải, full-bleed dọc
txt(s, 0.6, 0.5, 6.0, 0.5, "AI QUALITY INTELLIGENCE PLATFORM", 13, GREEN, bold=True)
txt(s, 0.6, 1.3, 6.1, 2.2, "2 GIỜ SÁNG.\nAI ĐANG ĐỌC\nREVIEW CỦA BẠN?", 40, INK, bold=True)
stat(s, 0.6, 4.0, "4.8★", "App Store Việt Nam")
stat(s, 3.4, 4.0, "1,5 TRIỆU", "lượt đánh giá — ai đọc hết?")
txt(s, 0.6, 5.6, 6.1, 1.2, "AI Quality Intelligence Platform cho Green SM\nBiến 1,5 triệu tiếng nói thành hành động — tự động, có kiểm soát.", 16, MUTED)
notes(s, "0:00–0:40 · Im lặng 2s. Câu chuyện 2 giờ sáng → con số 4.8★/1,5 triệu → 'ai đọc hết?' → giới thiệu sản phẩm.")

# ---- S2 BẰNG CHỨNG THẬT ----
s = prs.slides.add_slide(BLANK)
kicker(s, "PHẦN 1 · BÀI TOÁN"); title(s, "Điểm cao không có nghĩa là an toàn")
for i, (q, tag) in enumerate([
    ("“Tài xế có hành vi hành hung hành khách…”", "Review thật · App Store"),
    ("“Không đăng nhập được app trên máy của tôi.”", "Review thật · App Store"),
    ("“Tài xế say xỉn gây tai nạn, xe tông người rồi bỏ chạy.”", "Review thật · dữ liệu dự án"),
]):
    box = s.shapes.add_textbox(Inches(0.7), Inches(1.9 + i*1.15), Inches(7.3), Inches(1.0))
    tf = box.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; r = p.add_run(); r.text = q; r.font.size = Pt(18); r.font.italic = True; r.font.color.rgb = INK
    p2 = tf.add_paragraph(); r2 = p2.add_run(); r2.text = tag; r2.font.size = Pt(12); r2.font.color.rgb = GREEN
stat(s, 8.6, 2.0, "34", "tỉnh thành phủ sóng")
stat(s, 10.9, 2.0, "4", "quốc gia")
stat(s, 8.6, 3.7, "1000+", "review mới mỗi ngày")
txt(s, 8.6, 5.3, 4.2, 1.2, "Ca nghiêm trọng chìm giữa\nđám đông hài lòng.", 16, INK, bold=True)
notes(s, "0:40–1:40 · Đọc 2 review thật trên App Store, nhấn: chúng nằm ngay dưới điểm 4.8★. Quy mô 34 tỉnh/4 quốc gia → rủi ro ở phần đuôi.")

# ---- S3 BA LỖ HỔNG ----
s = prs.slides.add_slide(BLANK)
kicker(s, "PHẦN 1 · BÀI TOÁN"); title(s, "Ba lỗ hổng khiến 2 giờ sáng đơn độc")
bullets(s, [
    ("Quá tải.", "Hàng nghìn review/ngày — không đội ngũ nào đọc xuể bằng tay."),
    ("An toàn bị bỏ sót.", "Review 'tài xế say rượu' trông y hệt review 'app lag' — cho đến khi có người đọc kỹ. Người đọc kỹ luôn đến sau."),
    ("Sai địa chỉ.", "Vấn đề rơi vào hộp thư chung: ai cũng thấy, không ai chịu trách nhiệm."),
], y=2.1, size=22)
notes(s, "1:40–2:30 · Không phải thiếu dữ liệu — dữ liệu thừa mứa. Nhấn lỗ hổng 2 là nguy hiểm nhất.")

# ---- S4 ĐIỀU CẦN TỒN TẠI ----
s = prs.slides.add_slide(BLANK)
kicker(s, "PHẦN 1 · BÀI TOÁN"); title(s, "Điều cần tồn tại — và vì sao là bây giờ")
txt(s, 0.7, 2.2, 12.0, 1.6, "Một hệ thống ĐỌC THAY con người,\nPHÂN LOẠI đúng mức khẩn cấp, GIAO ĐÚNG NGƯỜI xử lý.", 30, GREEN, bold=True)
bullets(s, [
    ("Why now:", "AI đọc hiểu tiếng Việt đã đủ tốt và đủ rẻ để đọc 1,5 triệu review — 3 năm trước còn bất khả thi."),
    ("Và nó không phải ý tưởng:", "hệ thống đã chạy thật — 5 phút tiếp theo là bằng chứng."),
], y=4.3, size=20)
notes(s, "2:30–3:00 · Chốt phần bài toán bằng 1 câu giải pháp; bridge sang phần sản phẩm.")

# ---- S5 HÀNH TRÌNH 7 CHẶNG ----
s = prs.slides.add_slide(BLANK)
kicker(s, "PHẦN 2 · SẢN PHẨM"); title(s, "Phòng cấp cứu cho review — hành trình 7 chặng")
steps = ["① Che thông tin\nnhạy cảm", "② AI đọc lướt\n(topic·cảm xúc·mức độ)", "③ Luật an toàn\nghi đè", "④ Phát hiện\nổ dịch", "⑤ Định tuyến\n6 phòng ban", "⑥ Lập việc\ntự động/duyệt", "⑦ Người ký\nxác nhận"]
for i, st_ in enumerate(steps):
    x = 0.45 + i * 1.82
    box = s.shapes.add_textbox(Inches(x), Inches(2.5), Inches(1.72), Inches(1.6))
    tf = box.text_frame; tf.word_wrap = True
    for j, line in enumerate(st_.split("\n")):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = line; r.font.size = Pt(13 if j else 15); r.font.bold = (j == 0)
        r.font.color.rgb = GREEN if j == 0 else MUTED
bullets(s, [
    ("Rẻ chạy trước:", "ML nhỏ xử lý mọi review; LLM chỉ gọi khi cần suy luận sâu."),
    ("An toàn thắng xác suất.", "Luật an toàn luôn ghi đè được AI."),
    ("Đổi luật = sửa 1 file cấu hình.", "Một khối hỏng, hệ thống vẫn đứng."),
], y=4.7, size=17)
notes(s, "3:00–3:50 · Giới thiệu ẩn dụ phòng cấp cứu; lướt 7 chặng; 4 nguyên tắc vận hành.")

# ---- S6..S9: split ảnh phải ----
def split_slide(kick, ttl, items, img, note):
    s = prs.slides.add_slide(BLANK)
    kicker(s, kick); title(s, ttl, size=28)
    bullets(s, items, x=0.7, y=1.9, w=6.6, size=17)
    pic_fit(s, img, 7.6, 1.7, 5.4)
    notes(s, note); return s

split_slide("PHẦN 2 · SẢN PHẨM", "Chặng 1–3 · Làm sạch → AI đọc lướt → Luật ghi đè", [
    ("Che PII trước tiên.", "SĐT, email, biển số — trước khi người hay máy đọc."),
    ("AI nhanh & rẻ, <0,1s/review.", "77% chủ đề · 94%+ cảm xúc."),
    ("Ví dụ thật:", "“Tài xế say xỉn gây tai nạn… bỏ chạy” — AI đoán mức trung bình, luật an toàn GHI ĐÈ → khẩn cấp cao nhất, bắt buộc người xem."),
    ("Nguyên tắc:", "khi nghi ngờ an toàn, máy không được tự tin hơn sự thận trọng."),
], f"{A}/ui-feedback.png", "3:50–4:50 · Đi chậm ở ví dụ thật; chỉ vào screenshot màn Phản hồi.")

split_slide("PHẦN 2 · SẢN PHẨM", "Chặng 4–5 · Ổ dịch → Báo động → Đúng chuyên khoa", [
    ("1 ca là cá biệt — nhiều ca cùng nơi, cùng lúc là Ổ DỊCH.", "Theo dõi liên tục, tự chờ để không báo trùng."),
    ("Bảng phân khoa 6 phòng ban.", "An toàn → vận hành trong 1 giờ; lỗi app → kỹ thuật; thanh toán → CSKH."),
    ("Đổi luật phân khoa = sửa 1 file cấu hình.", "Không viết lại dòng code nào."),
], f"{A}/ui-ticket.png", "4:50–5:40 · Chỉ màn Phân loại ticket; nhấn câu 'không viết lại code'.")

split_slide("PHẦN 2 · SẢN PHẨM", "Chặng 6–7 · Từ báo động đến việc thật — người quyết định", [
    ("Đường tự động:", "gom báo động cùng loại → tự lập đầu việc, không trùng, không rơi rớt."),
    ("Đường có kiểm soát:", "AI viết báo cáo đề xuất → quản lý sửa & bấm duyệt → việc xuất hiện trên bảng."),
    ("MÁY ĐỀ XUẤT. NGƯỜI QUYẾT ĐỊNH.", "4 tình huống bắt buộc người xem; mọi lần sửa đều ghi sổ — hệ thống học từ từng lần sửa."),
], f"{A}/ui-report.png", "5:40–6:40 · Màn Báo cáo AI + bảng công việc; câu đinh: máy đề xuất, người quyết định.")

split_slide("PHẦN 2 · SẢN PHẨM", "Ai được thấy gì — phân quyền ở lõi hệ thống", [
    ("Bạn là AI → được làm gì.", "4 vai trò: Khách · Nhân viên · Quản lý · Admin."),
    ("Bạn thuộc PHÒNG NÀO → thấy dữ liệu của ai.", "Chatbot cũng chỉ trả lời trong phạm vi phòng."),
    ("Đi vòng qua giao diện, gọi thẳng hệ thống?", "Vẫn: KHÔNG ĐƯỢC PHÉP. Quyền nằm ở lõi, không phải nút bị ẩn."),
], f"{A}/ui-chat.png", "6:40–7:20 · Màn AI Chat 2 vai trò; nhấn 'quyền ở lõi hệ thống'.")

# ---- S10 BẰNG CHỨNG SỐ ----
s = prs.slides.add_slide(BLANK)
kicker(s, "PHẦN 2 · SẢN PHẨM"); title(s, "Chạy thật, đo thật — không phải số trình diễn")
for i, (big, small) in enumerate([
    ("77%", "đúng chủ đề"), ("94%+", "đúng cảm xúc"), ("97%", "không bỏ sót\nphản hồi tiêu cực"),
    ("<2 phút", "xử lý ~5.000 review"), ("6/6", "kịch bản kiểm thử đạt"),
]):
    stat(s, 0.7 + (i % 3) * 4.2, 2.2 + (i // 3) * 2.3, big, small)
txt(s, 0.7, 6.5, 12.0, 0.6, "Mọi con số tái lập được bằng bộ kiểm thử trong mã nguồn.", 16, INK, bold=True)
notes(s, "7:20–8:00 · Đọc chậm từng số, câu đời thường trước – phần trăm sau.")

# ---- S11 HẠN CHẾ & ROADMAP ----
s = prs.slides.add_slide(BLANK)
kicker(s, "PHẦN 3 · KẾT"); title(s, "Chúng tôi biết mình đang ở đâu")
bullets(s, [
    ("Khóa sâu tầng dữ liệu.", "Cửa chính (tầng ứng dụng) đã gate chặt; lớp khóa tại kho dữ liệu là bước kế — biết chính xác việc cần làm."),
    ("Nối dữ liệu sống.", "Đang chạy tập cố định ~5.000 review thật; kế tiếp: ống dữ liệu hằng ngày, giữ nguyên phần xử lý."),
    ("Báo động mới chỉ trên web.", "Người trực không mở máy 2 giờ sáng vẫn lỡ. Kế tiếp: đẩy thẳng vào điện thoại."),
], y=2.1, size=20)
notes(s, "8:00–8:50 · Giọng tự tin, không xin lỗi. Ý 3 móc lại câu chuyện mở đầu — nhấn chậm.")

# ---- S12 CLOSING / VISION ----
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)  # 1 = RECTANGLE
bg.fill.solid(); bg.fill.fore_color.rgb = GREEN; bg.line.fill.background()
txt(s, 0.9, 1.4, 11.5, 1.8, "Một lời phàn nàn không được đọc\nlà một sự cố đang chờ xảy ra lần nữa.", 34, WHITE, bold=True)
txt(s, 0.9, 3.6, 11.5, 1.5, "Tầm nhìn 3–5 năm: tầng lắng nghe tiêu chuẩn cho mọi nền tảng tiêu dùng Việt Nam —\nnơi mọi lời phàn nàn được đọc, được định tuyến, và trở thành hành động.", 18, WHITE)
txt(s, 0.9, 5.6, 11.5, 1.0, "Với chúng tôi — nó sẽ được đọc.   ·   Q&A", 20, WHITE, bold=True)
notes(s, "8:50–10:00 · Callback 2 giờ sáng → vòng lặp khép kín → tầm nhìn → câu kết → mời Q&A.")

out = "docs/project/slides/GreenSM-Pitch-10min.pptx"
prs.save(out); print("saved", out, "slides:", len(prs.slides._sldIdLst))
```

- [ ] **Step 2: Chạy và kiểm tra**

```bash
uv run --with python-pptx python scripts/slides/build_greensm_pitch.py
uv run --with python-pptx python - <<'EOF'
from pptx import Presentation
p = Presentation('docs/project/slides/GreenSM-Pitch-10min.pptx')
assert len(p.slides) == 12, len(p.slides)
assert all(s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip() for s in p.slides)
imgs = sum(1 for s in p.slides for sh in s.shapes if sh.shape_type == 13)
print('12 slides OK, notes OK, images:', imgs)
EOF
```

Expected: `12 slides OK, notes OK, images: >= 5`.

- [ ] **Step 3: Duyệt trực quan**

```bash
open docs/project/slides/GreenSM-Pitch-10min.pptx
```

Kiểm tra: chữ không tràn khung, ảnh không méo (pic_fit giữ tỉ lệ theo ngang — nếu ảnh S1 quá cao thì giảm width), slide 12 nền xanh chữ trắng. Sửa toạ độ nếu cần rồi chạy lại Step 2.

- [ ] **Step 4: Commit**

```bash
git add scripts/slides/build_greensm_pitch.py docs/project/slides/GreenSM-Pitch-10min.pptx
git commit -m "feat(slides): pitch deck Green SM 12 slide / 10 phút (pptx sinh bằng script)"
```

---

### Task 4: Cập nhật README slides + hoàn tất

**Files:**
- Modify: `docs/project/slides/README.md`

- [ ] **Step 1: Thêm mục mới vào README**

Thêm vào cuối `docs/project/slides/README.md`:

```markdown

## Pitch 10 phút (demo day)

- `GreenSM-Pitch-10min.pptx` — 12 slide, 16:9: 3' bài toán → 5' sản phẩm
  (mạch kịch bản v4, ẩn dụ phòng cấp cứu) → 2' closing/vision. Không có slide gọi vốn.
- `GreenSM-pitch-script.html` — kịch bản nói từng slide, mốc thời gian khớp speaker notes.
- `assets/pitch/` — screenshot UI thật + ảnh Green SM (nguồn trong `SOURCES.md`).
- Tái sinh deck: `uv run --with python-pptx python scripts/slides/build_greensm_pitch.py`.
```

- [ ] **Step 2: Kiểm tra tổng thể lần cuối**

Mở song song pptx (trình chiếu) và script HTML: đọc lướt từng slide theo script, bấm giờ nhẩm — tổng ≤ 10 phút; mốc thời gian trong notes khớp script.

- [ ] **Step 3: Commit**

```bash
git add docs/project/slides/README.md
git commit -m "docs(slides): README cho bộ pitch Green SM 10 phút"
```
