# RETAIL ERP & E-COMMERCE INTEGRATION SYSTEM

Hệ thống ERP bán lẻ đa kênh chuẩn nghiệp vụ Việt Nam tích hợp giữa **Website E-Commerce**, **FastAPI Middleware** và **Odoo 18 Core ERP**.

---

## 1. TỔNG QUAN DEPENDENCIES & MÔI TRƯỜNG (ENV)

Hệ thống đã được thiết lập đầy đủ 100% các biến môi trường và gói phụ thuộc:

### A. File cấu hình môi trường (.env)
- **[.env (Root)](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.env)**: Cấu hình chung cho Docker Compose, Odoo, PostgreSQL, và đường dẫn `PYTHONPATH`.
- **[backend/.env](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/backend/.env)**: Cấu hình FastAPI Middleware, Odoo JSON-RPC credentials, cổng thanh toán VNPay / MoMo và SQLite/PostgreSQL Database URL.
- **[frontend/.env](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/frontend/.env)**: Cấu hình `VITE_API_BASE_URL=http://localhost:8000/api/v1`.
- **[.env.example](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.env.example)**: File mẫu tham chiếu khi bàn giao môi trường Production.

### B. Dependencies Backend (Python 3.12 - 3.14)
Nằm trong `backend/requirements.txt` và đã cài đặt sẵn trong virtualenv `.venv`:
- `fastapi` & `uvicorn[standard]`: Async Web Framework & ASGI Server.
- `pydantic` & `pydantic-settings`: Validate data contracts & quản lý biến môi trường.
- `httpx`: Non-blocking HTTP client gọi JSON-RPC sang Odoo 18.
- `sqlalchemy` & `greenlet` & `aiosqlite`: ORM AsyncIO lưu vết Idempotency & Webhook IPN logs.
- `pytest` & `pytest-asyncio`: Bộ kiểm thử tự động TDD (7/7 tests passed).

### C. Dependencies Frontend (ReactJS + TypeScript)
Nằm trong `frontend/package.json` và đã cài đặt sẵn trong `frontend/node_modules`:
- `react` & `react-dom` (v18)
- `lucide-react`: Bộ icon hiện đại.
- `vite` & `@vitejs/plugin-react`: Bundler tốc độ cao.
- `typescript`: Kiểm tra kiểu tĩnh (0 errors).

### D. Hạ tầng Odoo 18 (Docker)
- `odoo:18.0` (Multi-workers).
- `postgres:16-alpine`.
- `nginx:alpine` (Reverse Proxy, SSL, Rate limiting).
- Addon: `custom_ecommerce_bridge` (Atomic Order & Stock Lock).

---

## 2. HƯỚNG DẪN KHỞI CHẠY (QUICK START)

### Bước 1: Khởi động Odoo 18 & Database
```bash
docker compose up -d
```
*Truy cập `http://localhost:8069`, vào Apps bật Developer Mode, nhấn **Update Apps List** và cài đặt module `custom_ecommerce_bridge`.*

### Bước 2: Khởi chạy FastAPI Middleware (Port 8000)
```bash
cd backend
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```
*Tài liệu Swagger UI tương tác trực tiếp tại: `http://localhost:8000/docs`*

### Bước 3: Khởi chạy Frontend ReactJS (Port 5173)
```bash
cd frontend
npm run dev
```
*Truy cập giao diện đặt hàng tại: `http://localhost:5173`*

### Bước 4: Chạy kiểm thử tự động (TDD Suite)
```bash
.\.venv\Scripts\pytest -v backend
```

---

## 3. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
new pj/
├── .env                              # Biến môi trường tổng thể
├── docker-compose.yml                # Odoo 18 + Postgres + Nginx
├── config/
│   ├── odoo.conf                     # Cấu hình Odoo multi-workers
│   └── nginx/nginx.conf              # Nginx reverse proxy & rate limit
├── odoo_addons/
│   └── custom_ecommerce_bridge/      # Thin Addon Odoo 18 (Atomic Stock Lock)
├── backend/
│   ├── .env                          # Biến môi trường FastAPI
│   ├── requirements.txt              # Dependencies Python
│   ├── app/                          # Source code FastAPI
│   └── tests/                        # 7 TDD Test Cases
├── frontend/
│   ├── .env                          # Biến môi trường Vite
│   ├── package.json                  # Dependencies React TS
│   └── src/                          # Checkout Portal & Hold Timer
├── RECONCILIATION.md                 # Quy trình đối soát 3 bên & VAS
├── PROJECT_PLAN.md                   # Tiến độ triển khai 5 Phase
└── HANDOFF.md                        # Tài liệu bàn giao kỹ thuật
```
