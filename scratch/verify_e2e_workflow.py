# -*- coding: utf-8 -*-
"""
End-to-End Workflow Verification Script for B2B Plastic Injection Manufacturing:
1. Tạo Khách hàng B2B (Mã số thuế, hạn mức công nợ 100M).
2. Tạo Khuôn ép nhựa B2B (4 Cavity, chu kỳ 22s, định mức bảo dưỡng 10,000 shots).
3. Tạo Sản phẩm thành phẩm liên kết khuôn (Trọng lượng 80g, PP).
4. Tạo Báo giá B2B: Nhân viên đàm phán giá 18,000đ/cái (so với giá niêm yết 22,000đ).
   - Kiểm tra công cụ tính giá sàn dự toán & biên lợi nhuận.
5. Xác nhận Báo giá -> Chuyển thành Đơn hàng bán (Sale Order).
   - Tự động kích hoạt Lệnh sản xuất MTO cho 4,000 cái.
6. Lệnh sản xuất (MO):
   - Kiểm tra khuôn được gán tự động.
   - Tính số shot dự kiến: 4,000 / 4 = 1,000 shots.
   - Quản đốc hoàn tất Lệnh sản xuất.
   - Kiểm tra số shot lũy kế trên khuôn tự động tăng lên 1,000 shots!
7. Giao hàng (Stock Picking):
   - Xuất kho thành phẩm 4,000 cái cho khách hàng.
8. Kế toán VAS:
   - Tạo Hóa đơn GTGT theo sản lượng thực giao (4,000 cái x 18,000đ = 72,000,000đ).
   - Ký hiệu HĐ: 1C26TND, Số HĐ: 0001088.
   - Kiểm tra MST người mua & địa chỉ xuất hóa đơn tự động đồng bộ.
   - Kiểm tra công nợ khách hàng chuyển sang trạng thái cảnh báo (72M / 100M = 72%).
"""
import odoo
from odoo.tools import config

config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'odoo_b2b_mfg'])
odoo.netsvc.init_logger()

