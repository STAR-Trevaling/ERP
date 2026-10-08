# Star Travels - Payment & Reconciliation Sync (`star_travels_payment_sync`)

Module Odoo 18 tích hợp toàn diện quy trình thanh toán du lịch đa kênh:
1. **Thanh toán tự động qua Cổng (VNPay, MoMo, ZaloPay)**: Tiếp nhận webhook `booking.paid` và `booking.refunded`, tự động tạo Đơn hàng (Sale Order), Hóa đơn (Invoice), Bút toán thanh toán (Payment) và đối trừ công nợ tự động.
2. **Xác nhận chuyển khoản VietQR thủ công (Manual Bank Transfer)**: Tiếp nhận đơn hàng chờ chuyển khoản (`payment-pending`), giao diện đối chiếu sao kê ngân hàng cho kế toán, wizard xác nhận tiền về kèm cơ chế gọi ngược cập nhật trạng thái sang Django backend.
3. **Nhật ký kiểm toán bất biến (Append-Only Audit Trail)**: Theo dõi chặt chẽ mọi biến động thanh toán, ngăn chặn chỉnh sửa hoặc xóa dữ liệu, kiểm soát nghiêm ngặt nguyên tắc tách biệt vai trò (Separation of Duties).
4. **Đối soát bảng kê (Statement Reconciliation Wizard)**: Nhập file sao kê CSV/Excel từ cổng thanh toán để tự động so khớp mã giao dịch và số tiền.

---

## 1. Kiến Trúc & Luồng Dữ Liệu VietQR Thủ Công

```
┌────────────────────────────────────────────────────────┐
│               Django Backend (PostgreSQL)              │
│  - Khách tạo QR thanh toán -> state: 'pending'         │
│  - Gửi webhook: POST /api/v1/travel/payment-pending    │
└───────────────────────────┬────────────────────────────┘
                            │ HMAC-SHA256 Signed Webhook
┌───────────────────────────▼────────────────────────────┐
│                  Odoo 18 Clean Monolith                │
│  1. Lưu vào Hàng đợi: star.travels.payment.pending     │
│  2. Ghi Audit Log: 'pending_received'                  │
│                                                        │
│  [Thao Tác Kế Toán]:                                   │
│  - Kế toán kiểm tra sao kê tài khoản ngân hàng thực tế │
│  - Bấm "Xác nhận đã nhận tiền" trên giao diện Odoo     │
│  - Wizard kiểm tra:                                    │
│    * Quyền: group_payment_confirmer                    │
│    * SoD: User xác nhận != Người tạo đơn (user_id)     │
│    * Nếu lệch tiền: BẮT BUỘC nhập chứng từ giải trình  │
│  - Hạch toán: Tạo SO -> Post Invoice -> Post Payment   │
│  - Reconcile công nợ hóa đơn & thanh toán              │
│  - Ghi Audit Log bất biến: 'manual_confirmed'          │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/payments/{id}/vietqr-confirm/
                            │ (HMAC-SHA256 ký trên raw body)
┌───────────────────────────▼────────────────────────────┐
│         Django Backend: Cập nhật state='paid'          │
│   (Nếu mất mạng -> Lưu vào Transactional Outbox để retry)│
└────────────────────────────────────────────────────────┘
```

---

## 2. Cấu Hình Tham Số Hệ Thống (System Parameters)

Các khóa cấu hình bảo mật được lưu tại `ir.config_parameter`:

| Tham Số (Key) | Giá Trị Mẫu Local | Ý Nghĩa / Mục Đích |
| :--- | :--- | :--- |
| `travel.webhook_secret` | `<WEBHOOK_SECRET_PLACEHOLDER>` (`star_travels_super_secret_webhook_key_2026`) | Khóa bí mật chung dùng để ký và verify chữ ký HMAC-SHA256 (cho cả 2 chiều Odoo ↔ Django). |
| `travel.inbound_api_key` | `<INBOUND_API_TOKEN_PLACEHOLDER>` (`star_travels_inbound_api_token_2026`) | Token xác thực qua header `Authorization: Bearer <token>` hoặc `X-API-Key`. |
| `travel.public_platform_url` | `http://host.docker.internal:8000` (hoặc domain Django) | Base URL của Django backend để Odoo gọi callback xác nhận VietQR. |
| `star_travels.vietqr_pending_timeout_hours` | `4` | Số giờ tối đa một đơn VietQR ở trạng thái pending trước khi kích hoạt cảnh báo Activity cho kế toán. |

