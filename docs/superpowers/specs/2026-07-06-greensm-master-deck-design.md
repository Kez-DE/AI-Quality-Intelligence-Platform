# Green SM Master Deck — Design Spec

**Ngày:** 2026-07-06 · **Trạng thái:** user đã duyệt cấu trúc 25 slide trong chat, kèm yêu cầu "hoàn thiện cả màu các thứ".

## Mục tiêu

Master deck trình bày trọn vẹn (~25 phút, không giới hạn giờ) cho ban giám khảo AI20K:
kể **câu chuyện business** (pain point thực, ứng dụng đáp ứng nhu cầu gì) → **sản phẩm thực tế**
(demo flow, 7 chặng, vòng đời task, vận hành giao việc) → **bằng chứng & kỹ thuật** → **giá trị & tầm nhìn**.
Kèm kịch bản nói HTML từng slide.

## Deliverables

1. `docs/project/slides/GreenSM-Master-Deck.pptx` — 25 slide 16:9, speaker notes có thời lượng gợi ý, sinh bằng `scripts/slides/build_greensm_master.py` (python-pptx qua uv).
2. `docs/project/slides/GreenSM-master-script.html` — kịch bản nói 25 section (CSS tái dùng từ file v4), mẹo trình bày, Q&A.
3. Asset bổ sung: `assets/pitch/ui-staff.png` (màn "Việc của tôi" của nhân viên, trích từ deck 20-slide cũ, slide 14).

## Cấu trúc 25 slide (đã duyệt)

- **Hồi 1 · Câu chuyện business (S1–S5):** Hook 2 giờ sáng + ảnh thật + 4.8★/1,5 triệu → Tăng trưởng Green SM & review thật chìm nghỉm → Pain point & cái giá business → Ai đang đau & cần gì (vận hành/CSKH/quản lý) → Why now + 1 câu giải pháp.
- **Hồi 2 · Sản phẩm thực tế (S6–S16):** Giải pháp "khoang lái" 4 khối → Demo flow 5 màn hình thật → 7 chặng + 4 nguyên tắc → Chặng 1–2 (PII+ML) → Chặng 3 (Rule ghi đè, ví dụ thật) → Chặng 4 (Spike, ngưỡng) → Chặng 5 (Router + bảng SLA) → Chặng 6 (Alert→Task 2 đường) → Chặng 7 (HITL + vòng học) → Vòng đời task 5 trạng thái → Vận hành giao việc Manager↔Nhân viên.
- **Hồi 3 · Bằng chứng & kỹ thuật (S17–S20):** Số đo pipeline → Bảng 6/6 test case → Kiến trúc 6 service + LLM failover → Tech stack.
- **Hồi 4 · Giá trị & tương lai (S21–S25):** Tư duy sản phẩm 5 nguyên tắc → Ứng dụng thực tế (bảng pain point → năng lực → kết quả) → Hạn chế & roadmap → Vòng lặp đã khép → Vision + kết + Q&A.

## Hệ thiết kế (yêu cầu "hoàn thiện màu")

- **Palette:** GREEN `#0E7C55` (chủ đạo) · GREEN_SOFT `#E3F1EA` (nền card/nhấn) · INK `#171D1A` · MUTED `#5B655F` · WHITE `#FFFFFF` · AMBER `#B45309` (cảnh báo/pain point) · AMBER_SOFT `#FEF3C7`.
- **Khung slide nội dung:** band mảnh màu GREEN cao 0.12in sát mép trên; kicker "HỒI n · TÊN HỒI" chữ GREEN; footer mảnh: "Green SM · AI Quality Intelligence Platform · Team 116" + số trang, chữ MUTED 10pt.
- **Thành phần:** card bo góc (rounded rect) nền GREEN_SOFT viền GREEN cho stat/quote; card AMBER_SOFT cho pain point; bảng (SLA, test case, pain→năng lực→kết quả) header nền GREEN chữ trắng, hàng chẵn nền `#F4F7F5`; pipeline 7 chặng dạng chip bo góc nối mũi tên.
- **Slide đặc biệt:** S1 (hook) ảnh phải + stat card; S25 (vision) nền GREEN full chữ trắng như S12 bản 10'.
- Font mặc định theme (không nhúng font); emoji dùng tiết chế, kiểm tra máy chiếu trước demo.

## Ràng buộc nội dung

- Chỉ số THẬT đã kiểm chứng (kế thừa bản 10'): 4.8★/1,5 triệu đánh giá App Store VN; ra mắt 14/04/2023; 34 tỉnh; 4 quốc gia; 1000+ review/ngày (số suy ra, có ghi nguồn); 77,1% topic (932 mẫu); 94,3% sentiment; 97% recall negative; 4.837 review/97 giây; ~50 review/giây streaming; 6/6 test case; spike 1/≥3/≥10 + cooldown 60'; SLA Safety→Vận hành 1 giờ, App Issue→IT 12h, Payment→CSKH 12h.
- **KHÔNG** slide gọi vốn; **KHÔNG** slide phân quyền/chatbot riêng (dòng nguyên tắc "RBAC" ở S21 sửa thành "kiểm quyền ở backend theo vai trò & phòng ban" — không nói RLS vì RLS còn trong roadmap).
- Ẩn dụ phòng cấp cứu giữ ở Hồi 2; callback "2 giờ sáng" ở S23/S24.
- Vị trí: nhánh local `feat/greensm-pitch-deck` (user không merge main).

## Nguồn nội dung tái dùng

Bản 10' (narration + style code) · deck cũ 20 slide (S4 giải pháp, S6 luồng E2E, S12–14 vòng đời/giao việc/nhân viên, S18 tư duy sản phẩm, S19 kết quả) · xanhQuocAnh.pptx (chi tiết chặng, bảng test case, kiến trúc/tech stack) · SOURCES.md (ảnh + số liệu).
