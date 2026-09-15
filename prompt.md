# Prompt cho NotebookLM — Dựng bộ slide giới thiệu sản phẩm xanhSM

> Dán toàn bộ nội dung dưới đây vào ô tùy chỉnh (customize) của NotebookLM khi tạo
> Report hoặc Video Overview. NotebookLM không xuất file PowerPoint trực tiếp, nên
> yêu cầu nó trả về **bản đặc tả slide theo từng trang** để bạn dán sang Google
> Slides / Canva / Gemini và lên hình.

---

## Vai trò và mục tiêu

Bạn là một giám đốc sản phẩm kiêm người dựng pitch deck. Nhiệm vụ: từ các tài liệu
nguồn trong notebook này, soạn một bộ slide **giới thiệu sản phẩm** hoàn chỉnh, dễ
hiểu, thuyết phục, dùng để **trình bày cho ban giám khảo và nhà đầu tư**.

Mục tiêu của bộ slide: người xem trong 7–10 phút phải nắm được sản phẩm giải bài
toán gì, vận hành ra sao, giá trị thật nằm ở đâu, và vì sao cách làm này khôn ngoan
về mặt kinh doanh lẫn kỹ thuật.

## Khán giả và bối cảnh

- **Khán giả**: hội đồng đánh giá và nhà đầu tư. Họ thông minh nhưng không có
  thời gian; họ quan tâm bài toán thật, giá trị thật, và tư duy đằng sau giải pháp
  hơn là chi tiết code.
- **Sản phẩm**: AI Quality Intelligence Platform — "Quality Operation Cockpit" cho
  dịch vụ gọi xe **xanhSM**. Một hệ thống AI đọc thay con người hàng nghìn phản hồi
  khách hàng mỗi ngày, tự phân loại, phát hiện điểm nóng, sinh cảnh báo và giao việc
  đúng phòng ban theo SLA, rồi tổng hợp thành báo cáo.

## Định dạng đầu ra bắt buộc

Trả về một bộ **19 slide**. Mỗi slide trình bày đúng theo khuôn sau:

```
Slide N — <Tiêu đề ngắn, mạnh, tối đa 8 chữ>
• Gạch đầu dòng 1 (ngắn, mỗi dòng một ý)
• Gạch đầu dòng 2
• ... (3–5 gạch đầu dòng, KHÔNG quá 5)

Ghi chú thuyết trình: 2–3 câu người nói sẽ nói khi đứng trước slide này.
Gợi ý hình ảnh: mô tả 1 biểu đồ, sơ đồ, hoặc ảnh màn hình phù hợp.
```

Không viết đoạn văn dài trên slide. Slide là điểm tựa cho người nói, không phải bài
đọc. Chữ trên slide ít, ghi chú thuyết trình mới mang nội dung.

## Giọng điệu

- Viết như một người thật đang kể về sản phẩm mình tâm huyết, không như máy.
- Cụ thể và có số. Tránh các cụm sáo rỗng kiểu "giải pháp đột phá toàn diện",
  "cách mạng hóa", "tận dụng sức mạnh AI". Thay bằng việc nói rõ nó làm được gì.
- Mỗi khẳng định giá trị nên gắn với một cơ chế thật hoặc một con số thật.
- Câu ngắn. Động từ mạnh. Hạn chế tính từ.

## Số liệu và sự thật được phép dùng (chỉ dùng những con số này, không bịa thêm)

- Phân loại bằng ML (TF-IDF + LinearSVC): ~77% chính xác topic, ~94% chính xác
  sentiment (test ~932 mẫu).
- Định tuyến đúng phòng ban: ~75.4% trên tập holdout.
- Chấm rủi ro 5 chiều bằng LLM: safety, fraud, attitude, vehicle, compliance →
  gộp thành điểm P1–P5.
- 8 agent nghiệp vụ + 1 orchestrator điều phối.
- 4 phòng ban (IT, CSKH, Vận hành, Marketing) và 4 vai trò (admin, manager, staff,
  guest).
