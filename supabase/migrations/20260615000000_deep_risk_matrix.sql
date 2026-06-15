-- Migration: Add Deep Risk Matrix columns to feedback table

ALTER TABLE public.feedback
ADD COLUMN IF NOT EXISTS risk_safety INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS risk_fraud INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS risk_attitude INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS risk_vehicle INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS risk_compliance INTEGER DEFAULT 0;

-- Comment for metadata
COMMENT ON COLUMN public.feedback.risk_safety IS 'Bậc 0-10: Đe dọa tính mạng, thân thể, tai nạn';
COMMENT ON COLUMN public.feedback.risk_fraud IS 'Bậc 0-10: Hành vi chiếm đoạt, gian lận cước';
COMMENT ON COLUMN public.feedback.risk_attitude IS 'Bậc 0-10: Cư xử không chuẩn mực, chửi bới';
COMMENT ON COLUMN public.feedback.risk_vehicle IS 'Bậc 0-10: Hỏng hóc, mất vệ sinh xe';
COMMENT ON COLUMN public.feedback.risk_compliance IS 'Bậc 0-10: Đi sai đường, trễ giờ, không tuân thủ quy trình';
