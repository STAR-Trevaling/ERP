# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StarTravelsPaymentPending(models.Model):
    _name = "star.travels.payment.pending"
    _description = "STAR Travels VietQR Pending Payment"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # noqa: RUF012
    _order = "created_at desc, id desc"
    _rec_name = "booking_code"

    name = fields.Char(string="Tham chiếu", compute="_compute_name", store=True)
    booking_code = fields.Char(
        string="Mã Booking",
        required=True,
        index=True,
        tracking=True,
        help="Mã đơn hàng khách sạn/tour (VD: ST-202610-001)",
    )
    payment_id = fields.Char(
        string="Django Transaction ID",
        required=True,
        index=True,
        copy=False,
        help="ID giao dịch payments_transaction tại Django backend",
    )
    booking_id = fields.Char(
        string="Django Booking UUID",
        index=True,
        copy=False,
        help="UUID booking tại Django",
    )
    amount = fields.Monetary(
        string="Số tiền cần chuyển",
        required=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_confirmed = fields.Monetary(
        string="Số tiền thực nhận",
        currency_field="currency_id",
        readonly=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    bank_transfer_content = fields.Char(
        string="Nội dung CK cần đối chiếu",
        required=True,
        index=True,
        tracking=True,
        help="Cú pháp chuyển khoản khách được cấp trên trang VietQR",
    )
    customer_name = fields.Char(string="Tên khách hàng", tracking=True)
    customer_email = fields.Char(string="Email khách hàng")
    customer_phone = fields.Char(string="Số điện thoại")

    user_id = fields.Many2one(
        "res.users",
        string="Salesperson (Người tạo đơn)",
        tracking=True,
        help="Nhân viên kinh doanh tạo đơn — dùng để kiểm soát nguyên tắc tách biệt vai trò (SoD)",
    )

    created_at = fields.Datetime(
        string="Thời gian tạo QR",
        default=fields.Datetime.now,
        index=True,
        required=True,
        readonly=True,
    )
    wait_hours = fields.Float(
        string="Thời gian chờ (Giờ)",
        compute="_compute_wait_hours",
        help="Số giờ giao dịch đang ở trạng thái pending chờ xác nhận",
    )

    state = fields.Selection(
        [
            ("pending", "Chờ xác nhận"),
            ("confirmed", "Đã xác nhận"),
            ("rejected", "Từ chối / Không tìm thấy"),
            ("expired", "Hết hạn"),
        ],
        string="Trạng thái",
        default="pending",
        required=True,
        index=True,
        tracking=True,
    )

    confirmed_by = fields.Many2one("res.users", string="Người xác nhận", readonly=True, tracking=True)
    confirmed_at = fields.Datetime(string="Thời gian xác nhận", readonly=True, tracking=True)
    bank_reference = fields.Char(string="Mã tham chiếu NH (FT Code)", readonly=True)
    rejection_reason = fields.Text(string="Lý do từ chối", readonly=True)

    payment_id_account = fields.Many2one(
        "account.payment",
        string="Bút toán thanh toán Odoo",
        readonly=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Đơn bán hàng liên kết",
        readonly=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Hóa đơn liên kết",
        readonly=True,
    )

    raw_payload = fields.Text(string="Raw Webhook Payload", readonly=True)

    audit_log_ids = fields.One2many(
        "star.travels.payment.audit.log",
        "pending_payment_id",
        string="Nhật ký Audit Trail",
        readonly=True,
    )

    _sql_constraints = [
        (
            "payment_id_uniq",
            "unique(payment_id)",
            "Giao dịch thanh toán với payment_id này đã tồn tại trong hệ thống!",
        ),
    ]

    @api.depends("booking_code", "bank_transfer_content")
    def _compute_name(self):
        for rec in self:
            rec.name = f"[{rec.booking_code}] {rec.bank_transfer_content or ''}".strip()

    @api.depends("created_at", "state")
    def _compute_wait_hours(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.created_at and rec.state == "pending":
                delta = now - rec.created_at
                rec.wait_hours = round(delta.total_seconds() / 3600.0, 1)
            else:
                rec.wait_hours = 0.0

    def action_open_confirm_wizard(self):
        """Opens the confirmation wizard with prefilled payment information."""
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Giao dịch này không còn ở trạng thái chờ xác nhận (Trạng thái hiện tại: %s).") % self.state)

        # Pre-check Separation of Duties
        if self.user_id and self.user_id == self.env.user:
            raise UserError(
                _("Quy chuẩn kiểm soát nội bộ (Separation of Duties):\n"
                  "Bạn là người phụ trách/tạo đơn này (%s). "
                  "Nhân viên tạo đơn không được phép tự duyệt thanh toán! "
                  "Vui lòng nhờ một kế toán viên khác kiểm tra sao kê và xác nhận.")
                % self.env.user.name
            )

        return {
            "name": _("Xác Nhận Tiền Chuyển Khoản VietQR"),
            "type": "ir.actions.act_window",
            "res_model": "star.travels.vietqr.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_pending_id": self.id,
                "default_amount_declared": self.amount,
                "default_amount_confirmed": self.amount,
            },
        }

    def action_open_reject_wizard(self):
        """Opens rejection wizard to record reason and audit trail."""
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Chỉ có thể từ chối các giao dịch đang ở trạng thái Chờ xác nhận."))

        return {
            "name": _("Từ Chối Giao Dịch Chuyển Khoản"),
            "type": "ir.actions.act_window",
            "res_model": "star.travels.vietqr.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_pending_id": self.id,
            },
        }

    @api.model
    def cron_check_pending_vietqr(self):
        """
        Scheduled Action (Chạy định kỳ):
        Tìm các khoản VietQR pending quá X giờ (cấu hình qua star_travels.vietqr_pending_timeout_hours)
        và tạo Activity nhắc nhở kế toán xử lý hoặc đối chiếu sao kê.
        """
        timeout_hours_param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("star_travels.vietqr_pending_timeout_hours", "4")
        )
        try:
            timeout_hours = float(timeout_hours_param)
        except ValueError:
            timeout_hours = 4.0

        cutoff = fields.Datetime.now() - timedelta(hours=timeout_hours)
        stale_records = self.search([
            ("state", "=", "pending"),
            ("created_at", "<=", cutoff),
        ])

        if not stale_records:
            return True

        _logger.warning("Found %d pending VietQR payment(s) older than %s hours!", len(stale_records), timeout_hours)

        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        confirmer_group = self.env.ref("star_travels_payment_sync.group_payment_confirmer", raise_if_not_found=False)
        target_user = confirmer_group.users[0] if (confirmer_group and confirmer_group.users) else self.env.user

        for rec in stale_records:
            existing = self.env["mail.activity"].search([
                ("res_model", "=", "star.travels.payment.pending"),
                ("res_id", "=", rec.id),
                ("summary", "ilike", "VietQR Pending Timeout"),
            ], limit=1)

            if not existing and activity_type:
                rec.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=f"[VietQR Alert] Đơn {rec.booking_code} chờ quá {timeout_hours}h",
                    note=(
                        f"Giao dịch VietQR đơn hàng {rec.booking_code} (Số tiền: {rec.amount:,.0f} {rec.currency_id.name}) "
                        f"Nội dung CK: '{rec.bank_transfer_content}' đã ở trạng thái Chờ xác nhận hơn {timeout_hours} giờ. "
                        "Vui lòng kiểm tra sao kê ngân hàng và xác nhận hoặc từ chối giao dịch."
                    ),
                    user_id=target_user.id,
                )

        return True
