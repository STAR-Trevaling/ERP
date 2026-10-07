# Scripts & Automation Utilities Directory

Thư mục này chứa các scripts tiện ích, tự động hóa cấu hình và nạp dữ liệu (data seeding) cho hệ thống Odoo 18 ERP & Nền tảng STAR Travels.

---

## 1. Dữ liệu Hạt giống (Data Seeding)

### `seed_odoo_cms.py`
* **Mục đích**: Nạp tự động toàn bộ dữ liệu mẫu du lịch Việt Nam (Destinations, Places, Articles) vào Odoo 18 CMS qua XML-RPC.
* **Cách chạy**:
  ```bash
  python scripts/seed_odoo_cms.py
  ```

---

## 2. Tự động hóa Tích hợp Nền tảng (Platform Wiring & Generation)

### `wire_django_integrations.py`
* **Mục đích**: Cập nhật file cấu hình `settings.py` và `urls.py` của Django platform để kích hoạt app `integrations`.

### `wire_nextjs_public_site.py`
* **Mục đích**: Tạo endpoint Webhook Revalidation `/api/revalidate` trên ứng dụng Next.js để làm mới cache khi nhận tín hiệu CMS từ Odoo.

### `generate_django_integrations.py`
* **Mục đích**: Tự động sinh mã nguồn app `integrations` trong Django (Inquiry Model, Outbox Model, Celery Tasks, REST APIs).

### `create_integrations_migration.py`
* **Mục đích**: Tạo database migration khởi tạo các bảng `integrations` trong Django.

---

## 3. Kiểm thử & Xác minh Thủ công (Verification)

### `test_odoo_cms_outbox.py`
* **Mục đích**: Kiểm tra nhanh luồng xuất bản (Publish) Điểm đến qua XML-RPC và kiểm tra bản ghi sinh ra trong bảng Outbox.
* **Cách chạy**:
  ```bash
  python scripts/test_odoo_cms_outbox.py
  ```

### `test_send_inquiry_to_odoo.py`
* **Mục đích**: Gửi thử nghiệm một Inquiry payload được ký bằng chữ ký bí mật HMAC-SHA256 đến endpoint `/api/v1/travel/inquiry`.
* **Cách chạy**:
  ```bash
  python scripts/test_send_inquiry_to_odoo.py
  ```

### `run_pytest_integrations.py`
* **Mục đích**: Kích hoạt bộ kiểm thử `pytest` cho app `integrations` của Django platform.

---

## 4. Bảo trì & Thanh lọc Dữ liệu (Maintenance & Purging)

### `clean_odoo_mock_data.py`
* **Mục đích**: Rà soát và xóa sạch toàn bộ các Leads và Contacts demo bàn ghế, văn phòng của Odoo core (`crm_case_*`, `res_partner_*`) và các mock test tạm thời, bảo toàn nguyên vẹn tài khoản quản trị và dữ liệu du lịch thực.
* **Cách chạy**:
  ```bash
  python scripts/clean_odoo_mock_data.py
  ```

---

## 5. Kiểm tra Tiền Kiểm CI (Local Pre-Flight Runner)

### `run_local_ci.py`
* **Mục đích**: Thực thi nhanh toàn bộ các chặng kiểm tra chất lượng mã nguồn (Ruff linter, XML template parse, JSON contracts validation, Pytest E2E suite) trên môi trường local trước khi commit và push lên GitHub.
* **Cách chạy**:
  ```bash
  python scripts/run_local_ci.py
  ```


