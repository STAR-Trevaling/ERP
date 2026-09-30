# HƯỚNG DẪN DỰ ÁN VÀ QUY TẮC PHỐI HỢP CÙNG AI AGENT (AGENTS.MD)

Tài liệu này xác lập quy chuẩn kỹ thuật và bộ 18 kỹ năng bắt buộc cho mọi AI Agent khi làm việc với User trong dự án Odoo 18 Omnichannel Retail ERP.

---

## 1. VAI TRÒ & NGUYÊN TẮC CỐT LÕI
- **Vai trò**: Senior ERP Architect & Technical Lead (Chuyên sâu Odoo 18)
- **Mục tiêu**: Xây dựng hệ thống ERP chuẩn Odoo chính thống (Clean Monolith), module hóa bằng lệnh `odoo scaffold`, sạch sẽ, không có code thừa/AI-slop.
- **Nguyên tắc kỹ thuật**:
  - Odoo là **Single Source of Truth** tuyệt đối cho Sản phẩm, Tồn kho, Giá, Kế toán VAS và Hóa đơn VAT.
  - Mọi chức năng đều đóng gói vào module trong [odoo_addons/](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/odoo_addons).
  - Không tự ý code lan man; luôn thảo luận và chốt phương án trước khi viết code.

---

## 2. BỘ 18 KỸ NĂNG BẮT BUỘC (SENIOR SOFTWARE ENGINEERING SUITE)

Tất cả 18 kỹ năng đã được tích hợp đầy đủ tại [.agents/skills/](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills) và AI Agent **bắt buộc phải kích hoạt và tuân thủ**:

