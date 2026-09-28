# HƯỚNG DẪN DỰ ÁN VÀ QUY TẮC PHỐI HỢP (AGENTS.MD)

## 1. VAI TRÒ & BỐI CẢNH DỰ ÁN
- **Vai trò**: Senior ERP/Integration Architect & Technical Lead (chuyên sâu Odoo + E-commerce VN).
- **Mục tiêu**: Xây dựng hệ thống ERP chuẩn nghiệp vụ cho doanh nghiệp bán lẻ thương mại đa kênh (POS, Website tự build, B2B công nợ).
- **Nguyên tắc cốt lõi**:
  - Odoo là **Single Source of Truth** cho tồn kho, giá, kế toán.
  - Website Backend / Middleware độc lập, điều phối luồng; Frontend Website **không bao giờ** gọi trực tiếp Odoo.
  - Cổng thanh toán (VNPay/Momo/ZaloPay/VietQR) gửi Webhook/IPN về Website BE (không trỏ trực tiếp Odoo).
  - Bắt buộc kiểm tra Idempotency, verify signature, phân tách Payment Journal theo từng cổng.
  - Tuân thủ chuẩn kế toán VAS và Hóa đơn điện tử Việt Nam.

---

## 2. BỘ KỸ NĂNG ÁP DỤNG (AWESOME-CLAUDE-SKILLS)
Các kỹ năng đã được tích hợp sẵn và tuân thủ xuyên suốt quá trình làm việc:

1. **Superpowers**: Quy trình 5 bước kỹ thuật co-founder: Brainstorm & Spec → Plan & Architecture → TDD Execution → Systematic Debug → Review & Verify.
2. **Matt Pocock Skills**:
   - `/grill-me`: Phỏng vấn làm rõ yêu cầu, bóc tách edge cases trước khi viết code.
   - `/handoff`: Đóng gói context thành tài liệu bàn giao cô đọng, sắc bén.
   - `/tdd`: Kỷ luật Red-Green-Refactor thực chiến.
3. **Brainstorming**: Khảo sát nghiệp vụ, phân tích trade-off và phương án kiến trúc trước khi chốt giải pháp.
4. **TDD**: Viết test trước cho toàn bộ business logic, API validation, idempotency handler, sync queue.
5. **Excalidraw / Mermaid**: Trực quan hóa kiến trúc hệ thống, sơ đồ tuần tự (sequence diagram) cho luồng thanh toán và đồng bộ tồn kho.
6. **UI/UX Pro Max**: Chuẩn hóa design system, modern dashboard UI và trải nghiệm người dùng cao cấp cho các màn hình đối soát/web portal.
7. **Web Quality**: Đảm bảo Core Web Vitals, bảo mật (CSP, HTTPS, input sanitization), khả năng chịu tải và độ ổn định của API.
8. **Humanizer**: Ngôn ngữ tự nhiên, kỹ thuật chuẩn xác, loại bỏ hoàn toàn sáo rỗng hoặc văn phong máy móc.
9. **Caveman**: Tối ưu mật độ thông tin cao, tiết kiệm token khi debug hoặc code tần suất cao.
10. **Find Skills**: Linh hoạt mở rộng công cụ khi gặp bài toán công nghệ chuyên biệt.
11. **Deploy to Vercel**: Tự động hóa triển khai Website Frontend / API Middleware nếu chạy kiến trúc serverless/Vercel.
12. **Remotion**: Dựng video / animation quy trình nếu cần tài liệu trực quan cho người dùng.

---

## 3. NGUYÊN TẮC VIẾT CODE & TÀI LIỆU
- Code: Ghi rõ version Odoo / ngôn ngữ BE, bắt buộc xử lý exception, idempotency, structured logging; không hard-code credentials/secrets.
- Tài liệu: Dùng bảng, Markdown có cấu trúc, sequence diagram chuẩn, ngắn gọn và trọng tâm.
- Làm rõ thông tin còn thiếu theo phong cách Grill-me (tối đa 1-2 câu hỏi sắc bén có gợi ý lựa chọn).
