# QUY TRÌNH ĐỐI SOÁT THANH TOÁN & ĐỒNG BỘ ERP (RECONCILIATION GUIDE)

Hệ thống bán lẻ đa kênh yêu cầu đối soát định kỳ (cuối ca POS và cuối ngày E-commerce) để đảm bảo không thất thoát tiền và lệch số liệu sổ sách kế toán VAS.

---

## 1. MÔ HÌNH ĐỐI SOÁT 3 BÊN (3-WAY RECONCILIATION)

```text
+-----------------------+       +-----------------------+       +-----------------------+
|  1. CỔNG THANH TOÁN   | <===> | 2. FASTAPI MIDDLEWARE | <===> |   3. ODOO 18 CORE     |
| (VNPay / MoMo Portal) |       | (payment_transactions)|       |  (account.journal)    |
+-----------------------+       +-----------------------+       +-----------------------+
  - Tổng số tiền thực thu          - Tổng giao dịch Webhook        - Tổng phát sinh Nợ 112
  - Báo cáo sao kê đối soát        - Log signature hợp lệ          - Chi tiết từng Payment
  - Trừ phí dịch vụ cổng           - Trạng thái odoo_synced        - Hóa đơn điện tử VAT
```

---

## 2. NGUYÊN TẮC HẠCH TOÁN KẾ TOÁN VAS

1. **Phân tách Payment Journal**:
   - `VNPAY`: Sổ nhật ký Ngân hàng VNPay (TK 1121_VNPAY)
   - `MOMO`: Sổ nhật ký Ví MoMo (TK 1121_MOMO)
   - `VIETQR`: Sổ nhật ký Ngân hàng MB/Vietcombank (TK 1121_VQR)
   - `POS_CASH`: Sổ nhật ký Tiền mặt tại quầy (TK 1111)

2. **Hạch toán phí giao dịch cổng (Payment Gateway Fee)**:
   - **Tuyệt đối không trừ phí vào doanh thu**.
   - Doanh thu ghi nhận 100% theo giá trị đơn hàng (Nợ 112 / Có 511 + 33311).
   - Phí cổng hạch toán riêng vào chi phí tài chính / chi phí bán hàng (Nợ 6425 / Có 112).

---

## 3. CÁC TÌNH HUỐNG LỆCH & CÁCH XỬ LÝ (EDGE CASES)

| Tình huống lệch | Nguyên nhân | Quy trình xử lý tự động / thủ công |
|---|---|---|
| **Cổng báo Thành công, Odoo chưa ghi nhận** (`odoo_synced = False`) | Server Odoo bảo trì hoặc timeout mạng lúc Webhook bắn về. | Chạy lệnh FastAPI Retry Worker quét các bản ghi `odoo_synced = False` để đồng bộ lại tự động. |
| **Cổng báo Thành công nhưng đơn đã bị Odoo hủy (Timeout 15p)** | Khách hàng thao tác chuyển khoản sau khi hết hạn 15 phút. Kho đã nhả hàng. | Hệ thống ghi nhận tiền vào TK Treo/Công nợ tạm (TK 1388 / 3388), bắn thông báo cho CSKH liên hệ khách gửi lại đơn mới hoặc hoàn tiền. |
| **Lệch tiền lẻ do chiết khấu/voucher** | Khách áp mã giảm giá trên cổng mà Web không ghi nhận. | Bắt buộc đối chiếu `vnp_Amount` khớp 100% với `amount_total` của `sale.order` trước khi confirm. |

---

## 4. SCRIPT ĐỐI SOÁT CUỐI NGÀY (CLI RECONCILER)

FastAPI hỗ trợ lệnh CLI để xuất danh sách giao dịch lệch trong ngày:

```bash
# Chạy script đối soát và xuất file CSV các đơn lệch
python -m app.cli.reconcile --date 2026-09-28
```
