#!/usr/bin/env bash
# Chuẩn bị ảnh (assets) cho pitch deck Green SM 10 phút.
# Tái lập Step 1-4 của task-1-brief.md, với URL/mapping cuối cùng đã chọn
# sau khi xác nhận trực quan (Read tool) từng ảnh trích từ deck cũ.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSETS_DIR="$REPO_ROOT/docs/project/slides/assets/pitch"
MEDIA_TMP="$(mktemp -d)"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

mkdir -p "$ASSETS_DIR"

# --- Step 1: Trích screenshot UI từ deck cũ ---
unzip -o -j "$REPO_ROOT/docs/project/slides/AI-Quality-Intelligence-Platform-Overview.pptx" \
  'ppt/media/*' -d "$MEDIA_TMP"

# --- Step 2: Đổi tên ngữ nghĩa ---
# Mapping dưới đây đã được xác nhận TRỰC QUAN bằng tool Read (không dùng
# suy đoán theo số thứ tự slide) — khác với mapping ví dụ trong brief.
cp "$MEDIA_TMP/image-4-1.png"  "$ASSETS_DIR/ui-dashboard.png"  # Bảng điều khiển Chất lượng / Tổng quan
cp "$MEDIA_TMP/image-7-1.png"  "$ASSETS_DIR/ui-feedback.png"   # Thu thập phản hồi
cp "$MEDIA_TMP/image-8-1.png"  "$ASSETS_DIR/ui-ticket.png"     # Phân loại Ticket
cp "$MEDIA_TMP/image-10-1.png" "$ASSETS_DIR/ui-report.png"     # Báo cáo Tự động (AI)
cp "$MEDIA_TMP/image-11-1.png" "$ASSETS_DIR/ui-tasks.png"      # Quản lý công việc
cp "$MEDIA_TMP/image-17-1.png" "$ASSETS_DIR/ui-chat.png"       # Trợ lý đồng hành xanhSM (chatbot)

# --- Step 3: Tải ảnh Green SM thật từ web ---
# 1) og:image / hero từ trang chủ chính thức xanhsm.com: LOẠI — ảnh có chú
#    thích "Hình ảnh minh họa được tạo bởi AI, có thể khác với thực tế".
# 2) Fallback dùng: bài báo Tuổi Trẻ về ngày ra mắt Taxi Xanh SM tại Hà Nội,
#    ảnh chụp thật (EXIF Sony ILCE-7M4), 1920x1280.
curl -sL 'https://cdn.tuoitre.vn/471584752817336320/2023/4/8/taxi-xanh-sm6-16809432795061009639820.jpg' \
  -A "$UA" -o "$ASSETS_DIR/greensm-photo.jpg"
sips -g pixelWidth -g pixelHeight "$ASSETS_DIR/greensm-photo.jpg"

# --- Step 4: SOURCES.md (bằng chứng App Store + nguồn ảnh) ---
cat > "$ASSETS_DIR/SOURCES.md" <<'EOF'
- App Store VN (Green SM: Electric Mobility, id6446425595): 4.8★, 1.5M ratings — truy cập 2026-07-06
  https://apps.apple.com/vn/app/green-sm-electric-mobility/id6446425595
- Ra mắt 14/04/2023; 34 tỉnh thành; 4 quốc gia (VN, Lào, Philippines, Indonesia) — xanhsm.com
- greensm-photo.jpg tải từ: https://cdn.tuoitre.vn/471584752817336320/2023/4/8/taxi-xanh-sm6-16809432795061009639820.jpg
  (Báo Tuổi Trẻ, bài "Taxi Xanh SM chính thức hoạt động tại Hà Nội từ ngày 14-4",
  https://tuoitre.vn/taxi-xanh-sm-chinh-thuc-hoat-dong-tai-ha-noi-tu-ngay-14-04-20230408154906708.htm)
  — lưu ý: ứng viên đầu (hero banner xanhsm.com) bị loại vì có chú thích
  "Hình ảnh minh họa được tạo bởi AI, có thể khác với thực tế" — không phải ảnh thật.
EOF

rm -rf "$MEDIA_TMP"
echo "Done. Assets in $ASSETS_DIR"
