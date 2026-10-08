# -*- coding: utf-8 -*-
import base64
import csv
import io
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StarTravelsReconciliationWizard(models.TransientModel):
    _name = "star.travels.reconciliation.wizard"
    _description = "STAR Travels Payment Gateway Statement Reconciliation Wizard"

    statement_file = fields.Binary(
        string="Statement File (CSV/Excel)",
        required=True,
        help="Upload the transaction settlement statement exported from the payment gateway merchant portal.",
    )
    filename = fields.Char(string="File Name")
    gateway = fields.Selection(
        [
            ("vnpay", "VNPay"),
            ("momo", "MoMo"),
            ("zalopay", "ZaloPay"),
            ("stripe", "Stripe"),
        ],
        string="Payment Gateway",
        default="vnpay",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Completed"),
        ],
        string="Status",
        default="draft",
        readonly=True,
    )

    total_rows = fields.Integer(string="Total Processed Rows", readonly=True)
    matched_count = fields.Integer(string="Matched Transactions", readonly=True)
    unmatched_count = fields.Integer(string="Unmatched / Discrepancies", readonly=True)
    discrepancy_amount = fields.Monetary(
        string="Total Discrepancy Amount",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    summary_html = fields.Html(string="Reconciliation Report", readonly=True)

    def _normalize_header(self, text):
        return text.strip().lower().replace(" ", "_").replace("-", "_")

    def _parse_amount(self, raw_val):
        """Safely parse amount from string removing commas, currency symbols, and spaces."""
        if not raw_val:
            return 0.0
        cleaned = str(raw_val).strip().replace(",", "").replace(".", "").replace("VND", "").replace("₫", "").strip()
        try:
            # Handle float or integer
            val = float(str(raw_val).strip().replace("VND", "").replace("₫", "").replace(" ", "").replace(",", ""))
            return val
        except ValueError:
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

    def action_process_reconciliation(self):
        """
        Parses statement file, reconciles against account.payment records,
        updates x_reconciliation_state and displays audit summary metrics.
        """
        self.ensure_one()
        if not self.statement_file:
            raise UserError(_("Please upload a statement file to process."))

        try:
            file_content = base64.b64decode(self.statement_file)
        except Exception as e:
            raise UserError(_("Invalid base64 file data: %s") % str(e))

        # Decode text with fallback encodings
        decoded_text = None
        for enc in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
            try:
                decoded_text = file_content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not decoded_text:
            raise UserError(_("Could not decode the statement file. Please ensure it is saved in UTF-8 format."))

        # Detect CSV delimiter
        first_line = decoded_text.splitlines()[0] if decoded_text.splitlines() else ""
        delimiter = ";" if ";" in first_line else ("\t" if "\t" in first_line else ",")

        f = io.StringIO(decoded_text)
        reader = csv.reader(f, delimiter=delimiter)

        headers: list[str] = []
        rows: list[list[str]] = []
        for row in reader:
            if not row or not any(row):
                continue
            if not headers:
                headers = [self._normalize_header(h) for h in row]
            else:
                rows.append(row)

        if not headers or not rows:
            raise UserError(_("The uploaded file contains no data or could not be parsed."))

        # Detect Transaction ID and Amount column indices
        tx_id_candidates = [
            "gateway_transaction_id",
            "vnp_transactionno",
            "transaction_id",
            "ma_giao_dich",
            "mã_giao_dịch",
            "trans_id",
            "transid",
            "vnp_txnid",
            "reference",
        ]
        amount_candidates = [
            "amount",
            "vnp_amount",
            "so_tien",
            "số_tiền",
            "total_amount",
            "total",
            "gia_tri",
        ]

        tx_col_idx = -1
        amount_col_idx = -1

        for idx, h in enumerate(headers):
            if any(cand in h for cand in tx_id_candidates) and tx_col_idx == -1:
                tx_col_idx = idx
            if any(cand in h for cand in amount_candidates) and amount_col_idx == -1:
                amount_col_idx = idx

        if tx_col_idx == -1:
            raise UserError(
                _("Could not locate a Transaction ID column in the statement headers: %s") % ", ".join(headers)
            )
        if amount_col_idx == -1:
            raise UserError(
                _("Could not locate an Amount column in the statement headers: %s") % ", ".join(headers)
            )

        matched = 0
        unmatched = 0
        total_discrepancy = 0.0
        audit_details = []

        for row in rows:
            if len(row) <= max(tx_col_idx, amount_col_idx):
                continue
            tx_id = str(row[tx_col_idx]).strip()
            if not tx_id:
                continue

            file_amount = self._parse_amount(row[amount_col_idx])
            # Handle VNPay raw convention (vnp_Amount = VND * 100)
            if self.gateway == "vnpay" and file_amount > 100000000 and "vnp_amount" in headers[amount_col_idx]:
                file_amount = file_amount / 100.0

            # Search payment in Odoo
            payment = self.env["account.payment"].search([
                ("x_gateway", "=", self.gateway),
                ("x_gateway_transaction_id", "=", tx_id),
            ], limit=1)

            if not payment:
                # Also try matching without gateway restriction
                payment = self.env["account.payment"].search([
                    ("x_gateway_transaction_id", "=", tx_id),
                ], limit=1)

            if payment:
                diff = abs(payment.amount - file_amount)
                if diff < 1.0:  # Matches within 1 VND rounding tolerance
                    payment.x_reconciliation_state = "matched"
                    matched += 1
                    status_badge = '<span class="badge rounded-pill text-bg-success">Khớp (Matched)</span>'
                else:
                    payment.x_reconciliation_state = "unmatched"
                    unmatched += 1
                    total_discrepancy += diff
                    status_badge = f'<span class="badge rounded-pill text-bg-warning">Lệch tiền ({diff:,.0f} VND)</span>'

                audit_details.append({
                    "tx_id": tx_id,
                    "payment_name": payment.name,
                    "odoo_amount": f"{payment.amount:,.0f} {payment.currency_id.name}",
                    "file_amount": f"{file_amount:,.0f} {self.currency_id.name}",
                    "status": status_badge,
                })
            else:
                unmatched += 1
                total_discrepancy += file_amount
                status_badge = '<span class="badge rounded-pill text-bg-danger">Không tìm thấy trong Odoo</span>'
                audit_details.append({
                    "tx_id": tx_id,
                    "payment_name": "—",
                    "odoo_amount": "0",
                    "file_amount": f"{file_amount:,.0f} {self.currency_id.name}",
                    "status": status_badge,
                })

        # Build visual summary HTML
        table_rows = "".join([
            f"<tr>"
            f"<td><code>{d['tx_id']}</code></td>"
            f"<td>{d['payment_name']}</td>"
            f"<td class='text-end'>{d['file_amount']}</td>"
            f"<td class='text-end'>{d['odoo_amount']}</td>"
            f"<td class='text-center'>{d['status']}</td>"
            f"</tr>"
            for d in audit_details[:50]  # Limit to 50 preview rows
        ])

        more_info = (
            f"<p class='text-muted small'>* Hiển thị 50 / {len(audit_details)} dòng đầu tiên.</p>"
            if len(audit_details) > 50 else ""
        )

        html_report = f"""
        <div class="p-3">
            <div class="row mb-3 text-center">
                <div class="col-md-3">
                    <div class="card p-2 bg-light">
                        <small class="text-muted">Tổng giao dịch</small>
                        <h4 class="mb-0 text-primary">{len(rows)}</h4>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-2 bg-light">
                        <small class="text-muted">Khớp hoàn toàn</small>
                        <h4 class="mb-0 text-success">{matched}</h4>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-2 bg-light">
                        <small class="text-muted">Lệch / Chưa tìm thấy</small>
                        <h4 class="mb-0 text-danger">{unmatched}</h4>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card p-2 bg-light">
                        <small class="text-muted">Tổng tiền chênh lệch</small>
                        <h4 class="mb-0 text-warning">{total_discrepancy:,.0f} {self.currency_id.name}</h4>
                    </div>
                </div>
            </div>
            <table class="table table-sm table-striped table-hover align-middle">
                <thead class="table-dark">
                    <tr>
                        <th>Mã GD Gateway</th>
                        <th>Bút toán Odoo</th>
                        <th class="text-end">Tiền file sao kê</th>
                        <th class="text-end">Tiền ghi nhận ERP</th>
                        <th class="text-center">Trạng thái đối soát</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            {more_info}
        </div>
        """

        self.write({
            "state": "done",
            "total_rows": len(rows),
            "matched_count": matched,
            "unmatched_count": unmatched,
            "discrepancy_amount": total_discrepancy,
            "summary_html": html_report,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "star.travels.reconciliation.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
