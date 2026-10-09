# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging

from odoo import SUPERUSER_ID, fields, http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class StarTravelsPaymentWebhookController(http.Controller):

    def _verify_auth(self):
        """
        Verify incoming request authentication against ir.config_parameter:
        1. Bearer API Key in Authorization header or X-API-Key against 'travel.inbound_api_key'
        2. HMAC-SHA256 signature in 'X-Signature-SHA256' against 'travel.webhook_secret'
           with dual-key rotation fallback to 'travel.webhook_secret_previous'
        Identical security handshake as travel_integration module.
        """
        auth_header = request.httprequest.headers.get("Authorization", "")
        api_key_header = request.httprequest.headers.get("X-API-Key", "")
        sig_header = request.httprequest.headers.get("X-Signature-SHA256", "")

        conf_api_key = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("travel.inbound_api_key", "star_travels_inbound_api_token_2026")
        )
        conf_secret = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("travel.webhook_secret", "star_travels_super_secret_webhook_key_2026")
        )
        conf_secret_previous = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("travel.webhook_secret_previous", False)
        )

        # 1. Check Bearer / X-API-Key
        token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else api_key_header
        if token and hmac.compare_digest(token, conf_api_key):
            return True

        # 2. Check HMAC-SHA256 signature over raw request body
        if sig_header:
            raw_body = request.httprequest.get_data()
            body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
            computed_sig = hmac.new(conf_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig_header, computed_sig):
                return True

            # 3. Dual-key rotation fallback: Verify against previous secret if configured
            if conf_secret_previous:
                computed_prev_sig = hmac.new(conf_secret_previous.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig_header, computed_prev_sig):
                    _logger.info("Webhook authenticated successfully using previous secret (rotation grace window).")
                    return True

        return False

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def _problem_response(self, title, detail, status=400, error_code="INVALID_REQUEST"):
        """RFC 7807 Problem Details representation."""
        problem = {
            "type": f"https://star-travels.com/errors/{error_code.lower()}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.httprequest.path,
        }
        return self._json_response(problem, status=status)

    def _extract_idempotency_key(self, payload):
        return (
            request.httprequest.headers.get("Idempotency-Key")
            or request.httprequest.headers.get("X-Event-ID")
            or payload.get("event_id")
            or (payload.get("data") and payload["data"].get("event_id"))
        )

    def _find_or_create_partner(self, env, customer_data):
        email = (customer_data.get("email") or "").strip()
        phone = (customer_data.get("phone") or "").strip()
        name = customer_data.get("name") or email or phone or "STAR Travels Customer"

        partner = False
        if email:
            partner = env["res.partner"].search([("email", "=ilike", email)], limit=1)
        if not partner and phone:
            partner = env["res.partner"].search([("phone", "=", phone)], limit=1)

        if not partner:
            partner = env["res.partner"].create({
                "name": name,
                "email": email or False,
                "phone": phone or False,
                "customer_rank": 1,
            })
            _logger.info("Created new customer partner: %s (ID: %s)", name, partner.id)
        return partner

    def _get_gateway_journal(self, env, gateway_code, company):
        """
        Locates the specific bank/cash journal for the payment gateway
        (VNPay, MoMo, ZaloPay, Stripe), falling back to company default bank journal.
        """
        journal_code_map = {
            "vnpay": "VNPAY",
            "momo": "MOMO",
            "zalopay": "ZALOP",
            "stripe": "STRIP",
        }
        target_code = journal_code_map.get(gateway_code.lower() if gateway_code else "", "VNPAY")
        journal = env["account.journal"].search([
            ("code", "=", target_code),
            ("company_id", "=", company.id),
        ], limit=1)

        if not journal:
            journal = env["account.journal"].search([
                ("type", "=", "bank"),
                ("company_id", "=", company.id),
            ], limit=1)

        return journal

    def _get_analytic_distribution(self, env, item_data):
        """
        Resolve analytic distribution according to tour/destination/category.
        """
        distribution = {}
        tour_slug = item_data.get("tour_slug") or item_data.get("slug")
        destination_slug = item_data.get("destination_slug")
        category_name = item_data.get("category") or "Tour Operations"

        # Search or create analytic account for reporting
        analytic_name = f"Tour: {tour_slug}" if tour_slug else (f"Dest: {destination_slug}" if destination_slug else category_name)
        analytic_plan = env["account.analytic.plan"].search([], limit=1)
        if analytic_plan:
            analytic_acc = env["account.analytic.account"].search([("name", "=", analytic_name)], limit=1)
            if not analytic_acc:
                analytic_acc = env["account.analytic.account"].create({
                    "name": analytic_name,
                    "plan_id": analytic_plan.id,
                })
            distribution[str(analytic_acc.id)] = 100.0

        return distribution or False

    def _get_or_create_service_product(self, env, item_data, company):
        """
        Locates or creates a service product for the booked tour/experience.
        Adheres to existing company tax configurations without hardcoding VAT %.
        """
        title = item_data.get("title") or item_data.get("name") or "Dịch Vụ Lữ Hành / Tour"
        slug = item_data.get("tour_slug") or item_data.get("slug") or "tour-service"
        default_code = f"TOUR-{slug.upper()[:16]}"

        product = env["product.product"].search([
            ("default_code", "=", default_code),
        ], limit=1)

        if not product:
            product = env["product.product"].search([
                ("name", "=ilike", title),
            ], limit=1)

        if not product:
            # Create product inheriting default customer sales taxes configured in Odoo Accounting settings
            product_vals = {
                "name": title,
                "default_code": default_code,
                "type": "service",
                "invoice_policy": "order",
                "list_price": float(item_data.get("price") or item_data.get("price_adult") or 0.0),
            }
            product = env["product.product"].create(product_vals)
            _logger.info("Created new service product: %s (%s)", title, default_code)

        return product

    @http.route(
        "/api/v1/travel/booking-paid",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        readonly=False,
    )
    def handle_booking_paid(self, **kwargs):
        """
        Inbound webhook receiver when a customer booking is paid on Django backend.
        Atomically creates: Partner -> Sale Order (sale) -> Order Lines -> Invoice (posted)
        -> Payment (posted) -> Reconciles invoice lines with payment lines.
        """
        if not self._verify_auth():
            _logger.warning("Unauthorized access attempt to /api/v1/travel/booking-paid")
            return self._problem_response(
                title="Unauthorized",
                detail="Missing or invalid authentication token / HMAC signature.",
                status=401,
                error_code="UNAUTHORIZED",
            )

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            return self._problem_response(
                title="Invalid JSON",
                detail="Request body must be valid JSON.",
                status=400,
                error_code="BAD_REQUEST",
            )

        idempotency_key = self._extract_idempotency_key(payload)
        if not idempotency_key:
            return self._problem_response(
                title="Missing Idempotency Key",
                detail="Header 'Idempotency-Key' or payload 'event_id' is required.",
                status=400,
                error_code="MISSING_IDEMPOTENCY_KEY",
            )

        env = request.env(user=SUPERUSER_ID)

        # 1. Idempotency Check
        existing_log = env["star.travels.webhook.log"].search([
            ("event_id", "=", str(idempotency_key)),
        ], limit=1)

        if existing_log and existing_log.state == "success" and existing_log.result_summary:
            _logger.info("Idempotent replay detected for event %s. Returning cached response.", idempotency_key)
            try:
                cached_data = json.loads(existing_log.result_summary)
                return self._json_response(cached_data, status=200)
            except Exception:
                pass

        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        booking_id = data.get("booking_id") or data.get("id") or payload.get("booking_id")
        booking_code = data.get("booking_code") or data.get("code") or f"ST-{idempotency_key[:8]}"
        customer_data = data.get("customer") or {}
        payment_data = data.get("payment") or {}
        items_data = data.get("items") or []
        company = env.company

        gateway = (payment_data.get("gateway") or data.get("gateway") or "vnpay").lower()
        gateway_tx_id = (
            payment_data.get("gateway_transaction_id")
            or payment_data.get("transaction_id")
            or data.get("gateway_transaction_id")
            or data.get("transaction_id")
            or f"TX-{idempotency_key[:12]}"
        )
        total_amount = float(
            payment_data.get("amount")
            or data.get("total_amount")
            or data.get("amount")
            or 0.0
        )

        try:
            with env.cr.savepoint():
                _logger.info(
                    "Processing booking.paid: Booking %s (UUID: %s), Gateway: %s, Amount: %s",
                    booking_code,
                    booking_id,
                    gateway,
                    total_amount,
                )

                # a. Find or create Partner
                partner = self._find_or_create_partner(env, customer_data)

                # b. Create Sale Order
                so_vals = {
                    "partner_id": partner.id,
                    "client_order_ref": booking_code,
                    "x_star_booking_id": str(booking_id) if booking_id else False,
                    "x_star_booking_code": booking_code,
                    "company_id": company.id,
                }
                sale_order = env["sale.order"].create(so_vals)

                # c. Create Order Lines
                total_lines_amount = 0.0
                if items_data:
                    for item in items_data:
                        product = self._get_or_create_service_product(env, item, company)
                        analytic_dist = self._get_analytic_distribution(env, item)

                        adults = int(item.get("adults") or 0)
                        children = int(item.get("children") or 0)
                        price_adult = float(item.get("price_adult") or item.get("price") or 0.0)
                        price_child = float(item.get("price_child") or (price_adult * 0.75))

                        if adults > 0 or children > 0:
                            if adults > 0:
                                total_lines_amount += (adults * price_adult)
                                env["sale.order.line"].create({
                                    "order_id": sale_order.id,
                                    "product_id": product.id,
                                    "name": f"{product.name} (Người lớn)",
                                    "product_uom_qty": adults,
                                    "price_unit": price_adult,
                                    "analytic_distribution": analytic_dist,
                                })
                            if children > 0:
                                total_lines_amount += (children * price_child)
                                env["sale.order.line"].create({
                                    "order_id": sale_order.id,
                                    "product_id": product.id,
                                    "name": f"{product.name} (Trẻ em)",
                                    "product_uom_qty": children,
                                    "price_unit": price_child,
                                    "analytic_distribution": analytic_dist,
                                })
                        else:
                            qty = float(item.get("quantity") or 1.0)
                            unit_price = float(item.get("price") or item.get("price_unit") or total_amount)
                            total_lines_amount += (qty * unit_price)
                            env["sale.order.line"].create({
                                "order_id": sale_order.id,
                                "product_id": product.id,
                                "name": product.name,
                                "product_uom_qty": qty,
                                "price_unit": unit_price,
                                "analytic_distribution": analytic_dist,
                            })

                    # RỦI RO KẾ TOÁN VAS: Tự động cân đối chênh lệch giữa tổng dòng và số tiền thực trả
                    # Ví dụ: Coupon giảm giá, chiết khấu khuyến mãi từ Django backend
                    if total_amount > 0:
                        discrepancy = round(total_amount - total_lines_amount, 2)
                        if abs(discrepancy) > 0.01:
                            if discrepancy < 0:
                                # Khách trả ít hơn tổng dòng niêm yết -> Chiết khấu khuyến mãi / Voucher
                                discount_val = abs(discrepancy)
                                _logger.warning(
                                    "Booking %s: Order lines total (%s) exceeds paid amount (%s). "
                                    "Adding promotional discount line (-%s) for accurate settlement and VAS reconciliation.",
                                    booking_code, total_lines_amount, total_amount, discount_val
                                )
                                disc_product = env["product.product"].search([("default_code", "=", "DISCOUNT-PROMO")], limit=1)
                                if not disc_product:
                                    disc_product = env["product.product"].create({
                                        "name": "Chiết khấu / Giảm giá khuyến mãi",
                                        "default_code": "DISCOUNT-PROMO",
                                        "type": "service",
                                        "invoice_policy": "order",
                                    })
                                env["sale.order.line"].create({
                                    "order_id": sale_order.id,
                                    "product_id": disc_product.id,
                                    "name": f"Chiết khấu khuyến mãi booking {booking_code}",
                                    "product_uom_qty": 1.0,
                                    "price_unit": -discount_val,
                                })
                            else:
                                # Khách trả nhiều hơn -> Phụ phí phát sinh
                                _logger.info(
                                    "Booking %s: Paid amount (%s) exceeds base lines (%s). "
                                    "Adding surcharge line (+%s).",
                                    booking_code, total_amount, total_lines_amount, discrepancy
                                )
                                surcharge_product = env["product.product"].search([("default_code", "=", "SURCHARGE-MISC")], limit=1)
                                if not surcharge_product:
                                    surcharge_product = env["product.product"].create({
                                        "name": "Phụ phí / Dịch vụ gia tăng",
                                        "default_code": "SURCHARGE-MISC",
                                        "type": "service",
                                        "invoice_policy": "order",
                                    })
                                env["sale.order.line"].create({
                                    "order_id": sale_order.id,
                                    "product_id": surcharge_product.id,
                                    "name": f"Phụ phí phát sinh booking {booking_code}",
                                    "product_uom_qty": 1.0,
                                    "price_unit": discrepancy,
                                })
                else:
                    # Single service fallback line matching total paid amount
                    fallback_item = {"title": f"Tour Booking {booking_code}", "price": total_amount}
                    product = self._get_or_create_service_product(env, fallback_item, company)
                    env["sale.order.line"].create({
                        "order_id": sale_order.id,
                        "product_id": product.id,
                        "name": product.name,
                        "product_uom_qty": 1.0,
                        "price_unit": total_amount,
                    })

                # Confirm Sale Order to state='sale'
                sale_order.action_confirm()

                # d. Create & Post Invoice
                invoices = sale_order._create_invoices()
                if not invoices:
                    raise ValueError(f"Failed to generate invoice for sale order {sale_order.name}")
                invoice = invoices[0]
                invoice.action_post()

                # e. Create Payment & Reconcile
                journal = self._get_gateway_journal(env, gateway, company)
                if not journal:
                    raise ValueError(f"No suitable payment journal found for gateway '{gateway}'")

                payment_amount = total_amount if total_amount > 0 else invoice.amount_total
                payment_vals = {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": partner.id,
                    "amount": payment_amount,
                    "currency_id": invoice.currency_id.id,
                    "journal_id": journal.id,
                    "date": fields.Date.context_today(env["account.payment"]),
                    "x_gateway": gateway if gateway in ("vnpay", "momo", "zalopay", "stripe") else "vnpay",
                    "x_gateway_transaction_id": gateway_tx_id,
                    "x_reconciliation_state": "pending",
                    "ref": f"Booking {booking_code} via {gateway.upper()} ({gateway_tx_id})",
                }
                payment = env["account.payment"].create(payment_vals)
                payment.action_post()

                # Reconcile invoice line with payment line
                receivable_lines = (invoice.line_ids + payment.line_ids).filtered(
                    lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable")
                    and not line.reconciled
                )
                if receivable_lines:
                    receivable_lines.reconcile()

                result_data = {
                    "success": True,
                    "odoo_sale_order_id": sale_order.id,
                    "odoo_invoice_id": invoice.id,
                    "odoo_payment_id": payment.id,
                    "booking_code": booking_code,
                    "message": "Booking payment synced and reconciled successfully.",
                }

                # Save Idempotency Log
                log_vals = {
                    "event_id": str(idempotency_key),
                    "event_type": "booking.paid",
                    "payload": raw_data,
                    "state": "success",
                    "result_summary": json.dumps(result_data),
                    "res_model": "sale.order",
                    "res_id": sale_order.id,
                }
                if existing_log:
                    existing_log.write(log_vals)
                else:
                    env["star.travels.webhook.log"].create(log_vals)

                _logger.info(
                    "Booking paid successfully synced: SO #%d, Inv #%d, Pay #%d",
                    sale_order.id,
                    invoice.id,
                    payment.id,
                )
                return self._json_response(result_data, status=200)

        except Exception as e:
            _logger.exception("Error processing booking-paid webhook for event %s: %s", idempotency_key, str(e))
            return self._problem_response(
                title="Payment Processing Error",
                detail=str(e),
                status=500,
                error_code="PROCESSING_ERROR",
            )

    @http.route(
        "/api/v1/travel/booking-refunded",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        readonly=False,
    )
    def handle_booking_refunded(self, **kwargs):
        """
        Inbound webhook receiver when a customer booking is refunded on Django backend.
        Finds original Sale Order, creates posted Credit Note (out_refund) linked to original invoice,
        creates outbound payment in gateway journal, and reconciles them.
        """
        if not self._verify_auth():
            _logger.warning("Unauthorized access attempt to /api/v1/travel/booking-refunded")
            return self._problem_response(
                title="Unauthorized",
                detail="Missing or invalid authentication token / HMAC signature.",
                status=401,
                error_code="UNAUTHORIZED",
            )

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            return self._problem_response(
                title="Invalid JSON",
                detail="Request body must be valid JSON.",
                status=400,
                error_code="BAD_REQUEST",
            )

        idempotency_key = self._extract_idempotency_key(payload)
        if not idempotency_key:
            return self._problem_response(
                title="Missing Idempotency Key",
                detail="Header 'Idempotency-Key' or payload 'event_id' is required.",
                status=400,
                error_code="MISSING_IDEMPOTENCY_KEY",
            )

        env = request.env(user=SUPERUSER_ID)

        # 1. Idempotency Check
        existing_log = env["star.travels.webhook.log"].search([
            ("event_id", "=", str(idempotency_key)),
        ], limit=1)

        if existing_log and existing_log.state == "success" and existing_log.result_summary:
            _logger.info("Idempotent replay detected for event %s in booking-refunded.", idempotency_key)
            try:
                cached_data = json.loads(existing_log.result_summary)
                return self._json_response(cached_data, status=200)
            except Exception:
                pass

        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        booking_id = data.get("booking_id") or data.get("id") or payload.get("booking_id")
        refund_amount = float(data.get("refund_amount") or payload.get("refund_amount") or 0.0)
        refund_reason = data.get("reason") or payload.get("reason") or "Customer Cancellation Refund"
        refund_tx_id = (
            data.get("refund_transaction_id")
            or data.get("gateway_transaction_id")
            or f"RF-{idempotency_key[:12]}"
        )
        gateway = (data.get("gateway") or "vnpay").lower()
        company = env.company

        if not booking_id:
            return self._problem_response(
                title="Missing Booking ID",
                detail="Field 'booking_id' is required to locate the original booking.",
                status=400,
                error_code="MISSING_BOOKING_ID",
            )

        # Locate original Sale Order by x_star_booking_id
        sale_order = env["sale.order"].search([
            ("x_star_booking_id", "=", str(booking_id)),
        ], limit=1)

        if not sale_order:
            # Fallback search by booking code
            booking_code = data.get("booking_code")
            if booking_code:
                sale_order = env["sale.order"].search([
                    ("x_star_booking_code", "=", booking_code),
                ], limit=1)

        if not sale_order:
            _logger.error("Refund failed: Sale order with booking_id %s not found.", booking_id)
            return self._problem_response(
                title="Order Not Found",
                detail=f"Cannot refund booking {booking_id}: No matching sale order found in Odoo.",
                status=404,
                error_code="BOOKING_NOT_FOUND",
            )

        # Find posted original customer invoice
        posted_invoices = sale_order.invoice_ids.filtered(
            lambda m: m.move_type == "out_invoice" and m.state == "posted"
        )
        if not posted_invoices:
            return self._problem_response(
                title="Invoice Not Found",
                detail=f"Sale order {sale_order.name} has no posted customer invoice to refund.",
                status=422,
                error_code="NO_POSTED_INVOICE",
            )
        original_invoice = posted_invoices[0]

        if refund_amount <= 0:
            refund_amount = original_invoice.amount_total

        try:
            with env.cr.savepoint():
                _logger.info(
                    "Processing booking.refunded: Booking %s, Amount: %s, Reason: %s",
                    sale_order.x_star_booking_code or sale_order.name,
                    refund_amount,
                    refund_reason,
                )

                # Create posted Credit Note (out_refund)
                first_line = original_invoice.invoice_line_ids[0] if original_invoice.invoice_line_ids else False
                credit_note_vals = {
                    "move_type": "out_refund",
                    "partner_id": sale_order.partner_id.id,
                    "reversed_entry_id": original_invoice.id,
                    "ref": f"Refund for {sale_order.x_star_booking_code or sale_order.name}: {refund_reason}",
                    "invoice_origin": sale_order.name,
                    "invoice_date": fields.Date.context_today(env["account.move"]),
                    "company_id": company.id,
                    "invoice_line_ids": [
                        (0, 0, {
                            "name": f"Hoàn tiền booking {sale_order.x_star_booking_code or sale_order.name}",
                            "quantity": 1.0,
                            "price_unit": refund_amount,
                            "product_id": first_line.product_id.id if first_line else False,
                            "tax_ids": [(6, 0, first_line.tax_ids.ids)] if (first_line and first_line.tax_ids) else [],
                        })
                    ],
                }
                credit_note = env["account.move"].create(credit_note_vals)
                credit_note.action_post()

                # Create outbound payment in gateway journal
                journal = self._get_gateway_journal(env, gateway, company)
                payment_vals = {
                    "payment_type": "outbound",
                    "partner_type": "customer",
                    "partner_id": sale_order.partner_id.id,
                    "amount": refund_amount,
                    "currency_id": credit_note.currency_id.id,
                    "journal_id": journal.id,
                    "date": fields.Date.context_today(env["account.payment"]),
                    "x_gateway": gateway if gateway in ("vnpay", "momo", "zalopay", "stripe") else "vnpay",
                    "x_gateway_transaction_id": refund_tx_id,
                    "x_reconciliation_state": "pending",
                    "ref": f"Hoàn tiền {sale_order.x_star_booking_code} ({refund_tx_id})",
                }
                outbound_payment = env["account.payment"].create(payment_vals)
                outbound_payment.action_post()

                # Reconcile credit note with outbound payment
                receivable_lines = (credit_note.line_ids + outbound_payment.line_ids).filtered(
                    lambda line: line.account_id.account_type in ("asset_receivable", "liability_payable")
                    and not line.reconciled
                )
                if receivable_lines:
                    receivable_lines.reconcile()

                result_data = {
                    "success": True,
                    "odoo_refund_id": credit_note.id,
                    "odoo_payment_id": outbound_payment.id,
                    "refund_amount": refund_amount,
                    "message": "Booking refund synced and reconciled successfully.",
                }

                # Record Idempotency Log
                log_vals = {
                    "event_id": str(idempotency_key),
                    "event_type": "booking.refunded",
                    "payload": raw_data,
                    "state": "success",
                    "result_summary": json.dumps(result_data),
                    "res_model": "account.move",
                    "res_id": credit_note.id,
                }
                if existing_log:
                    existing_log.write(log_vals)
                else:
                    env["star.travels.webhook.log"].create(log_vals)

                _logger.info(
                    "Booking refund successfully synced: Credit Note #%d, Outbound Pay #%d",
                    credit_note.id,
                    outbound_payment.id,
                )
                return self._json_response(result_data, status=200)

        except Exception as e:
            _logger.exception("Error processing booking-refunded webhook for event %s: %s", idempotency_key, str(e))
            return self._problem_response(
                title="Refund Processing Error",
                detail=str(e),
                status=500,
                error_code="PROCESSING_ERROR",
            )

    @http.route(
        "/api/v1/travel/payment-pending",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        readonly=False,
    )
    def handle_payment_pending(self, **kwargs):
        """
        Inbound webhook receiver when a customer creates a VietQR transfer payment on Django backend.
        Registers the pending transfer in star.travels.payment.pending queue so accountants can
        verify bank statements and manually confirm or reject.
        """
        if not self._verify_auth():
            _logger.warning("Unauthorized access attempt to /api/v1/travel/payment-pending")
            return self._problem_response(
                title="Unauthorized",
                detail="Missing or invalid authentication token / HMAC signature.",
                status=401,
                error_code="UNAUTHORIZED",
            )

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            return self._problem_response(
                title="Invalid JSON",
                detail="Request body must be valid JSON.",
                status=400,
                error_code="BAD_REQUEST",
            )

        idempotency_key = self._extract_idempotency_key(payload)
        if not idempotency_key:
            return self._problem_response(
                title="Missing Idempotency Key",
                detail="Header 'Idempotency-Key' or payload 'event_id' is required.",
                status=400,
                error_code="MISSING_IDEMPOTENCY_KEY",
            )

        env = request.env(user=SUPERUSER_ID)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

        payment_id = data.get("payment_id") or data.get("id") or payload.get("payment_id")
        booking_code = data.get("booking_code") or data.get("code") or f"ST-{idempotency_key[:8]}"
        amount = float(data.get("amount") or payload.get("amount") or 0.0)
        bank_transfer_content = data.get("bank_transfer_content") or data.get("transfer_content") or booking_code
        customer_name = data.get("customer_name") or (data.get("customer") and data["customer"].get("name")) or "Khách hàng VietQR"
        customer_email = data.get("customer_email") or (data.get("customer") and data["customer"].get("email"))
        customer_phone = data.get("customer_phone") or (data.get("customer") and data["customer"].get("phone"))
        booking_id = data.get("booking_id") or payload.get("booking_id")
        salesperson_email = data.get("salesperson_email")

        if not payment_id:
            return self._problem_response(
                title="Missing Payment ID",
                detail="Field 'payment_id' is required.",
                status=400,
                error_code="MISSING_PAYMENT_ID",
            )

        # Check existing pending record (Idempotency)
        existing_pending = env["star.travels.payment.pending"].search([
            ("payment_id", "=", str(payment_id)),
        ], limit=1)

        if existing_pending:
            _logger.info("Idempotent replay detected for VietQR payment %s", payment_id)
            return self._json_response({
                "success": True,
                "pending_id": existing_pending.id,
                "booking_code": existing_pending.booking_code,
                "state": existing_pending.state,
                "message": "Payment pending record already exists.",
            }, status=200)

        try:
            with env.cr.savepoint():
                # Find salesperson user if email provided
                sales_user = False
                if salesperson_email:
                    sales_user = env["res.users"].search([("email", "=ilike", salesperson_email.strip())], limit=1)

                pending_vals = {
                    "payment_id": str(payment_id),
                    "booking_code": booking_code,
                    "booking_id": str(booking_id) if booking_id else False,
                    "amount": amount,
                    "bank_transfer_content": bank_transfer_content,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "user_id": sales_user.id if sales_user else False,
                    "state": "pending",
                    "raw_payload": raw_data,
                }
                pending = env["star.travels.payment.pending"].create(pending_vals)

                # Write Audit Trail
                env["star.travels.payment.audit.log"]._write_audit_log({
                    "pending_payment_id": pending.id,
                    "booking_code": booking_code,
                    "action": "pending_received",
                    "source": "manual_odoo_ui",
                    "performed_by": False,
                    "old_state": False,
                    "new_state": "pending",
                    "amount_declared": amount,
                    "amount_confirmed": 0.0,
                    "evidence_note": f"Tiếp nhận giao dịch VietQR chờ chuyển khoản. Cú pháp: '{bank_transfer_content}'",
                })

                # Write Idempotency Log
                result_data = {
                    "success": True,
                    "pending_id": pending.id,
                    "booking_code": booking_code,
                    "message": "VietQR payment registered in pending queue.",
                }
                env["star.travels.webhook.log"].create({
                    "event_id": str(idempotency_key),
                    "event_type": "payment.pending",
                    "payload": raw_data,
                    "state": "success",
                    "result_summary": json.dumps(result_data),
                    "res_model": "star.travels.payment.pending",
                    "res_id": pending.id,
                })

                _logger.info("Registered pending VietQR payment #%d (Booking: %s, Amount: %s)", pending.id, booking_code, amount)
                return self._json_response(result_data, status=200)

        except Exception as e:
            _logger.exception("Error processing payment-pending webhook for event %s: %s", idempotency_key, str(e))
            return self._problem_response(
                title="Payment Pending Registration Error",
                detail=str(e),
                status=500,
                error_code="PROCESSING_ERROR",
            )

    @http.route(
        "/api/v1/travel/referral-created",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        readonly=False,
    )
    def handle_referral_created(self, **kwargs):
        """
        Inbound webhook receiver when a customer clicks a partner referral link on STAR Travels.
        Creates a CRM lead for partner tracking and commission analytics:
        - type='lead' (NO sale.order / invoice / payment created!).
        - Tagged with [PARTNER_REFERRAL].
        - If has_contact_info is True: Tagged [WARM_REFERRAL] and routed to Sales pipeline.
        - If has_contact_info is False: Stored for click analytics only (no Salesperson assigned).
        """
        if not self._verify_auth():
            _logger.warning("Unauthorized access attempt to /api/v1/travel/referral-created")
            return self._problem_response(
                title="Unauthorized",
                detail="Missing or invalid authentication token / HMAC signature.",
                status=401,
                error_code="UNAUTHORIZED",
            )

        try:
            raw_data = request.httprequest.get_data(as_text=True)
            payload = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            return self._problem_response(
                title="Invalid JSON",
                detail="Request body must be valid JSON.",
                status=400,
                error_code="BAD_REQUEST",
            )

        idempotency_key = self._extract_idempotency_key(payload)
        if not idempotency_key:
            return self._problem_response(
                title="Missing Idempotency Key",
                detail="Header 'Idempotency-Key' or payload 'event_id' is required.",
                status=400,
                error_code="MISSING_IDEMPOTENCY_KEY",
            )

        env = request.env(user=SUPERUSER_ID)

        # 1. Idempotency Check
        existing_log = env["star.travels.webhook.log"].search([
            ("event_id", "=", str(idempotency_key)),
        ], limit=1)

        if existing_log and existing_log.state == "success" and existing_log.result_summary:
            _logger.info("Idempotent replay detected for referral event %s", idempotency_key)
            try:
                cached_data = json.loads(existing_log.result_summary)
                return self._json_response(cached_data, status=200)
            except Exception:
                pass

        try:
            with env.cr.savepoint():
                lead = env["crm.lead"].create_from_referral_payload(payload)

                result_data = {
                    "success": True,
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "type": lead.type,
                    "has_contact_info": lead.x_has_contact_info,
                    "partner_name": lead.x_referral_partner_name,
                    "routed_to_sales": bool(lead.team_id or lead.user_id),
                    "commission_rate": lead.x_referral_commission_rate,
                    "estimated_commission": lead.x_referral_estimated_commission,
                    "message": "Referral lead registered successfully for partner tracking.",
                }

                # Record Idempotency Log
                env["star.travels.webhook.log"].create({
                    "event_id": str(idempotency_key),
                    "event_type": "referral.created",
                    "payload": raw_data,
                    "state": "success",
                    "result_summary": json.dumps(result_data),
                    "res_model": "crm.lead",
                    "res_id": lead.id,
                })

                _logger.info(
                    "Processed referral.created webhook: Lead #%d (%s), Routed to Sales: %s",
                    lead.id, lead.name, bool(lead.team_id or lead.user_id)
                )
                return self._json_response(result_data, status=200)

        except Exception as e:
            _logger.exception("Error processing referral-created webhook for event %s: %s", idempotency_key, str(e))
            return self._problem_response(
                title="Referral Processing Error",
                detail=str(e),
                status=500,
                error_code="PROCESSING_ERROR",
            )

