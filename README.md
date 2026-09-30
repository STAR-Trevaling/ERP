# ODOO 18 RETAIL ERP SYSTEM

Hệ thống ERP Quản trị Bán lẻ & Thương mại Đa kênh xây dựng trực tiếp trên nền tảng **Odoo 18 Chính Thống** (Official Odoo 18 Community / Enterprise).

---

## 1. HẠ TẦNG & DỊCH VỤ

Dự án sử dụng Docker theo chuẩn tài liệu chính thức của Odoo (Official Odoo Docker Setup):

* **Odoo Version**: `odoo:18.0`
* **PostgreSQL Database**: `postgres:16-alpine`
* **Cấu hình Odoo**: [config/odoo.conf](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/config/odoo.conf)
* **Thư mục Addons tùy biến**: [odoo_addons/](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/odoo_addons) (được mount trực tiếp vào container tại `/mnt/extra-addons`)

---

## 2. KHỞI CHẠY HỆ THỐNG

### Bước 1: Khởi động container Odoo & Database
```bash
docker compose up -d
```

### Bước 2: Truy cập ứng dụng
* **URL**: [http://localhost:8069](http://localhost:8069)
* **Database**: `odoo_retail`
* **Admin Login**: `admin`
* **Admin Password**: `admin`
* **Master Password**: `admin_master_secret_2026`

---

## 3. CÁCH TẠO MODULE TÙY BIẾN THEO CHUẨN ODOO (SCAFFOLD)

Để khởi tạo module mới theo đúng chuẩn Odoo Developer Docs:
```bash
docker compose exec odoo odoo scaffold <ten_module> /mnt/extra-addons
```
Module sẽ tự động được sinh ra trong thư mục `odoo_addons/` với đầy đủ cấu trúc: `models/`, `views/`, `controllers/`, `security/`, `__manifest__.py`.
