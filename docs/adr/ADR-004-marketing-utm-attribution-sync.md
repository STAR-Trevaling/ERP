# ADR 004: Marketing UTM Attribution & Ad Click ID Synchronization

## 1. Context (Bối cảnh)
Phía Public Site (Next.js & Django API) vừa nâng cấp cơ chế theo dõi tiếp thị (Marketing Attribution & UTM Tracking):
1. **Tham số UTM**: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` được lưu trữ ở client với cửa sổ ghi nhận (attribution window) 30 ngày.
2. **Ad Click IDs**: Thu thập `gclid` (Google Ads Click ID) và `fbclid` (Facebook Ads Click ID).
3. **Ngữ cảnh truy cập**: `landing_page` và `referrer` URL được đính kèm khi khách gửi tư vấn (`/api/v1/inquiries/`).
4. **Vấn đề cần giải quyết**:
   - Trước đây Odoo `crm.lead` chỉ nhận trường `channel` thô và map vào `utm.source`, thiếu hoàn toàn thông tin chiến dịch (`utm_campaign`), hình thức quảng cáo (`utm_medium`), từ khóa (`utm_term`), mẫu quảng cáo (`utm_content`) và mã click quảng cáo.
   - Khiến đội ngũ Sales & Marketing không đo lường được chi phí quảng cáo (CAC), ROI chiến dịch, và hành trình khách hàng từ lúc click ad đến lúc chốt cọc tour.

## 2. Decision (Quyết định)

### 2.1 Chuẩn Hóa Data Contract (Inbound Payload Envelope)
- Mở rộng JSON Schema `contracts/integration/inquiry_created.json` và `contracts/integration/openapi.yaml` bổ sung đối tượng `marketing`:
  ```json
  "marketing": {
    "channel": "website",
    "utm_source": "google_ads",
    "utm_medium": "cpc",
    "utm_campaign": "autumn_promotion_2026",
    "utm_term": "du lich ha long 3n2d",
    "utm_content": "banner_creative_v1",
    "gclid": "Cj0KCQjwx...",
    "fbclid": "IwAR3...",
    "landing_page": "/tours/ha-long-cruise?utm_source=google_ads...",
    "referrer": "https://www.google.com"
  }
  ```
- **Khả năng tương thích ngược (Backward Compatibility)**: Controller và Lead Parser tự động kiểm tra theo thứ tự ưu tiên: `data.marketing` -> `data.source_metadata` -> `data.utm` -> root fields.

### 2.2 Ánh Xạ Chuẩn Odoo `utm.mixin` & Auto-Discovery
- `crm.lead` trong Odoo 18 kế thừa sẵn `utm.mixin`. Ta ánh xạ:
  - `source_id`: Resolve case-insensitive (`=ilike`) với `utm.source` theo `utm_source` (hoặc fallback `channel`). Nếu chưa tồn tại, tự động tạo mới `utm.source`.
  - `medium_id`: Resolve case-insensitive (`=ilike`) với `utm.medium` theo `utm_medium`. Nếu chưa tồn tại, tự động tạo mới `utm.medium`.
  - `campaign_id`: Resolve case-insensitive (`=ilike`) với `utm.campaign` theo `utm_campaign` (hoặc `campaign`). Nếu chưa tồn tại, tự động tạo mới `utm.campaign`.

### 2.3 Mở Rộng Schema `crm.lead` (PostgreSQL Model)
Bổ sung các trường lưu trữ chiến dịch chi tiết và click ID:
- `utm_term`: `fields.Char(string="UTM Term / Keywords", index=True, copy=False)`
- `utm_content`: `fields.Char(string="UTM Content", copy=False)`
- `gclid`: `fields.Char(string="Google Click ID (GCLID)", index=True, copy=False)`
- `fbclid`: `fields.Char(string="Facebook Click ID (FBCLID)", index=True, copy=False)`
- `landing_page_url`: `fields.Char(string="Landing Page URL", copy=False)`
- `referrer_url`: `fields.Char(string="Referrer URL", copy=False)`

### 2.4 Giao Diện Backoffice UX (Odoo CRM Views)
- Thêm nhóm "Marketing & Attribution" trên Form View của `crm.lead`: hiển thị rõ ràng Source, Medium, Campaign, Keywords, Creative Content, Click IDs và Landing/Referrer URLs.
- Thêm bộ lọc Search & Group By trong CRM Pipeline theo Chiến dịch (Campaign), Nguồn (Source) và Kênh (Medium).

## 3. Status (Trạng thái)
**ACCEPTED** - Đã thiết kế, tích hợp và kiểm thử đạt 100% qua bộ unit test và schema validator.

## 4. Consequences (Hệ quả)
- **Ưu điểm**:
  - Đảm bảo tính toàn vẹn dữ liệu đa kênh giữa Next.js/Django và Odoo CRM.
  - Odoo trở thành Single Source of Truth duy nhất cho dữ liệu chuyển đổi tiếp thị (Marketing Conversion Attribution).
  - Tự động hóa hoàn toàn việc phân loại Leads, không cần nhân viên nhập liệu thủ công nguồn marketing.
- **Đánh đổi**:
  - Bảng `utm.source`, `utm.medium`, `utm.campaign` có thể phát sinh thêm bản ghi khi có chiến dịch mới (đã giải quyết bằng tìm kiếm không phân biệt hoa thường và trim khoảng trắng).
