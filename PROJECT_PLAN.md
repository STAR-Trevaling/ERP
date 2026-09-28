# KẾ HOẠCH TRIỂN KHAI HỆ THỐNG ERP ODOO 18 & WEBSITE E-COMMERCE

## TỔNG QUAN KIẾN TRÚC
- **Backoffice ERP**: Odoo 18 (Multi-workers, PostgreSQL 16) chạy trong Docker cô lập.
- **Middleware / Website BE**: Python FastAPI (Async I/O, Pydantic, BackgroundTasks, Idempotency DB).
- **Frontend**: ReactJS + TypeScript (Vite).
- **Cơ chế**: Native RPC + 1 Thin Custom Addon (`custom_ecommerce_bridge`) đảm bảo giao dịch nguyên khối (Atomic Transaction) và tự giải phóng tồn kho sau 15 phút.

---

## LỘ TRÌNH TRIỂN KHAI THEO PHASE

### PHASE 1: HẠ TẦNG DOCKER & BỘ KHUNG DỰ ÁN (SCAFFOLDING) - [HOÀN THÀNH]
- [x] **Task 1.1**: Tạo `docker-compose.yml` gồm Odoo 18, PostgreSQL 16, Nginx Reverse Proxy.
- [x] **Task 1.2**: Tạo file cấu hình `odoo.conf`, `nginx.conf`, template biến môi trường `.env.example`.
- [x] **Task 1.3**: Khởi tạo cấu trúc thư mục chuẩn cho Backend (FastAPI), Odoo Addon, và Frontend.

### PHASE 2: THIN CUSTOM ADDON ODOO 18 (`custom_ecommerce_bridge`) - [HOÀN THÀNH]
- [x] **Task 2.1**: Khởi tạo module structure (`__manifest__.py`, `__init__.py`, `ir.model.access.csv`).
- [x] **Task 2.2**: Kế thừa `sale.order` với các trường phục vụ Web: `web_order_ref`, `web_payment_status`, `hold_expires_at`, `gateway_transaction_id`.
- [x] **Task 2.3**: Viết logic Atomic RPC:
  - `action_create_web_order_atomic()`: Tìm/tạo khách hàng, tạo Sale Order, tạo Stock Move để giữ chỗ tồn kho (Hold Stock) trong 1 Transaction duy nhất.
  - `action_confirm_web_payment()`: Xác nhận đơn khi nhận webhook, ghi nhận bút toán `account.payment` theo Journal của cổng thanh toán.
- [x] **Task 2.4**: Tạo Scheduled Action (`ir.cron`) tự động quét và hủy đơn quá 15 phút (Release reserved stock).

### PHASE 3: FASTAPI MIDDLEWARE & WEBHOOK HANDLER - [HOÀN THÀNH]
- [x] **Task 3.1**: Cấu hình FastAPI (`config.py`, `main.py`, dependencies `requirements.txt`).
- [x] **Task 3.2**: Xây dựng `OdooRPCClient` (kết nối JSON-RPC/XML-RPC với Odoo an toàn, có retry và error handling).
- [x] **Task 3.3**: Xây dựng Database Schema lưu vết Idempotency, Request Log và Transaction status.
- [x] **Task 3.4**: Viết Endpoint Checkout (`POST /api/v1/orders/checkout`) gọi sang Odoo atomic API.
- [x] **Task 3.5**: Viết Webhook Handler (`POST /api/v1/webhooks/{gateway}`) verify chữ ký, kiểm tra idempotency và điều phối BackgroundTasks cập nhật Odoo.
- [x] **Task 3.6**: Viết bộ Unit/Integration Tests (Pytest) theo kỷ luật TDD cho Webhook & Idempotency (**7/7 tests PASSED**).

### PHASE 4: REACTJS TYPESCRIPT FRONTEND (DEMO PORTAL) - [HOÀN THÀNH]
- [x] **Task 4.1**: Khởi tạo khung giao diện React + TypeScript + Vite.
- [x] **Task 4.2**: Màn hình Checkout hiển thị thời gian giữ giỏ hàng (15-minute countdown timer) và Sandbox mô phỏng Webhook thanh toán.
- [x] **Task 4.3**: Kiểm tra build production `npm run build` thành công 100%.

### PHASE 5: TÀI LIỆU VẬN HÀNH & ĐỐI SOÁT (RECONCILIATION & HANDOFF) - [HOÀN THÀNH]
- [x] **Task 5.1**: Quy trình đối soát chéo (Reconciliation logic) giữa Web DB và Odoo Accounting Journal tại `RECONCILIATION.md`.
- [x] **Task 5.2**: Tài liệu Handoff chuẩn Matt Pocock (`HANDOFF.md`) hướng dẫn chạy và vận hành.