### Cấu hình nhanh qua Odoo Shell:
```python
env['ir.config_parameter'].sudo().set_param('travel.webhook_secret', 'star_travels_super_secret_webhook_key_2026')
env['ir.config_parameter'].sudo().set_param('travel.inbound_api_key', 'star_travels_inbound_api_token_2026')
env['ir.config_parameter'].sudo().set_param('travel.public_platform_url', 'http://localhost:8000')
env['ir.config_parameter'].sudo().set_param('star_travels.vietqr_pending_timeout_hours', '4')
```

---

## 3. Quy Trình Thao Tác Kế Toán: Xác Nhận VietQR Thủ Công

> [!IMPORTANT]
> **Lưu ý nghiệp vụ:** Chuyển khoản VietQR là quy trình thủ công có độ trễ phụ thuộc vào thời điểm khách chuyển và hệ thống ngân hàng xử lý. Kế toán viên cần kiểm tra biến động số dư / sao kê Internet Banking thực tế trước khi xác nhận trên Odoo.

### Bước 1: Tiếp nhận hàng đợi chờ duyệt
1. Vào menu **Kế toán > Bút toán sổ sách > Xác Nhận Chuyển Khoản VietQR** (hoặc menu **Báo cáo > Đối Soát Thanh Toán > Hàng Đợi VietQR Chờ Duyệt**).
2. Danh sách hiển thị các khoản chuyển khoản đang ở trạng thái **Chờ xác nhận**:
   - `Thời gian tạo`: Thời điểm khách quét QR.
   - `Chờ (Giờ)`: Số giờ đơn hàng đang chờ duyệt (đổi màu vàng sau 2 giờ, màu đỏ sau 4 giờ).
   - `Mã Booking`: Mã đơn hàng đối chiếu.
   - `Nội dung CK đối chiếu`: Cú pháp chuyển khoản khách được cấp trên web (VD: `STAR ST-202610-001`).
   - `Số tiền cần chuyển`: Số tiền đơn hàng.

### Bước 2: Kiểm tra sao kê ngân hàng & Xác nhận tiền về
1. Mở app ngân hàng doanh nghiệp hoặc cổng thông báo biến động số dư.
2. Tìm giao dịch có nội dung chuyển khoản khớp với cột **Nội dung CK đối chiếu**.
3. Bấm nút **Xác nhận tiền** trên dòng tương ứng (hoặc mở form xem chi tiết rồi bấm **Xác nhận đã nhận tiền**).
4. Cửa sổ Wizard hiện ra:
   - **Số tiền thực nhận**: Mặc định hiển thị số tiền yêu cầu. Nếu khách chuyển thiếu hoặc thừa, kế toán nhập số tiền thực tế vào tài khoản.
   - **Ngày giờ nhận tiền thực tế**: Nhập thời gian giao dịch trên sao kê.
   - **Mã tham chiếu NH (FT Code)**: Nhập mã bút toán giao dịch ngân hàng (VD: `FT241088921` hoặc số Trace).
   - **Ghi chú đối soát**: *Bắt buộc nhập nếu số tiền thực nhận có sai lệch so với số tiền ban đầu!*
5. Bấm **Xác Nhận Đã Nhận Tiền**:
   - Hệ thống tự động hạch toán Đơn bán hàng, Hóa đơn và Bút toán thanh toán vào sổ cái kế toán.
   - Ghi nhận 1 dòng kiểm toán bất biến vào **Audit Trail**.
   - Tự động gọi API báo sang Django backend để kích hoạt đơn trên website. Nếu kết nối mạng gián đoạn, hệ thống tự động lưu vào **Transactional Outbox** để tiếp tục thử lại (retry), đảm bảo tuyệt đối không mất dữ liệu kế toán.

### Bước 3: Xử lý giao dịch không tìm thấy tiền về (Từ chối)
- Trường hợp khách ấn xác nhận trên web nhưng quá hạn vẫn không thấy tiền vào tài khoản ngân hàng:
  1. Bấm nút **Từ chối**.
  2. Nhập rõ lý do (VD: *Kiểm tra sao kê Vietcombank lúc 17:00 ngày 08/10 không thấy tiền về*).
  3. Bấm **Xác Nhận Từ Chối**: Đơn chuyển sang trạng thái `rejected` và được ghi nhận vào Audit Log.

---

## 4. Kiểm Soát Nội Bộ & Quy Chuẩn Audit Trail