- SLA theo chủ đề: ví dụ Safety 1 giờ, App Issue 12 giờ, Other 24 giờ.
- Lưới Safety luôn ghi đè: review nguy hiểm bị ép Safety / negative / P5 / cần duyệt.
- 4 lớp AI: chat LLM realtime, multi-agent batch, ML phân loại, rule engine.
- Hạ tầng: 3 tầng (frontend React / backend FastAPI + 4 worker / Supabase
  PostgreSQL), deploy thành 6 service Docker trên Railway.
- Đa nhà cung cấp LLM (OpenRouter, OpenAI, Gemini, Groq) qua một cổng duy nhất có
  failover; hết key thật thì chạy mock nên demo không bao giờ vỡ.
- Human-in-the-loop: nhân viên sửa nhãn AI → ghi correction log → dữ liệu retrain.
- Khép kín Báo cáo → Task: manager biên tập hành động AI đề xuất rồi duyệt một nút
  để tự tạo task chính thức, có liên kết ngược về báo cáo gốc.

## Ràng buộc

- Không bịa số liệu, tên khách hàng, doanh thu, hay đối tác. Chỉ dùng dữ kiện trên.
- Không hiển thị bất kỳ khóa API, mật khẩu, email tài khoản, hay thông tin nhạy cảm
  nào dù có gặp trong nguồn.
- Nói rõ đây là **bản demo chạy thật** trên dữ liệu review công khai, không phải dữ
  liệu vận hành nội bộ của hãng — trung thực tạo uy tín với giám khảo.
- Không phóng đại. Nếu một phần là mô phỏng (ví dụ vòng đời ticket theo thời gian),
  hãy gọi đúng tên là mô phỏng.

---

## Dàn ý 19 slide

Bám sát dàn ý này về thứ tự và thông điệp. Làm giàu nội dung từ tài liệu nguồn.

**Slide 1 — Bìa.** Tên sản phẩm và một câu định vị: "Quality Operation Cockpit cho
xanhSM — AI đọc phản hồi khách hàng thay con người." Tên sản phẩm.

**Slide 2 — Bài toán.** Mỗi ngày hàng nghìn phản hồi về dịch vụ gọi xe. Con người
không đọc xuể. Vấn đề nghiêm trọng bị chìm trong khối lượng.

**Slide 3 — Hệ quả nếu chậm.** Một vụ tài xế đi ẩu hôm nay, nếu không phát hiện
sớm, lan thành rủi ro an toàn, mất khách, và tổn hại thương hiệu. Tốc độ phát hiện
là tiền.

**Slide 4 — Giải pháp một câu.** Hệ thống đọc thay → phân loại → phát hiện điểm
nóng → sinh cảnh báo và giao đúng phòng ban theo SLA → tổng hợp báo cáo. Khép kín
từ phản hồi đến hành động.

**Slide 5 — Sản phẩm nhìn thế nào.** Giới thiệu Cockpit: dashboard realtime với
KPI, luồng phản hồi trực tiếp, bản đồ nhiệt khu vực, bảng xếp hạng phòng ban. Gợi ý
ảnh chụp màn hình dashboard.

**Slide 6 — Cách vận hành: hành trình một review.** Đi theo một câu phản hồi từ đầu
đến cuối: che PII → ML phân loại → rule ghi đè → phát hiện spike → định tuyến phòng
ban → tạo ticket → gom thành task → báo cáo. Gợi ý sơ đồ luồng ngang.

**Slide 7 — Tư duy thiết kế: 4 nguyên tắc.** Hybrid nhanh/chậm (ML rẻ chạy mọi
review, LLM đắt chỉ chạy chỗ cần suy luận); Safety-first; Config-driven (đổi nghiệp
vụ không sửa code); Graceful degradation (hỏng một mảnh không sập cả hệ). Đây là
"tư duy kinh doanh" gặp "tư duy kỹ thuật".

