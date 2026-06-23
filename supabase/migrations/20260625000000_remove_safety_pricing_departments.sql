-- Bỏ 2 phòng ban không còn dùng: Safety (An toàn) và Pricing (Giá cước).
-- Routing mới: topic Safety -> Vận hành, topic Pricing -> CSKH; P5 override -> Vận hành.
-- Phòng ban hợp lệ còn lại: IT, CSKH, Vận hành, Marketing.
--
-- LƯU Ý: profiles.department và alerts.assigned_team là TEXT (KHÔNG có CHECK
-- constraint), nên migration này KHÔNG fail dữ liệu cũ. Việc dọn dữ liệu lịch sử
-- (user/ticket đang gắn Safety/Pricing) là thao tác nghiệp vụ — xem phần cuối file.

-- 1) Cập nhật COMMENT cho khớp danh sách phòng ban mới (chỉ tài liệu hoá schema).
COMMENT ON COLUMN public.profiles.department IS
  'Team assignment: IT, CSKH, Vận hành, Marketing';

COMMENT ON COLUMN public.alerts.assigned_team IS
  'Canonical RBAC department: IT, CSKH, Vận hành, Marketing';

-- 2) Re-route alert đang mở còn gắn Pricing -> CSKH (đối xứng với routing mới).
--    (Alert gắn Safety nên dùng script pipeline/rescore_overall_risk.py để re-route
--    theo topic/severity cho chính xác; ở đây chỉ xử lý Pricing đơn giản.)
UPDATE public.alerts
SET assigned_team = 'CSKH'
WHERE assigned_team = 'Pricing'
  AND status IN ('open', 'in_progress');

-- 3) DỮ LIỆU CẦN ADMIN XỬ LÝ THỦ CÔNG (không tự đoán đích nên không auto-update):
--    - Các user (profiles) đang có department = 'Safety' hoặc 'Pricing' sẽ không còn
--      thuộc danh sách phòng hợp lệ -> admin cần gán lại phòng cho họ:
--        SELECT id, email, department FROM public.profiles
--        WHERE department IN ('Safety', 'Pricing');
--      rồi UPDATE từng người về phòng phù hợp (vd Safety->Vận hành, Pricing->CSKH).
--    - Alert/ticket gắn Safety đang mở: chạy pipeline/rescore_overall_risk.py --apply.
