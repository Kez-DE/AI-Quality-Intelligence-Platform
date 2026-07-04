-- Cho phép task đẩy trực tiếp từ Phân loại Ticket (source='ticket'), tách khỏi luồng
-- agent tự sinh và report dispatch.
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_source_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_source_check
  CHECK (source IN ('agent','report','ticket'));