**Slide 8 — Lõi AI: 4 lớp.** Chat LLM realtime, multi-agent batch, ML phân loại,
rule engine. Mỗi lớp một việc, chi phí khác nhau, phối hợp với nhau.

**Slide 9 — Bộ não multi-agent.** 8 agent nghiệp vụ + orchestrator như một dây
chuyền: ingestion → scoring → alert → router → ticket → task → insight → analyst.
Gợi ý sơ đồ dây chuyền agent.

**Slide 10 — An toàn là trên hết.** Lưới Safety luôn thắng xác suất. Định tuyến
phòng ban theo bảng cấu hình, mỗi chủ đề một mốc SLA; mọi ca P5 ép về đội Vận hành
phản ứng nhanh.

**Slide 11 — Con người trong vòng lặp.** AI không phải lúc nào cũng đúng. Nhân viên
sửa nhãn → ghi correction log (ai sửa, sửa gì) → vừa là audit, vừa là dữ liệu
retrain. Một vòng học khép kín.

**Slide 12 — Điểm nhấn: Báo cáo thành hành động.** Manager đọc báo cáo AI, biên tập
danh sách hành động đề xuất, bấm một nút "Duyệt và triển khai" để tự tạo task chính
thức có liên kết ngược về báo cáo gốc. Đây là chỗ AI biến thành việc làm thật.

**Slide 13 — Bảo mật và phân quyền.** 4 vai trò × 4 phòng ban. Mỗi người chỉ thấy
dữ liệu phòng mình; admin thấy tất cả. Mọi thay đổi quyền vào audit log. Chat cũng
bị giới hạn theo phòng và che PII hai đầu.

**Slide 14 — Kiến trúc và công nghệ.** 3 tầng, 6 service Docker. Đa nhà cung cấp
LLM qua một cổng có failover và mock — không khóa vào một nhà cung cấp, demo không
bao giờ vỡ. Gợi ý sơ đồ kiến trúc 3 tầng.

**Slide 15 — Giá trị thật và ROI.** Giảm thời gian phát hiện và xử lý sự cố; bắt
vấn đề trước khi lan; quyết định dựa trên dữ liệu thay vì cảm tính; chi phí AI tối
ưu nhờ chỉ gọi LLM ở chỗ cần. Nói bằng lợi ích vận hành, không bằng thuật ngữ.

**Slide 16 — Khác biệt cạnh tranh.** Hybrid tiết kiệm chi phí, safety-first, cấu
hình thay vì sửa code, đa provider không phụ thuộc một bên. So với "ném tất cả vào
một LLM lớn", cách này rẻ hơn, an toàn hơn, kiểm soát được hơn.

**Slide 17 — Demo.** Tóm tắt kịch bản 5–7 phút: gửi phản hồi → AI tự gán nhãn →
sửa một nhãn sai → chạy streaming → xem Ticket Triage → phân tích phòng ban → duyệt
báo cáo thành task → hỏi AI Chat "khu vực nào đang nóng?".

**Slide 18 — Lộ trình.** Từ bản demo (review công khai, mô phỏng vòng đời ticket,
thông báo trên dashboard) đến production thật (hút realtime từ app, dữ liệu vận hành
thật, push Slack/email/app tài xế, CI/CD và monitoring đầy đủ).

**Slide 19 — Tổng kết và tầm nhìn.** Một câu đọng lại: biến tiếng nói khách hàng
thành hành động trước khi sự cố lan. Lời mời tiếp theo (dùng thử, đầu tư, mở rộng).

---

## Sau khi tạo xong

Sau bộ slide, thêm một mục ngắn **"Câu hỏi giám khảo có thể hỏi"**: liệt kê 5 câu
hỏi khó có khả năng được hỏi (độ chính xác model, chi phí LLM khi scale, bảo mật dữ
liệu, vì sao không dùng một LLM lớn duy nhất, đường đến production) kèm câu trả lời
ngắn dựa trên dữ kiện ở trên.
