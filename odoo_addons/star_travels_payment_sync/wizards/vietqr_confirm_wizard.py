# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
import uuid

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StarTravelsVietqrConfirmWizard(models.TransientModel):
    _name = "star.travels.vietqr.confirm.wizard"
    _description = "Wizard Xác Nhận Thanh Toán VietQR Thủ Công"

    pending_id = fields.Many2one(
        "star.travels.payment.pending",
        string="Giao dịch chờ",
        required=True,
        readonly=True,
    )
    booking_code = fields.Char(string="Mã Booking", related="pending_id.booking_code", readonly=True)
    customer_name = fields.Char(string="Tên khách hàng", related="pending_id.customer_name", readonly=True)
    bank_transfer_content = fields.Char(
        string="Nội dung CK đối chiếu",
        related="pending_id.bank_transfer_content",
        readonly=True,
    )
    amount_declared = fields.Monetary(
        string="Số tiền yêu cầu",
        related="pending_id.amount",
        currency_field="currency_id",
        readonly=True,
    )
    amount_confirmed = fields.Monetary(
        string="Số tiền thực nhận (VND)",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="pending_id.currency_id",
        readonly=True,
    )
    confirmed_date = fields.Datetime(
        string="Ngày giờ nhận tiền thực tế",
        default=fields.Datetime.now,
        required=True,
        help="Thời điểm tiền vào tài khoản ngân hàng theo sao kê",
    )
    bank_reference = fields.Char(
        string="Mã tham chiếu NH (FT Code / Ref)",
        help="Mã bút toán chuyển tiền từ sao kê ngân hàng (VD: FT241088921)",
    )
    evidence_note = fields.Text(
        string="Ghi chú đối soát / Chứng từ",
        help="Bắt buộc nhập nếu số tiền thực nhận có sai lệch so với số tiền yêu cầu",
    )

    def _notify_django_vietqr_confirm(self, payment_id, payload_dict):
        """
        Calls external Django backend to notify that VietQR payment is confirmed.
        Uses identical HMAC-SHA256 signing and endpoints.
        If network fails, enqueues to travel.integration.outbox without rolling back Odoo transactions!
        """
        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("travel.public_platform_url", "http://host.docker.internal:8000")
            .rstrip("/")
        )
        secret = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("travel.webhook_secret", "star_travels_super_secret_webhook_key_2026")
        )

        endpoint_path = f"/api/v1/payments/{payment_id}/vietqr-confirm/"
        full_url = f"{base_url}{endpoint_path}"

        raw_bytes = json.dumps(payload_dict, default=str).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
        event_uuid = str(uuid.uuid4())

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "StarTravels-Odoo18-VietQR/1.0",
            "X-Signature-SHA256": signature,
            "Idempotency-Key": event_uuid,
            "X-Event-ID": event_uuid,
        }

        req = urllib.request.Request(full_url, data=raw_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.getcode() < 300:
                    _logger.info("Successfully notified Django VietQR confirmation for payment %s", payment_id)
                    return True
        except (urllib.error.HTTPError, urllib.error.URLError, Exception) as e:
            _logger.warning(
                "Direct call to Django endpoint %s failed (%s). Enqueuing into Outbox for background retry.",
                full_url,
                str(e),
            )
            # Resilient Outbox Enqueue - Zero data loss!
            outbox_model = self.env["travel.integration.outbox"]
            envelope = {
                "event_id": event_uuid,
                "event_type": "payment.vietqr.confirmed",
                "payment_id": payment_id,
                "endpoint": endpoint_path,
                "data": payload_dict,
            }
            outbox_model.create({
                "event_id": event_uuid,
                "event_type": "payment.vietqr.confirmed",
                "source": "odoo",
                "payload": json.dumps(envelope),
                "state": "pending",
                "next_retry_at": fields.Datetime.now(),
            })
            return False

    def action_confirm(self):
        """
        Executes manual confirmation:
        1. Verifies permission (Payment Confirmer group).
        2. Enforces Separation of Duties (User != Order creator).
        3. Enforces Evidence Note when amount differs.
        4. Atomically creates Sale Order, Invoice, and Payment (state: posted, gateway: vietqr, matched).
        5. Writes immutable Audit Log.
        6. Notifies Django backend with Outbox fallback.
        """
        self.ensure_one()
        pending = self.pending_id
        if pending.state != "pending":
            raise UserError(_("Giao dịch này không còn ở trạng thái chờ xác nhận!"))

        # 1. Permission Check
        confirmer_group = self.env.ref("star_travels_payment_sync.group_payment_confirmer", raise_if_not_found=False)
        has_perm = (
            self.env.user.has_group("account.group_account_user")
            or (confirmer_group and self.env.user in confirmer_group.users)
            or self.env.user._is_admin()
        )
        if not has_perm:
            # Audit log unauthorized attempt
            self.env["star.travels.payment.audit.log"]._write_audit_log({
                "pending_payment_id": pending.id,
                "booking_code": pending.booking_code,
                "action": "manual_confirmed",
                "source": "manual_odoo_ui",
                "performed_by": self.env.user.id,
                "old_state": pending.state,
                "new_state": pending.state,
                "evidence_note": f"UNAUTHORIZED ACCESS ATTEMPT: User {self.env.user.name} does not have Confirmer role.",
            })
            raise UserError(_("Bạn không thuộc nhóm quyền 'Kế toán Xác Nhận Thanh Toán' nên không thể duyệt giao dịch này!"))

        # 2. Separation of Duties (SoD) Check
        if pending.user_id and pending.user_id == self.env.user and not self.env.user._is_admin():
            self.env["star.travels.payment.audit.log"]._write_audit_log({
                "pending_payment_id": pending.id,
                "booking_code": pending.booking_code,
                "action": "manual_confirmed",
                "source": "manual_odoo_ui",
                "performed_by": self.env.user.id,
                "old_state": pending.state,
                "new_state": pending.state,
                "evidence_note": f"SOD VIOLATION ATTEMPT: Creator {self.env.user.name} attempted self-approval.",
            })
            raise UserError(
                _("Quy chuẩn kiểm soát nội bộ (Separation of Duties):\n"
                  "Bạn là người phụ trách/tạo đơn này (%s). "
                  "Nhân viên tạo đơn không được phép tự duyệt thanh toán! "
                  "Vui lòng nhờ một kế toán viên khác kiểm tra sao kê và xác nhận.")
                % self.env.user.name
            )

        # 3. Discrepancy Note Check
        diff = abs(self.amount_confirmed - self.amount_declared)
        if diff > 0.01 and not (self.evidence_note and self.evidence_note.strip()):
            raise UserError(
                _("Số tiền thực nhận (%s) khác với số tiền yêu cầu (%s).\n"
                  "Bắt buộc phải nhập 'Ghi chú đối soát / Chứng từ' để giải trình sai lệch cho kiểm toán!")
                % (f"{self.amount_confirmed:,.0f}", f"{self.amount_declared:,.0f}")
            )

        company = self.env.company

        # 4. Atomic Accounting Execution
        with self.env.cr.savepoint():
            # a. Find or create Partner
            partner = False
            if pending.customer_email:
                partner = self.env["res.partner"].search([("email", "=ilike", pending.customer_email.strip())], limit=1)
            if not partner and pending.customer_phone:
                partner = self.env["res.partner"].search([("phone", "=", pending.customer_phone.strip())], limit=1)
            if not partner:
                partner = self.env["res.partner"].create({
                    "name": pending.customer_name or pending.booking_code,
                    "email": pending.customer_email or False,
                    "phone": pending.customer_phone or False,
                    "customer_rank": 1,
                })

            # b. Find or create Sale Order
            sale_order = self.env["sale.order"].search([
                ("x_star_booking_id", "=", str(pending.booking_id)),
            ], limit=1) if pending.booking_id else False

            if not sale_order:
                sale_order = self.env["sale.order"].search([
                    ("x_star_booking_code", "=", pending.booking_code),
                ], limit=1)

            if not sale_order:
                # Create service product and order
                default_code = f"TOUR-{pending.booking_code[:12].upper()}"
                product = self.env["product.product"].search([("default_code", "=", default_code)], limit=1)
                if not product:
                    product = self.env["product.product"].create({
                        "name": f"Tour Booking {pending.booking_code}",
                        "default_code": default_code,
                        "type": "service",
                        "invoice_policy": "order",
                        "list_price": self.amount_confirmed,
                    })

                sale_order = self.env["sale.order"].create({
                    "partner_id": partner.id,
                    "client_order_ref": pending.booking_code,
                    "x_star_booking_id": str(pending.booking_id) if pending.booking_id else False,
                    "x_star_booking_code": pending.booking_code,
                    "company_id": company.id,
                    "user_id": pending.user_id.id if pending.user_id else False,
                    "order_line": [
                        (0, 0, {
                            "product_id": product.id,
                            "name": product.name,
                            "product_uom_qty": 1.0,
                            "price_unit": self.amount_confirmed,
                        })
                    ],
                })

            if sale_order.state not in ("sale", "done"):
                sale_order.action_confirm()

            # c. Create & Post Invoice
            posted_invoices = sale_order.invoice_ids.filtered(
                lambda m: m.move_type == "out_invoice" and m.state == "posted"
            )
            if posted_invoices:
                invoice = posted_invoices[0]
            else:
                invoices = sale_order._create_invoices()
                invoice = invoices[0]
                invoice.action_post()

            # d. Locate VietQR Journal
            journal = self.env["account.journal"].search([
                ("code", "=", "VIETQR"),
                ("company_id", "=", company.id),
            ], limit=1)
            if not journal:
                journal = self.env["account.journal"].search([
                    ("type", "=", "bank"),
                    ("company_id", "=", company.id),
                ], limit=1)

            # e. Create Payment & Reconcile
            payment_vals = {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner.id,
                "amount": self.amount_confirmed,
                "currency_id": invoice.currency_id.id,
                "journal_id": journal.id,
                "date": self.confirmed_date.date() if self.confirmed_date else fields.Date.today(),
                "x_gateway": "vietqr",
                "x_gateway_transaction_id": self.bank_reference or pending.payment_id,
                "x_reconciliation_state": "matched",
                "ref": f"VietQR CK {pending.booking_code} ({self.bank_reference or 'FT-N/A'})",
            }
            payment = self.env["account.payment"].create(payment_vals)
            payment.action_post()

            # Reconcile invoice line with payment line
            receivable_lines = (invoice.line_ids + payment.line_ids).filtered(
                lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable")
                and not line.reconciled
            )
            if receivable_lines:
                receivable_lines.reconcile()

            # f. Update Pending record
            pending.write({
                "state": "confirmed",
                "confirmed_by": self.env.user.id,
                "confirmed_at": self.confirmed_date,
                "bank_reference": self.bank_reference,
                "amount_confirmed": self.amount_confirmed,
                "payment_id_account": payment.id,
                "sale_order_id": sale_order.id,
                "invoice_id": invoice.id,
            })

            # g. Write Immutable Audit Trail
            evidence = self.evidence_note or f"Xác nhận sao kê NH thành công. Mã tham chiếu: {self.bank_reference or 'N/A'}"
            self.env["star.travels.payment.audit.log"]._write_audit_log({
                "payment_id": payment.id,
                "pending_payment_id": pending.id,
                "booking_code": pending.booking_code,
                "action": "manual_confirmed",
                "performed_by": self.env.user.id,
                "performed_at": fields.Datetime.now(),
                "source": "manual_odoo_ui",
                "old_state": "pending",
                "new_state": "confirmed",
                "amount_declared": self.amount_declared,
                "amount_confirmed": self.amount_confirmed,
                "evidence_note": evidence,
            })

        # 5. Outbound Django Callback with Outbox Resilience
        django_payload = {
            "payment_id": pending.payment_id,
            "booking_code": pending.booking_code,
            "amount_confirmed": self.amount_confirmed,
            "confirmed_by": self.env.user.name,
            "confirmed_at": fields.Datetime.to_string(self.confirmed_date),
            "bank_reference": self.bank_reference or "",
            "source": "manual_odoo_ui",
        }
        self._notify_django_vietqr_confirm(pending.payment_id, django_payload)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Xác Nhận Thành Công"),
                "message": _("Đơn hàng %s đã được xác nhận thanh toán VietQR và hạch toán vào sổ cái.") % pending.booking_code,
                "type": "success",
                "sticky": False,
            },
        }
