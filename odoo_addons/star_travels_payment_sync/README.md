# Star Travels - Payment & Reconciliation Sync (`star_travels_payment_sync`)

Module Odoo 18 tiếp nhận sự kiện thanh toán và hoàn tiền trực tuyến từ nền tảng công cộng (Django Backend) qua Webhook, tự động hạch toán kế toán và hỗ trợ đối soát sao kê bảng kê cổng thanh toán.

---

## 1. Tính Năng Cốt Lõi

1. **Tiếp nhận Webhook Thanh toán (`POST /api/v1/travel/booking-paid`)**:
   - Xác thực bảo mật đa tầng: Khóa API Bearer / Header `X-API-Key` và Chữ ký mật mã HMAC-SHA256 (`X-Signature-SHA256`).
   - Phòng thủ tấn công phát lại (Replay Attack) và cơ chế Idempotent tuyệt đối qua model `star.travels.webhook.log`.
   - Tự động tạo hoặc cập nhật đối tác khách hàng (`res.partner`).
   - Tự động tạo và xác nhận Đơn bán hàng (`sale.order`) với mã booking tham chiếu.
   - Tự động tạo và ghi sổ Hóa đơn khách hàng (`account.move` - `out_invoice`).
   - Tự động đăng ký và ghi sổ Thanh toán (`account.payment`) trên Sổ nhật ký cổng tương ứng (VNPay, MoMo, ZaloPay).
   - Tự động đối trừ công nợ (Auto-reconciliation) giữa hóa đơn và bút toán thanh toán.

2. **Tiếp nhận Webhook Hoàn tiền (`POST /api/v1/travel/booking-refunded`)**:
   - Tự động tìm hóa đơn gốc của booking tương ứng.
   - Tự động tạo và ghi sổ Hóa đơn điều chỉnh giảm / Hoàn tiền (Credit Note - `out_refund`).
   - Tự động tạo bút toán chi tiền hoàn trả (`account.payment` - `outbound`).
   - Tự động đối trừ công nợ giữa Credit Note và bút toán chi tiền.

3. **Sổ Nhật Ký Thanh Toán Riêng Biệt (Dedicated Gateway Journals)**:
   - Sổ VNPay Gateway (`VNPAY`, loại `bank`)
   - Sổ MoMo E-Wallet (`MOMO`, loại `bank`)
   - Sổ ZaloPay E-Wallet (`ZALOP`, loại `bank`)

4. **Đối Soát Bảng Kê Cổng Thanh Toán (Statement Reconciliation Wizard)**:
   - Wizard `star.travels.reconciliation.wizard` cho phép kế toán tải lên file sao kê định dạng CSV/Excel do VNPay / MoMo cung cấp.
   - Tự động trích xuất mã giao dịch cổng (`gateway_transaction_id`) và số tiền.
   - Tự động đối chiếu với các bút toán `account.payment` trong hệ thống:
     * Khớp hoàn toàn: Chuyển trạng thái `x_reconciliation_state` sang `matched`, ghi nhận ngày đối soát.
     * Sai lệch hoặc thiếu: Đánh dấu `unmatched`, thống kê tổng số tiền sai lệch để kế toán xử lý.

5. **Tự Động Giám Sát & Cảnh Báo (Scheduled Action)**:
   - Cron job hàng ngày kiểm tra các giao dịch thanh toán cổng chưa đối soát quá 2 ngày và gửi cảnh báo đến kế toán viên.

---

## 2. Đặc Tả Webhook API (API Contracts)

### Endpoint 1: Thanh toán thành công (`booking.paid`)
- **URL**: `POST /api/v1/travel/booking-paid`
- **Headers**:
  * `Content-Type: application/json`
  * `X-Signature-SHA256: <hmac_hex_digest>`
  * `Idempotency-Key: <uuid>`
- **Payload mẫu**:
```json
{
  "event_id": "c5f590fc-25ee-4614-a957-3a05953051da",
  "event_type": "booking.paid",
  "data": {
    "booking_id": "11111111-2222-3333-4444-555555555555",
    "booking_code": "ST-PQ-001",
    "customer": {
      "name": "Nguyễn Văn Du Khách",
      "email": "traveler@example.com",
      "phone": "0912345678"
    },
    "items": [
      {
        "tour_slug": "tour-phu-quoc-sunset",
        "title": "Tour Phú Quốc Sunset Cruise",
        "adults": 2,
        "children": 1,
        "price_adult": 1500000.0,
        "price_child": 1000000.0
      }
    ],
    "payment": {
      "gateway": "vnpay",
      "gateway_transaction_id": "VNP14889211",
      "amount": 4000000.0
    }
  }
}
```

### Endpoint 2: Hoàn tiền booking (`booking.refunded`)
- **URL**: `POST /api/v1/travel/booking-refunded`
- **Payload mẫu**:
```json
{
  "event_id": "d8a113bc-79f9-42b8-9333-4f93498b8712",
  "event_type": "booking.refunded",
  "data": {
    "booking_id": "11111111-2222-3333-4444-555555555555",
    "refund_amount": 2000000.0,
    "reason": "Khách hủy vé theo chính sách hoàn tiền 50%",
    "refund_transaction_id": "RF-VNP-998811",
    "gateway": "vnpay"
  }
}
```

---

## 3. Cấu Hình Tham Số Hệ Thống

Các tham số trong `ir.config_parameter`:
- `travel.webhook_secret`: Khóa bí mật dùng để tính toán chữ ký HMAC-SHA256. Mặc định kiểm thử: `star_travels_super_secret_webhook_key_2026`.
- `travel.inbound_api_key`: Khóa API dùng để xác thực Bearer token hoặc header `X-API-Key`.