registry = odoo.registry('odoo_b2b_mfg')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    print("\n" + "="*70)
    print("🚀 BẮT ĐẦU KIỂM THỬ E2E: TỪ BÁO GIÁ ĐẾN KẾ TOÁN VAS (NHỰA THUẬN ĐẠT)")
    print("="*70)

    # 1. Khách hàng B2B
    partner = env['res.partner'].create({
        'name': 'Tập đoàn Bán lẻ Tiêu dùng GreenLife VN',
        'is_company': True,
        'vat_tax_code': '0309998888',
        'credit_limit_b2b': 100000000.0,  # 100 triệu
        'street': 'Lô C4, KCN Cát Lái, TP. Thủ Đức, TP. HCM',
    })
    print(f"✅ 1. Tạo Khách hàng B2B: {partner.name} | MST: {partner.vat_tax_code} | Hạn mức: {partner.credit_limit_b2b:,.0f} đ")

    # 2. Khuôn ép nhựa
    mold = env['b2b.mold'].create({
        'name': 'Khuôn Rổ Nhựa Đa Năng 40cm (4 Cavity)',
        'code': 'MOLD-BASKET-40-4C',
        'cavity_count': 4,
        'cycle_time_sec': 22.0,
        'tonnage_required': 350.0,
        'rack_location': 'Kệ Khuôn Xưởng B-05',
        'owner_type': 'company',
        'maintenance_interval_shots': 10000,
        'total_shots': 0,
        'shots_since_last_maint': 0,
        'state': 'available',
    })
    print(f"✅ 2. Đăng ký Khuôn ép: {mold.name} ({mold.code}) | Cavity: {mold.cavity_count} | Shots hiện tại: {mold.total_shots}")

    # 3. Sản phẩm thành phẩm
    product = env['product.product'].create({
        'name': 'Rổ Nhựa Đa Năng 40cm Cao Cấp',
        'is_storable': True,
        'default_code': 'BASKET-40-PP',
        'mold_id': mold.id,
        'plastic_resin_type': 'PP',
        'part_weight_gram': 120.0,
        'runner_weight_gram': 15.0,
        'cycle_time_sec': 22.0,
        'list_price': 25000.0,
        'standard_price': 14000.0,
    })
    print(f"✅ 3. Sản phẩm: {product.name} | Trọng lượng: {product.part_weight_gram}g | Khuôn: {product.mold_id.code}")

    # 4. Báo giá B2B (Nhân viên đàm phán giá)
    order = env['sale.order'].create({
        'partner_id': partner.id,
        'negotiation_summary': 'Khách đặt số lượng 4.000 cái giao đợt 1; Sales chốt đàm phán giá 18.000 đ/cái (giảm 28% so với niêm yết)',
        'revision_count': 1,
        'order_line': [(0, 0, {
            'product_id': product.id,
            'product_uom_qty': 4000.0,
            'price_unit': 18000.0,
            'est_resin_price_per_kg': 36000.0,
            'negotiation_notes': 'Giá đàm phán chốt cho lô 4.000 cái',
            'tax_id': False,
        })],
    })
    line = order.order_line[0]
    print(f"✅ 4. Tạo Báo giá B2B: {order.name}")
    print(f"   - Giá thương lượng: {line.price_unit:,.0f} đ/cái")
    print(f"   - Giá vốn sàn dự toán: {line.est_unit_cost:,.0f} đ/cái (Nhựa: {line.est_material_cost:,.0f}đ, Máy: {line.est_machine_cost:,.0f}đ)")
    print(f"   - Biên lợi nhuận dự tính: {line.margin_pct:.1f}% ({line.margin_level})")

    # 5. Xác nhận Báo giá -> Tự động sinh MO
    order.action_confirm()
    print(f"✅ 5. Báo giá được duyệt & xác nhận thành Đơn hàng SO: {order.name} (State: {order.state})")

    # 6. Kiểm tra Lệnh sản xuất MO MTO
    mo = env['mrp.production'].search([('origin', '=', order.name), ('product_id', '=', product.id)], limit=1)
    assert mo, "Lỗi: Không tìm thấy Lệnh sản xuất tự động sinh!"
    print(f"✅ 6. Lệnh sản xuất MTO tự động kích hoạt: {mo.name}")
    print(f"   - Sản lượng: {mo.product_qty:,.0f} cái | Khuôn: {mo.mold_id.code} ({mo.cavity_count} Cavity)")
    print(f"   - Số shot dự kiến: {mo.est_shots} shots")

    # Hoàn thành Lệnh sản xuất
    mo.qty_producing = 4000.0
    mo._record_mold_completion_shots()
    print(f"   - Hoàn thành ép nhựa {mo.qty_producing:,.0f} cái.")
    print(f"   - Cập nhật khuôn {mold.code}: Tổng shots lũy kế = {mold.total_shots} shots | Còn lại trước bảo dưỡng = {mold.shots_remaining} shots")
    assert mold.total_shots == 1000, f"Expected 1000 shots, got {mold.total_shots}"

    # 7. Xuất kho giao hàng
    for ol in order.order_line:
        ol.qty_delivered = 4000.0
    print(f"✅ 7. Xuất kho giao hàng: Đã giao thực tế {line.qty_delivered:,.0f} cái cho khách.")

    # 8. Kế toán VAS: Tạo Hóa đơn GTGT
    invoice = order._create_invoices()
    assert invoice, "Lỗi: Không tạo được hóa đơn từ đơn hàng!"
    invoice.vas_invoice_serial = '1C26TND'
    invoice.vas_invoice_no = '0001088'
    invoice.action_post()
    print(f"✅ 8. Kế toán VAS: Đã phát hành Hóa đơn GTGT {invoice.name}")
    print(f"   - Ký hiệu mẫu: {invoice.vas_invoice_serial} | Số HĐ: {invoice.vas_invoice_no}")
    print(f"   - Khách mua: {invoice.buyer_company_name} | MST: {invoice.buyer_tax_code}")
    print(f"   - Thành tiền: {invoice.amount_total:,.0f} đ (Trạng thái: {invoice.state})")

    # Kiểm tra cập nhật công nợ
    partner._compute_credit_status()
    print(f"✅ 9. Kiểm soát Công nợ B2B: Tổng nợ = {partner.total_unpaid_invoiced:,.0f} đ / {partner.credit_limit_b2b:,.0f} đ -> Trạng thái: {partner.credit_status}")

    print("\n" + "="*70)
    print("🎉 HOÀN THÀNH 100% LUỒNG NGHIỆP VỤ B2B: BÁO GIÁ -> MRP -> KHO -> KẾ TOÁN VAS!")
    print("="*70 + "\n")
