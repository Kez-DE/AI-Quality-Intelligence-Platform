-- ============================================================
-- Feedback review workflow: tách Review Queue vs Feedback Stream
-- ============================================================
-- needs_review : AI đánh dấu cần người duyệt (safety/severity cao/confidence thấp)
-- reviewed     : đã có người xử lý (duyệt hoặc sửa nhãn)
-- review_reason: lý do cần duyệt (hiển thị trên UI)

ALTER TABLE public.feedback
  ADD COLUMN IF NOT EXISTS needs_review BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS reviewed BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS review_reason TEXT;

-- Index phục vụ truy vấn Review Queue (cần duyệt & chưa xử lý).
CREATE INDEX IF NOT EXISTS feedback_review_queue_idx
  ON public.feedback (needs_review, reviewed, created_at DESC);
