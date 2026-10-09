# -*- coding: utf-8 -*-
import base64
import csv
import io
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StarTravelsPaymentAuditLog(models.Model):
    _name = "star.travels.payment.audit.log"
    _description = "STAR Travels Payment Append-Only Audit Log"
    _order = "performed_at desc, id desc"
    _rec_name = "booking_code"

    uuid = fields.Char(
        string="Audit UUID",
        default=lambda self: str(uuid.uuid4()),
        readonly=True,
        index=True,
        copy=False,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Bút toán thanh toán Odoo",
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    pending_payment_id = fields.Many2one(
        "star.travels.payment.pending",
        string="Giao dịch VietQR",
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    booking_code = fields.Char(
        string="Mã Booking",
        required=True,
        index=True,
        readonly=True,
    )
    action = fields.Selection(
        [
            ("pending_received", "Pending Received"),
            ("manual_confirmed", "Manual Confirmed"),
            ("auto_confirmed", "Auto Confirmed"),
            ("rejected", "Rejected"),
            ("refunded", "Refunded"),
            ("expired", "Expired"),
        ],
        string="Hành động (Action)",
        required=True,
        index=True,
        readonly=True,
    )
    performed_by = fields.Many2one(
        "res.users",
        string="Người thực hiện",
        readonly=True,
        index=True,
    )
    performed_at = fields.Datetime(
        string="Thời điểm thực hiện",
        default=fields.Datetime.now,
        readonly=True,
        required=True,
        index=True,
    )
    source = fields.Selection(
        [
            ("manual_odoo_ui", "Manual Odoo UI"),
            ("vnpay_webhook", "VNPay Webhook"),
            ("sepay_webhook", "SePay Webhook"),
            ("system_expiry", "System Expiry"),
        ],
        string="Nguồn (Source)",
        required=True,
        readonly=True,
    )
    old_state = fields.Char(string="Trạng thái cũ", readonly=True)
    new_state = fields.Char(string="Trạng thái mới", readonly=True)
    amount_declared = fields.Monetary(
        string="Số tiền yêu cầu",
        currency_field="currency_id",
        readonly=True,
    )
    amount_confirmed = fields.Monetary(
        string="Số tiền thực nhận",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    is_discrepancy = fields.Boolean(
        string="Có sai lệch tiền",
        compute="_compute_is_discrepancy",
        store=True,
        index=True,
        help="Đánh dấu các trường hợp số tiền thực nhận khác với số tiền yêu cầu",
    )
    evidence_note = fields.Text(string="Ghi chú đối soát / Chứng từ", readonly=True)
    ip_address = fields.Char(string="Địa chỉ IP", readonly=True)

    @api.depends("amount_declared", "amount_confirmed")
    def _compute_is_discrepancy(self):
        for rec in self:
            if rec.amount_confirmed and rec.amount_declared:
                rec.is_discrepancy = abs(rec.amount_confirmed - rec.amount_declared) > 0.01
            else:
                rec.is_discrepancy = False

    # -------------------------------------------------------------------------
    # HARD IMMUTABILITY CONSTRAINT: APPEND-ONLY AUDIT TRAIL
    # -------------------------------------------------------------------------
    def write(self, vals):
        raise UserError(
            _("Hồ sơ nhật ký kiểm toán (Audit Log) là bất biến (append-only). "
              "Mọi hành vi chỉnh sửa bị nghiêm cấm tuyệt đối theo chính sách bảo mật & kiểm toán nội bộ!")
        )

    def unlink(self):
        raise UserError(
            _("Hồ sơ nhật ký kiểm toán (Audit Log) là bất biến (append-only). "
              "Mọi hành vi xóa bỏ bị nghiêm cấm tuyệt đối theo chính sách bảo mật & kiểm toán nội bộ!")
        )

    @api.model
    def _write_audit_log(self, vals):
        """
        Generic centralized method for recording payment audit trail events.
        Callable from manual UI wizard, controllers, webhooks, or scheduled actions.
        """
        vals_to_create = dict(vals)
        if "uuid" not in vals_to_create:
            vals_to_create["uuid"] = str(uuid.uuid4())
        if "performed_at" not in vals_to_create:
            vals_to_create["performed_at"] = fields.Datetime.now()
        if "currency_id" not in vals_to_create:
            vals_to_create["currency_id"] = self.env.company.currency_id.id

        return self.sudo().create(vals_to_create)

    def action_export_audit_excel(self):
        """
        Generates and downloads a clean CSV/Excel file of current audit log records
        for internal auditing and compliance review.
        """
        records = self.search([], order="performed_at desc") if not self else self

        output = io.StringIO()
        # Add UTF-8 BOM so Excel on Windows recognizes Vietnamese characters correctly
        output.write("\ufeff")
        writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Audit UUID",
            "Mã Booking",
            "Hành Động",
            "Nguồn (Source)",
            "Người Thực Hiện",
            "Thời Điểm",
            "Trạng Thái Cũ",
            "Trạng Thái Mới",
            "Tiền Yêu Cầu",
            "Tiền Thực Nhận",
            "Chênh Lệch",
            "Ghi Chú Đối Soát",
            "IP Address",
        ])

        for rec in records:
            discrepancy = (rec.amount_confirmed or 0.0) - (rec.amount_declared or 0.0)
            writer.writerow([
                rec.uuid or "",
                rec.booking_code or "",
                dict(self._fields["action"].selection).get(rec.action, rec.action),
                dict(self._fields["source"].selection).get(rec.source, rec.source),
                rec.performed_by.name if rec.performed_by else "System Automation",
                fields.Datetime.to_string(rec.performed_at) if rec.performed_at else "",
                rec.old_state or "",
                rec.new_state or "",
                f"{rec.amount_declared:,.0f}" if rec.amount_declared else "0",
                f"{rec.amount_confirmed:,.0f}" if rec.amount_confirmed else "0",
                f"{discrepancy:,.0f}",
                rec.evidence_note or "",
                rec.ip_address or "",
            ])

        csv_bytes = output.getvalue().encode("utf-8")
        b64_content = base64.b64encode(csv_bytes)

        filename = f"STAR_Payment_Audit_Report_{fields.Date.today()}.csv"
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": b64_content,
            "mimetype": "text/csv;charset=utf-8",
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
