# SESSION HANDOFF: ODOO 18 CLEAN MONOLITH & OMNICHANNEL PLATFORM INTEGRATION

## 1. Goal & Architectural Overview
- **Hệ thống ERP**: Odoo 18 Clean Monolith (`odoo18_app` + `odoo18_postgres`), phân tách theo 5 decoupled addons: `travel_core`, `travel_cms`, `travel_partner`, `travel_crm`, `travel_integration`.
- **Vai trò**: Odoo là **Single Source of Truth** cho CMS Authoring (vòng đời kiểm duyệt nội dung), CRM Leads (tự động dedup và phân loại nguồn), và Quản lý đối tác B2B.
- **Tích hợp Public Platform**: Kết nối bảo mật qua REST APIs và Webhooks ký bằng HMAC-SHA256, áp dụng Transactional Outbox Pattern và Inbound Idempotency Replay Cache.
- **Chất lượng**: 100% tuân thủ bộ 18 kỹ năng Senior Software Engineering tại [AGENTS.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/ERP/AGENTS.md).

---

## 2. Infrastructure & Service Status
- **Docker Containers**:
  - `odoo18_app` (Odoo 18.0) đang chạy trên cổng `8069:8069`.
  - `odoo18_postgres` (PostgreSQL 16) đang hoạt động healthy.
- **Database**: `odoo_travel` đã được migrate và seed dữ liệu du lịch Việt Nam mẫu.
- **Linter & Type Checking**:
  - Ruff Linter: `All checks passed!` (0 errors).
  - Pyright: `0 errors`.

---

## 3. Test Suite Verification Matrix (30/30 Tests Passing)
| Tầng kiểm thử | Runner / Framework | Số lượng | Kết quả |
| :--- | :--- | :---: | :---: |
| **Odoo Native Unit Tests** | Docker `odoo --test-enable` (DB Transaction Rollback) | 21 |  **21/21 PASSED** (0 failures, 0 errors) |
| **Live E2E API Contracts** | Host `pytest tests/test_e2e_api_contracts.py` | 5 |  **5/5 PASSED** (1.10s) |
| **Live E2E CMS & Partner** | Host `pytest tests/test_e2e_cms_workflow.py` | 4 |  **4/4 PASSED** (1.34s) |
| **Tổng cộng** | | **30** |  **100% GREEN** |

---

## 4. Codebase Directory Organization
```text
ERP/
├── .agents/                    # 18 Senior Skills & Quy chuẩn AGENTS.md
├── config/                     # Cấu hình Nginx reverse proxy & Odoo 18
├── contracts/                  # JSON Schemas & OpenAPI 3.0 specs
├── docs/                       # Tài liệu kỹ thuật
│   ├── adr/                    # ADR-001 (Stock), ADR-002 (Clean Monolith), ADR-003 (Outbox & Idempotency)
│   └── specs/                  # Đặc tả kỹ thuật & integration prompts
├── odoo_addons/                # 5 Addons Odoo 18 Clean Monolith + Muk Web Themes
├── scripts/                    # Scripts nạp dữ liệu (seed_odoo_cms.py) kèm scripts/README.md
├── tests/                      # Bộ kiểm thử Pytest E2E live HTTP & XML-RPC
├── docker-compose.yml          # Hạ tầng container chuẩn hóa
├── pyproject.toml              # Cấu hình Ruff & Pyrefly
├── pytest.ini                  # Cấu hình Pytest
└── README.md                   # Tài liệu Showcase dự án chuẩn Senior SE
```

---

## 5. Quick Verification Commands
```powershell
# 1. Chạy Odoo Native Test Suite
docker exec -i odoo18_app odoo -d odoo_travel --http-port 8070 `
  --test-enable `
  --test-tags /travel_core,/travel_cms,/travel_partner,/travel_crm,/travel_integration `
  --stop-after-init --log-level=test

# 2. Chạy Pytest E2E Suite
python -m pytest tests -v

# 3. Kiểm tra code quality
python -m ruff check .
```
