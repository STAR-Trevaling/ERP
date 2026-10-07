# ADR 003: Transactional Outbox Pattern & Inbound Idempotency Defense

## 1. Context (Bối cảnh)
Trong hệ thống thương mại du lịch đa kênh (Omnichannel Travel Platform), kết nối giữa Public Platform (Django/Next.js) và Backoffice ERP (Odoo 18) chịu tác động của độ trễ mạng, timeout và việc gửi lại (retry) các HTTP requests. 
Nếu không có cơ chế phòng thủ chặt chẽ:
1. **Network Retries** sẽ làm phát sinh duplicate Leads trong CRM, gửi trùng email xác nhận hoặc tính sai chỉ số bán hàng.
2. **Dual-Write Hazard**: Việc ghi dữ liệu vào Odoo DB và bắn webhook ra bên ngoài trong cùng 1 request dễ dẫn đến sai lệch dữ liệu nếu một bên thất bại.

## 2. Decision (Quyết định)

### 2.1 Inbound Idempotency Defense (Phòng thủ Nhập sự kiện)
- Mọi HTTP request gửi đến Odoo (`POST /api/v1/travel/inquiry`, `POST /api/v1/travel/partner-application`) bắt buộc phải có `X-Idempotency-Key` (UUIDv4) hoặc `event_id` trong payload.
- Odoo lưu lại từng sự kiện vào bảng `travel.integration.event` với ràng buộc database `_sql_constraints = [('source_event_uniq', 'unique(source, external_event_id)', ...)]`.
- **Cơ chế Replay Cache**: Nếu nhận cùng một `(source, external_event_id)`:
  - Cursor phát hiện bản ghi đã tồn tại.
  - Tăng số lần thử `attempt_count += 1`.
  - Trả về nguyên trạng phản hồi JSON đã lưu trong `response_payload` với mã HTTP 200 OK.
  - **Tuyệt đối không chạy lại business logic** và không nhân bản `crm.lead` hay `res.partner`.

### 2.2 Transactional Outbox Pattern (Mẫu Outbox Giao dịch)
- Khi nhân viên biên tập xuất bản nội dung trong CMS (Destination, Place, Article), sự kiện `*.published` được ghi vào bảng `travel.integration.outbox` **trong cùng một Database Transaction** với việc cập nhật `state = 'published'`.
- Nếu commit thành công, bản ghi Outbox luôn tồn tại (không bao giờ mất sự kiện do crash).
- Quá trình dispatch sự kiện gửi webhook sang Public Platform theo cơ chế:
  - Ký chữ ký `X-Signature-SHA256` sử dụng HMAC-SHA256.
  - Tự động retry với Exponential Backoff (1s, 2s, 4s, 8s, 16s...) tối đa 5 lần trước khi chuyển sang trạng thái `failed`.
  - Định kỳ Scheduled Action (`ir.cron`) quét các outbox `state in ('pending', 'processing')` để tái gửi.

### 2.3 Bảo mật & Chuẩn Lỗi
- Mọi webhook payload được ký bằng HMAC-SHA256 bí mật (`travel.webhook_secret`).
- Odoo xác thực bằng `hmac.compare_digest` để triệt tiêu lỗ hổng Timing Attack.
- Các lỗi 4xx/5xx tuân thủ chuẩn **RFC 7807 (Problem Details for HTTP APIs)** với trường `type`, `title`, `status`, `detail`, `invalid_params`.

## 3. Status (Trạng thái)
**ACCEPTED** - Đã triển khai và bảo chứng 100% qua bộ kiểm thử Unit Test & E2E Test.

## 4. Consequences (Hệ quả)
- **Ưu điểm**:
  - Đảm bảo tính nhất quán cuối cùng (Eventual Consistency) tuyệt đối.
  - Triệt tiêu hoàn toàn rủi ro duplicate Leads và race-conditions do mạng.
  - Nhật ký kiểm toán (Audit Trail) đầy đủ cho từng gói tin inbound và outbound.
- **Đánh đổi**:
  - Cần quản lý dọn dẹp (Housekeeping/Archival) bảng outbox sau một khoảng thời gian (e.g. 90 ngày).
