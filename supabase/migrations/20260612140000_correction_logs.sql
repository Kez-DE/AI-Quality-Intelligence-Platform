-- ============================================================
-- correction_logs: nhật ký người duyệt sửa nhãn AI (Human-in-the-loop)
-- ============================================================
-- Mỗi lần nhân viên sửa nhãn (topic/sentiment/severity) mà AI gán sai,
-- ghi lại 1 dòng: nhãn cũ -> nhãn mới + ai sửa + lúc nào.
-- Dùng cho: audit, và về sau retrain model từ nhãn người đã sửa.

CREATE TABLE IF NOT EXISTS public.correction_logs (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  feedback_id UUID NOT NULL REFERENCES public.feedback(id) ON DELETE CASCADE,
  corrected_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  field TEXT NOT NULL CHECK (field IN ('topic', 'sentiment', 'severity')),
  old_value TEXT,
  new_value TEXT NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT ON public.correction_logs TO authenticated;
GRANT ALL ON public.correction_logs TO service_role;
ALTER TABLE public.correction_logs ENABLE ROW LEVEL SECURITY;

-- Ops staff (admin/manager/staff) xem được toàn bộ log; guest không.
CREATE POLICY "Correction logs select" ON public.correction_logs
  FOR SELECT TO authenticated
  USING (public.is_ops_staff());

-- Chỉ ops staff được ghi log sửa nhãn, và phải đúng danh tính người sửa.
CREATE POLICY "Correction logs insert" ON public.correction_logs
  FOR INSERT TO authenticated
  WITH CHECK (public.is_ops_staff() AND auth.uid() = corrected_by);

CREATE INDEX correction_logs_feedback_idx ON public.correction_logs(feedback_id, created_at DESC);
