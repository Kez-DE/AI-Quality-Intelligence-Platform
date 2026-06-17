-- Migration: Add overall_risk column (Waterfall algorithm output, 1-5 scale)
-- Used by ml-worker (worker_ml.py) to filter unscored rows and store results.

ALTER TABLE public.feedback
ADD COLUMN IF NOT EXISTS overall_risk INTEGER DEFAULT NULL;

COMMENT ON COLUMN public.feedback.overall_risk IS 'Điểm rủi ro tổng hợp (1-5) từ Max-Pooling Waterfall algorithm. NULL = chưa chấm.';