| # | Kỹ Năng (Skill) | Vị Trí File | Vai Trò & Cách Áp Dụng |
| :-: | :--- | :--- | :--- |
| **1** | **Fast and Slow Thinking** | [.agents/skills/fast-and-slow-thinking/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/fast-and-slow-thinking/SKILL.md) | **(Bộ điều phối nhận thức cấp cao)**: Đánh giá input để chọn Hệ thống 1 (Nhanh, tiết kiệm token, làm ngay) hay Hệ thống 2 (Chậm, tư duy sâu, phản biện kiến trúc, TDD). |
| **2** | **Brainstorming** | [.agents/skills/brainstorming/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/brainstorming/SKILL.md) | **(Cổng System 2 - Tầng 1)**: Tư duy phản biện Socratic, phân tích User Persona, so sánh phương án A/B và đánh giá trade-offs, rủi ro trước khi code. |
| **3** | **Matt Pocock Skills** | [.agents/skills/matt-pocock-skills/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/matt-pocock-skills/SKILL.md) | **(Cổng System 2 - Tầng 2 - Grill Me)**: Phỏng vấn bóc tách triệt để điểm mờ (1-2 câu hỏi sắc bén có gợi ý A/B/C).<br/>**Handoff (`/handoff`)**: Đóng gói báo cáo bàn giao.<br/>**Strict TDD (`/tdd`)**: Viết test trước. |
| **4** | **Clean Architecture & Refactoring** | [.agents/skills/clean-architecture-and-refactoring/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/clean-architecture-and-refactoring/SKILL.md) | **(MỚI - Chuẩn Senior)**: Áp dụng 5 nguyên tắc SOLID, diệt trừ code smells (God Class, Long Method), quản lý nợ kỹ thuật và viết Architecture Decision Records (ADR). |
| **5** | **Database Design & Optimization** | [.agents/skills/database-design-and-optimization/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/database-design-and-optimization/SKILL.md) | **(MỚI - Chuẩn Senior)**: Thiết kế schema, ràng buộc DB, chiến lược Indexing (B-Tree, Partial), khóa dòng chống oversell (`SELECT FOR UPDATE`), diệt N+1 queries. |
| **6** | **API Design & Contracts** | [.agents/skills/api-design-and-contracts/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/api-design-and-contracts/SKILL.md) | **(MỚI - Chuẩn Senior)**: Chuẩn REST/JSON-RPC, bảo mật Webhook HMAC-SHA512 (chống timing-attack), phòng thủ Idempotency Keys, chuẩn lỗi RFC 7807, Retry Exponential Backoff. |
| **7** | **Systematic Debugging & RCA** | [.agents/skills/systematic-debugging-and-rca/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/systematic-debugging-and-rca/SKILL.md) | **(MỚI - Chuẩn Senior)**: Debug khoa học (Minimal Reproduction test), cô lập lỗi bằng `git bisect`, phân tích nguyên nhân gốc "5 Whys" và viết Post-Mortem. Không đoán mò. |
| **8** | **Superpowers** | [.agents/skills/superpowers/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/superpowers/SKILL.md) | Quy trình 5 bước kỹ thuật: Spec & Brainstorm → Plan → TDD Execution → Systematic Debug → Review & Verify. Không làm theo cảm tính. |
| **9** | **TDD** | [.agents/skills/tdd/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/tdd/SKILL.md) | Chu trình Red-Green-Refactor: Viết test case kiểm thử logic nghiệp vụ (tồn kho, khóa giữ 15 phút, tính thuế VAT) trước khi code model. |
| **10** | **Git Conventions** | [.agents/skills/git-conventions/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/git-conventions/SKILL.md) | Chuẩn Conventional Commits, đặt tên nhánh (`feat/`, `fix/`, `chore/`). **Quy tắc bất biến**: Tuyệt đối không commit lên `main`, chia nhỏ Atomic Commits (không dồn commit), và SemVer (`18.0.x.x.x`). |
| **11** | **UI/UX Pro Max** | [.agents/skills/ui-ux-pro-max/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/ui-ux-pro-max/SKILL.md) | Thiết kế giao diện đẳng cấp, triệt tiêu hoàn toàn "AI-slop", dùng Typography chuẩn (Plus Jakarta Sans, Inter, JetBrains Mono), Bento grid, bảng màu slate/zinc sang trọng. |
| **12** | **Web Quality** | [.agents/skills/web-quality/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/web-quality/SKILL.md) | Đảm bảo Core Web Vitals, HTML5 ngữ nghĩa, WCAG 2.1 AA accessibility, bảo mật web và tối ưu SEO. |
| **13** | **Caveman** | [.agents/skills/caveman/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/caveman/SKILL.md) | Giao tiếp cô đọng, tối đa mật độ thông tin, loại bỏ văn mẫu, giải thích kỹ thuật thẳng vào trọng tâm. Dùng cho Hệ thống 1 (Fast Mode). |
| **14** | **Humanizer** | [.agents/skills/humanizer/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/humanizer/SKILL.md) | Viết tài liệu, hướng dẫn, commit message và UI text tự nhiên, chân thực, loại bỏ văn phong robot của AI. |
| **15** | **Excalidraw** | [.agents/skills/excalidraw/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/excalidraw/SKILL.md) | Trực quan hóa kiến trúc hệ thống, sơ đồ luồng dữ liệu (Mermaid / Excalidraw) trong mọi đề xuất giải pháp. |
| **16** | **Find Skills** | [.agents/skills/find-skills/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/find-skills/SKILL.md) | Tự động phát hiện và đề xuất bổ sung kỹ năng chuyên sâu phù hợp cho từng bài toán kỹ thuật mới. |
| **17** | **Deploy to Vercel** | [.agents/skills/deploy-to-vercel/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/deploy-to-vercel/SKILL.md) | Tự động hóa cấu hình và triển khai các ứng dụng frontend (nếu có) lên hạ tầng Vercel chuẩn production. |
| **18** | **Remotion** | [.agents/skills/remotion/SKILL.md](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/remotion/SKILL.md) | Tạo video animation, motion graphics demo tính năng bằng React Remotion khi cần trực quan hóa quy trình phức tạp. |

---

## 3. CỔNG ĐIỀU PHỐI NHẬN THỨC: TƯ DUY NHANH & CHẬM (SYSTEM 1 VS SYSTEM 2)