### 1. Tính chất Bất biến (Append-Only Immutability)
- Toàn bộ thay đổi trạng thái đều được ghi nhận vào model `star.travels.payment.audit.log`.
- Phương thức `write()` và `unlink()` của model này được ghi đè để **luôn luôn chặn (raise UserError)**. Ngay cả tài khoản Administrator hay thao tác qua Odoo Developer Mode / Studio cũng **không thể sửa đổi hay xóa bỏ** bất kỳ dòng log nào.

### 2. Tách biệt vai trò (Separation of Duties - SoD)
- Nhóm quyền: `Kế toán Xác Nhận Thanh Toán` (`star_travels_payment_sync.group_payment_confirmer`). Chỉ nhân viên kế toán mới thấy và thực hiện được nút duyệt tiền.
- **Quy tắc ngăn chặn tự phê duyệt**: Một nhân viên kinh doanh (Salesperson) tạo đơn hàng thì chính nhân viên đó **không được phép tự xác nhận thanh toán** cho đơn hàng của mình. Thao tác tự duyệt sẽ bị hệ thống chặn đứng và ghi lại cảnh báo vi phạm SoD vào Audit Trail.

### 3. Xuất Báo Cáo Kiểm Toán (Export Excel)
- Vào menu **Báo cáo > Đối Soát Thanh Toán > Nhật Ký Kiểm Toán (Audit Trail)**.
- Bấm nút **Xuất Báo Cáo Excel (CSV)** trên thanh công cụ để tải file báo cáo đã được định dạng chuẩn UTF-8 BOM, hỗ trợ mở trực tiếp trên Excel hiển thị đầy đủ tiếng Việt.
- Bộ lọc nhanh **Có sai lệch tiền (Discrepancy)** giúp kiểm toán viên lọc ngay các khoản có tiền thực nhận lệch so với tiền yêu cầu.

---

## 5. Danh Sách Endpoint Webhook & Mẫu Gọi API

### 1. Inbound: Django gửi thông tin VietQR Pending sang Odoo
- **Endpoint**: `POST /api/v1/travel/payment-pending`
- **Headers**:
  - `Content-Type: application/json`
  - `X-Signature-SHA256: <hmac_sha256_hex(secret, raw_body)>`
  - `Idempotency-Key: <uuid-v4>`

```json
{
  "event_id": "8a7b6c5d-1111-2222-3333-444455556666",
  "event_type": "payment.pending",
  "data": {
    "payment_id": "tx_vietqr_20261008_001",
    "booking_id": "book-uuid-1234",
    "booking_code": "ST-PQ-001",
    "amount": 2500000.0,
    "bank_transfer_content": "STAR ST-PQ-001",
    "customer_name": "Nguyễn Văn Du Khách",
    "customer_email": "traveler@example.com",
    "customer_phone": "0912345678",
    "salesperson_email": "sales.tour@startravels.vn"
  }
}
```

### 2. Outbound: Odoo gọi sang Django xác nhận tiền đã về
- **Endpoint trên Django**: `POST /api/v1/payments/{payment_id}/vietqr-confirm/`
- **Headers**:
  - `Content-Type: application/json`
  - `X-Signature-SHA256: <hmac_sha256_hex(secret, raw_body)>`
  - `Idempotency-Key: <uuid-v4>`

```json
{
  "payment_id": "tx_vietqr_20261008_001",
  "booking_code": "ST-PQ-001",
  "amount_confirmed": 2500000.0,
  "confirmed_by": "Nguyễn Kế Toán",
  "confirmed_at": "2026-10-08T18:45:00",
  "bank_reference": "FT241088921",
  "source": "manual_odoo_ui"
}
```

---

## 6. Hướng Dẫn Đồng Bộ Secret Key Cho Team DevOps

Khi triển khai môi trường Production / Staging, Team DevOps cần đảm bảo 2 repo có các giá trị biến môi trường đồng bộ như sau:

| Thông Số | Giá Trị Cần Cấu Hình Trên Django | Giá Trị Cần Cấu Hình Trên Odoo (`ir.config_parameter`) |
| :--- | :--- | :--- |
| **Shared Webhook Secret** | `ODOO_WEBHOOK_SECRET` | `travel.webhook_secret` |
| **Inbound API Token** | `ODOO_API_KEY` | `travel.inbound_api_key` |
| **Django Base URL** | `DJANGO_PUBLIC_URL` | `travel.public_platform_url` |
