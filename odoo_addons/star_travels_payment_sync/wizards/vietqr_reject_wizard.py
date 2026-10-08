# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class StarTravelsVietqrRejectWizard(models.TransientModel):
    _name = "star.travels.vietqr.reject.wizard"
    _description = "Wizard Từ Chối Giao Dịch Chuyển Khoản VietQR"

    pending_id = fields.Many2one(
        "star.travels.payment.pending",
        string="Giao dịch chờ",
        required=True,
        readonly=True,
    )
    booking_code = fields.Char(string="Mã Booking", related="pending_id.booking_code", readonly=True)
    amount = fields.Monetary(string="Số tiền yêu cầu", related="pending_id.amount", currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one("res.currency", related="pending_id.currency_id", readonly=True)
    rejection_reason = fields.Text(
        string="Lý do từ chối / Không tìm thấy giao dịch",
        required=True,
        help="Ghi rõ lý do (VD: Kiểm tra sao kê ngân hàng lúc 17:00 ngày 08/10 không thấy tiền về)",
    )

    def action_reject(self):
        self.ensure_one()
        pending = self.pending_id
        if pending.state != "pending":
            raise UserError(_("Giao dịch này không còn ở trạng thái chờ xác nhận."))

        if not self.rejection_reason or not self.rejection_reason.strip():
            raise UserError(_("Bắt buộc phải nhập lý do từ chối để phục vụ kiểm toán nội bộ!"))

        # 1. Update Pending record
        pending.write({
            "state": "rejected",
            "rejection_reason": self.rejection_reason,
            "confirmed_by": self.env.user.id,
            "confirmed_at": fields.Datetime.now(),
        })

        # 2. Write Immutable Audit Trail
        self.env["star.travels.payment.audit.log"]._write_audit_log({
            "pending_payment_id": pending.id,
            "booking_code": pending.booking_code,
            "action": "rejected",
            "performed_by": self.env.user.id,
            "performed_at": fields.Datetime.now(),
            "source": "manual_odoo_ui",
            "old_state": "pending",
            "new_state": "rejected",
            "amount_declared": pending.amount,
            "amount_confirmed": 0.0,
            "evidence_note": self.rejection_reason,
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã Từ Chối Giao Dịch"),
                "message": _("Giao dịch VietQR cho đơn %s đã được đánh dấu từ chối.") % pending.booking_code,
                "type": "warning",
                "sticky": False,
            },
        }