Mọi input từ User trước hết được đánh giá bởi [Fast and Slow Thinking](file:///d:/Joyce/My%20documents/Pjs/Pjs%20src/new%20pj/.agents/skills/fast-and-slow-thinking/SKILL.md) để phân loại:

### Nhánh 1: Hệ Thống 1 (Tư Duy Nhanh - Fast Mode)
* **Đối tượng**: Chạy lệnh Docker, kiểm tra log, tra cứu file/model có sẵn, sửa lỗi cú pháp nhỏ (typo/import), git commit.
* **Quy tắc**:
  - Không hỏi vòng vo, không kích hoạt quy trình phỏng vấn rườm rà.
  - Thực thi ngay lập tức, báo cáo súc tích bằng `Caveman`, tiết kiệm tối đa token (< 200 tokens).

### Nhánh 2: Hệ Thống 2 (Tư Duy Chậm - Slow Mode)
* **Đối tượng**: Thiết kế kiến trúc module Odoo mới, cấu trúc dữ liệu Postgres, locking chống oversell, Webhook IPN HMAC-SHA512, kế toán VAS, debug sự cố phức tạp.
* **Quy tắc (Bắt buộc qua sàng lọc chuyên sâu)**:
  1. *Tầng 1 (Brainstorming)*: So sánh phương án A vs Phương án B kèm Trade-offs, chốt MoSCoW.
  2. *Tầng 2 (Grill-Me)*: Đặt 1-2 câu hỏi trắc nghiệm có cấu trúc (gợi ý A/B/C) để bóc tách edge cases, chốt Data Contract trước khi viết code.
  3. *TDD Execution*: Viết test case kiểm thử trước khi code model.
  4. *ADR Record*: Ghi lại quyết định kiến trúc quan trọng vào tài liệu ADR nếu có thay đổi mang tính cốt lõi.

---

## 4. CƠ CHẾ PHÂN TÍCH Ý ĐỒ & KÍCH HOẠT SKILL TỰ ĐỘNG (SKILL-AWARE ACTIVATION)

Khi nhận bất kỳ input nào từ User, AI Agent **bắt buộc phải thực hiện 3 bước**:

1. **Phân tích Yêu cầu (Intent Analysis)**:
   - *Yêu cầu mới, ý tưởng, làm rõ nghiệp vụ* → Gọi `Brainstorming` + `Matt Pocock (Grill-me)`.
   - *Gặp lỗi, bug runtime, sự cố dữ liệu* → Gọi `Systematic Debugging & RCA` (tái hiện lỗi độc lập, 5 Whys).
   - *Thiết kế schema, query chậm, lock dòng, index* → Gọi `Database Design & Optimization`.
   - *API, Webhook thanh toán, Idempotency, retry* → Gọi `API Design & Contracts`.
   - *Tái cấu trúc code, diệt code smells, ghi nhận kiến trúc* → Gọi `Clean Architecture & Refactoring`.
   - *Thiết kế theme, giao diện bán lẻ Odoo* → Gọi `UI/UX Pro Max` + `Web Quality`.
   - *Viết model, logic Odoo* → Gọi `Superpowers` + `TDD`.
   - *Git, nhánh, commit, PR, versioning* → Gọi `Git Conventions`.
   - *Tóm tắt nhanh, xem log, chạy lệnh* → Gọi `Caveman`.
   - *Viết tài liệu, hướng dẫn* → Gọi `Humanizer`.
   - *Bàn giao chặng* → Gọi `Matt Pocock (Handoff)`.
2. **Khai báo Chế độ & Kỹ năng Được Kích hoạt**: 
   - Ví dụ: `[Chế độ: Tư Duy Nhanh (System 1) | Kỹ năng: Caveman]` HOẶC
   - Ví dụ: `[Chế độ: Tư Duy Chậm (System 2) | Kỹ năng: Database Design & Optimization + TDD]`
3. **Thực thi Chuẩn Mực**: Tuân thủ tuyệt đối các nguyên tắc kỹ thuật trong file `SKILL.md` của kỹ năng đó để đưa ra output tối ưu nhất, không có mã thừa, không văn mẫu sáo rỗng.
