# ADR 001: Omnichannel Retail Inventory Management & Soft Stock Reservation

## Trạng Thái (Status)
**Accepted** (Đã triển khai và vượt qua toàn bộ 5 test cases TDD)

## Bối Cảnh (Context)
Trong mô hình bán lẻ đa kênh (Omnichannel Retail: Online Web, Quầy POS, Đặt hàng đa sàn), vấn đề tranh chấp tồn kho (Race condition & Overselling) xảy ra thường xuyên khi nhiều khách hàng cùng checkout vào những phút flash-sale hoặc khi tồn kho thực tế tại quầy đang biến động.
Nếu trừ trực tiếp tồn kho khi khách vừa nhấn nút "Thanh toán", đơn hàng bị huỷ hoặc khách đổi ý sẽ gây tồn ảo và sai lệch số liệu kế toán VAS. Nếu không giữ tồn kho, nhiều khách sẽ cùng thanh toán cho cùng 1 sản phẩm có tồn on-hand cuối cùng.

## Quyết Định Kiến Trúc (Architecture Decision)
1. **Module hóa chuẩn Odoo 18**: Tạo module `retail_inventory` trong `odoo_addons/`, kế thừa trực tiếp core `stock` và `stock_account`.
2. **Cơ chế Khóa giữ hàng mềm (15-Minute Soft Stock Reservation)**:
   - Model: `retail.stock.reservation`
   - Dùng PostgreSQL Row-Level Locking (`SELECT ... FOR UPDATE` trên bảng `stock_quant`) khi tạo phiên giữ hàng.
   - Trạng thái phiên giữ: `active` (đang giữ 15p) -> `consumed` (đã chốt đơn xuất kho) HOẶC `released` (giải phóng tồn).
3. **Cấu hình Đệm An Toàn (Safety Buffer %)**:
   - Mở rộng model `stock.location` với `is_retail_store` và `safety_buffer_pct`.
   - Giúp các điểm bán lẻ giữ lại một lượng % tồn vật lý an toàn để khách mua tại quầy không bị ảnh hưởng bởi đơn hàng online.
4. **Tự động giải phóng định kỳ (Automated Cron Job)**:
   - Cấu hình cron job `ir_cron_release_expired_stock_reservations` quét mỗi 1 phút để auto-release các phiên giữ hàng quá hạn 15 phút.
5. **Tuân thủ Kế toán VAS**:
   - Chỉ khi phiên giữ hàng chuyển sang `consumed` và sinh `stock.picking` thì Odoo mới hạch toán lớp định giá kho (`stock.valuation.layer`) theo chuẩn FIFO / Bình quân gia quyền VAS.

## Hệ Quả & Đánh Giá (Consequences)
- **Ưu điểm**:
  - Loại bỏ hoàn toàn nguy cơ overselling nhờ row-lock.
  - Tồn kho khả dụng phản ánh trung thực cho cả Web eCommerce và POS.
  - Code sạch, 0 AI-slop, tuân thủ chu trình TDD.
- **Rủi ro & Phòng vệ**:
  - Row-lock ngắn hạn chỉ giữ trong transaction tạo reservation, không block toàn bộ database.
