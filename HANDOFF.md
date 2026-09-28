# SESSION HANDOFF: ODOO 18 & E-COMMERCE RETAIL ERP INTEGRATION

## 1. Goal & Context
- Xây dựng hệ sinh thái ERP chuẩn nghiệp vụ bán lẻ thương mại đa kênh tại Việt Nam.
- **Odoo 18 Core ERP**: Single Source of Truth cho Tồn kho, Giá, Kế toán VAS & Hóa đơn VAT.
- **FastAPI Middleware**: Non-blocking Async layer điều phối luồng, quản lý Idempotency, verify Webhook chữ ký và gọi Odoo qua JSON-RPC an toàn.
- **ReactJS + TypeScript**: Cổng đặt hàng hiện đại với cơ chế giữ tồn kho tạm thời (15-Minute Stock Hold).
- Áp dụng bộ kỹ năng **Awesome-Claude-Skills** (Superpowers, Matt Pocock, TDD, Excalidraw, UI/UX Pro Max, Web Quality).

---

## 2. Completed Milestones

### Phase 1: Hạ tầng Docker & Scaffolding
- [x] [docker-compose.yml](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/docker-compose.yml): Odoo 18 + PostgreSQL 16 + Nginx Reverse Proxy.
- [x] [config/odoo.conf](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/config/odoo.conf): Cấu hình Multi-workers (4 workers), Proxy mode và Data limits.
- [x] [config/nginx/nginx.conf](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/config/nginx/nginx.conf): Bảo vệ Odoo, rate-limiting API và chặn truy cập Database Manager từ internet.

### Phase 2: Odoo 18 Thin Custom Addon (`custom_ecommerce_bridge`)
- [x] [__manifest__.py](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/odoo_addons/custom_ecommerce_bridge/__manifest__.py): Manifest Odoo 18 phụ thuộc `sale`, `stock`, `account`.
- [x] [models/sale_order.py](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/odoo_addons/custom_ecommerce_bridge/models/sale_order.py):
  - `action_create_web_order_atomic()`: Tạo partner, kiểm tra free stock, tạo SO và confirm để khóa giữ tồn kho (15 phút) trong 1 Transaction nguyên khối.
  - `action_confirm_web_payment()`: Chuyển trạng thái Paid, phát hành hóa đơn VAT và hạch toán đúng Payment Journal (VNPAY, MOMO...).
  - `action_cron_release_expired_web_orders()`: Tự động hủy đơn quá hạn và giải phóng reserved stock quants.
- [x] [data/ir_cron_data.xml](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/odoo_addons/custom_ecommerce_bridge/data/ir_cron_data.xml): Scheduled action chạy định kỳ mỗi 5 phút.

### Phase 3: FastAPI Backend & Webhook Integration
- [x] [app/core/odoo_client.py](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/backend/app/core/odoo_client.py): Async JSON-RPC Client với re-auth & error handling.
- [x] [app/services/payment_verifier.py](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/backend/app/services/payment_verifier.py): Verify chữ ký HMAC-SHA512 (VNPay) & HMAC-SHA256 (MoMo).
- [x] [app/api/v1/endpoints/orders.py](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/backend/app/api/v1/endpoints/orders.py): Checkout endpoint với Idempotency guard.
- [x] [app/api/v1/endpoints/webhooks.py](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/backend/app/api/v1/endpoints/webhooks.py): Xử lý IPN 200 OK ngay lập tức + BackgroundTasks đồng bộ Odoo.
- [x] **Test Suite TDD**: **7/7 tests PASSED** (Kiểm thử chữ ký, Idempotency, Checkout OOS, Mock RPC).

### Phase 4: Frontend ReactJS + TypeScript
- [x] [frontend/src/App.tsx](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/frontend/src/App.tsx): Màn hình Checkout chuẩn Bento Grid & Dark Glassmorphism, Live 15-Minute Countdown Timer, và Webhook Simulation Sandbox.
- [x] `npm run build`: Production bundle biên dịch thành công 100%.

### Phase 5: Hướng dẫn Vận hành & Đối soát
- [x] [RECONCILIATION.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/RECONCILIATION.md): Hướng dẫn đối soát 3 bên và hạch toán kế toán VAS.

---

## 3. Current State & Active Changes
- Toàn bộ source code đã được khởi tạo sạch sẽ tại workspace `new pj/`.
- Môi trường Python virtualenv `.venv` đã cài đặt đầy đủ và pass toàn bộ pytest.
- Môi trường Node.js frontend đã cài đặt đầy đủ node_modules và build sẵn sàng.

---

## 4. Known Gotchas & Decisions Made
1. **Stock Reservation**: Sử dụng native `order.action_confirm()` trong Odoo để sinh `stock.move` và khóa giữ `reserved_quantity`. Điều này giúp nhân viên POS tại cửa hàng vật lý thấy ngay `free_qty = on_hand - reserved` bị giảm, triệt tiêu 100% rủi ro oversell.
2. **Idempotency Multi-layer**: 
   - Layer 1 tại FastAPI DB (`idempotency_records` & `payment_transactions`).
   - Layer 2 tại Odoo Addon (`web_order_ref` duplicate check & `web_payment_status == 'paid'` check).
3. **Kế toán VAS**: Phí cổng thanh toán hạch toán Nợ 6425 / Có 112, không bao giờ trừ trực tiếp vào Doanh thu 511.

---

## 5. Immediate Next Steps
1. **Khởi chạy Docker**:
   ```bash
   docker compose up -d
   ```
2. **Cài đặt Addon Odoo 18**:
   - Truy cập Odoo Apps, bật Developer Mode, nhấn **Update Apps List**.
   - Cài đặt module `custom_ecommerce_bridge`.
3. **Khởi chạy FastAPI Backend**:
   ```bash
   cd backend
   .\.venv\Scripts\uvicorn app.main:app --reload --port 8000
   ```
4. **Khởi chạy Frontend React**:
   ```bash
   cd frontend
   npm run dev
   ```
