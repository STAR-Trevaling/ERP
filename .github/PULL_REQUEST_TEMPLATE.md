## 1. Mục Tiêu (Objective)
<!-- Mô tả bài toán nghiệp vụ cần giải quyết và lý do thay đổi. -->

## 2. Thay Đổi Chính (Key Changes)
<!-- Liệt kê ngắn gọn các thay đổi trong PR này -->
- [ ] Model / Field / Schema updates:
- [ ] View / UX / Controller routes:
- [ ] API Contracts / Schemas / Outbox:

## 3. Kế Hoạch & Bằng Chứng Kiểm Thử (Test Plan & Verification)
<!-- Đánh dấu các tiêu chí kiểm thử đã pass trước khi gửi PR -->
- [ ] **Linter Check**: `python -m ruff check .` đạt 0 lỗi (All checks passed).
- [ ] **Odoo Native Tests**: Chạy `odoo --test-enable` (21/21 passed, 0 failed, 0 errors).
- [ ] **Live Pytest E2E Suite**: Chạy `python -m pytest tests/ -v` (9/9 passed 100%).
- [ ] **Data Contract Compliance**: JSON Schemas trong `contracts/` hợp lệ và tương thích ngược.

## 4. Tác Động Dữ Liệu & Migrations (Breaking Changes)
- [ ] Có thay đổi cấu trúc bảng database PostgreSQL không?
- [ ] Cần chạy nâng cấp module (`-u <module_name>`) khi deploy không?
- [ ] Có ảnh hưởng đến giao thức API với Public Platform không?
