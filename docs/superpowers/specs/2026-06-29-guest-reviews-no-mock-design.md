# Spec: Bỏ mock reviews trong "Phản hồi của bạn" — GuestDashboard

**Date:** 2026-06-29  
**Lane:** Tiny  
**File affected:** `app/src/components/GuestDashboard.tsx`

## Vấn đề

Section "Phản hồi của bạn" hiện khởi tạo state với `seedReviews` — 3 review giả hardcode. Khách thấy card giả ngay khi vào trang, dù chưa gửi gì. Gây hiểu nhầm.

## Yêu cầu

- Không hiện review nào khi khách chưa gửi phản hồi trong phiên hiện tại.
- Sau khi khách submit form, review mới xuất hiện đúng như logic `submitFeedback` hiện tại.
- Empty state rõ ràng khi chưa có review: hướng khách xuống form gửi.

## Thay đổi

### 1. Xóa `seedReviews` constant (dòng 94–131)

Toàn bộ mảng hardcode này bị xóa.

### 2. Đổi init state

```ts
// trước
const [reviews, setReviews] = useState<Review[]>(seedReviews);

// sau
const [reviews, setReviews] = useState<Review[]>([]);
```

### 3. Cải thiện empty state của section

Khi `reviews.length === 0`, ẩn filter bar và hiện empty state với CTA:

```tsx
{reviews.length === 0 ? (
  <div className="rounded-xl border border-dashed bg-background/40 p-8 text-center">
    <MessageSquare className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
    <p className="text-sm font-medium">Bạn chưa gửi phản hồi nào</p>
    <p className="mt-1 text-xs text-muted-foreground">Điền form bên trên để gửi đánh giá đầu tiên.</p>
    <a href="#guest-feedback" className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline">
      <PenLine className="h-3.5 w-3.5" /> Gửi phản hồi ngay
    </a>
  </div>
) : (
  // filter bar + grid cards như hiện tại
)}
```

`SectionTitle` sub cũng cập nhật: hiện `${reviews.length} phản hồi` khi có review, hoặc `"Gửi đánh giá để xem lịch sử xử lý"` khi chưa có.

## Không thay đổi

- Logic `submitFeedback` — giữ nguyên.
- Filter bar, sentiment badge, card layout — giữ nguyên khi có review.
- Các section khác trong `GuestDashboard` — không đụng.

## Validation

- Load trang guest → section "Phản hồi của bạn" trống, hiện empty state + link.
- Submit review → card xuất hiện, filter bar hiện, sub count cập nhật.
