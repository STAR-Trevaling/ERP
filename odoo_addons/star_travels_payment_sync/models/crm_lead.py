# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_is_referral = fields.Boolean(
        string="Là Referral Đối Tác",
        default=False,
        index=True,
        help="Đánh dấu Lead được tạo từ sự kiện click chuyển hướng sang đối tác dịch vụ",
    )
    x_referral_partner_name = fields.Char(
        string="Đối Tác Giới Thiệu (Partner)",
        index=True,
        help="Tên đối tác OTA/Hotel/Restaurant (VD: Booking.com, Agoda, Klook)",
    )
    x_referral_item_type = fields.Selection(
        [
            ("accommodation_referral", "Lưu Trú / Khách Sạn"),
            ("restaurant_referral", "Nhà Hàng / Ẩm Thực"),
            ("activity_referral", "Vé / Hoạt Động Trải Nghiệm"),
            ("transport_referral", "Vận Chuyển / Thuê Xe"),
            ("other_referral", "Dịch Vụ Khác"),
        ],
        string="Loại Mục Giới Thiệu",
        default="accommodation_referral",
        index=True,
    )
    x_referral_item_name = fields.Char(
        string="Tên Dịch Vụ / Khách Sạn / Nhà Hàng",
        help="Tên dịch vụ hoặc cơ sở mà khách hàng click xem chi tiết",
    )
    x_referral_destination = fields.Char(
        string="Điểm Đến (Destination)",
        index=True,
        help="Khu vực/Điểm đến của dịch vụ (VD: ha-long, phu-quoc, da-nang)",
    )
    x_referral_booking_id = fields.Char(
        string="Django Referral UUID",
        index=True,
        copy=False,
        help="UUID của sự kiện referral tại Django backend",
    )
    x_has_contact_info = fields.Boolean(
        string="Có Thông Tin Khách Hàng",
        default=False,
        index=True,
        help="Khách hàng có để lại tên/SĐT để tư vấn bổ sung (Warm Lead)",
    )
    x_referral_commission_rate = fields.Float(
        string="Tỷ Lệ Hoa Hồng Ước Tính (%)",
        default=0.0,
        help="Tỷ lệ hoa hồng thỏa thuận với đối tác (VD: 5.0 cho 5%)",
    )
    x_referral_estimated_value = fields.Monetary(
        string="Giá Trị Giao Dịch Ước Tính",
        currency_field="company_currency",
        default=0.0,
        help="Giá trị đặt phòng / dịch vụ trung bình ước tính",
    )
    x_referral_estimated_commission = fields.Monetary(
        string="Hoa Hồng Ước Tính (Click-based)",
        compute="_compute_referral_estimated_commission",
        store=True,
        currency_field="company_currency",
        help="Ước tính hoa hồng tiềm năng nội bộ dựa trên lượt click = Giá trị ước tính * Tỷ lệ %",
    )

    @api.depends("x_referral_estimated_value", "x_referral_commission_rate")
    def _compute_referral_estimated_commission(self):
        for rec in self:
            if rec.x_referral_estimated_value and rec.x_referral_commission_rate:
                rec.x_referral_estimated_commission = round(
                    rec.x_referral_estimated_value * (rec.x_referral_commission_rate / 100.0), 2
                )
            else:
                rec.x_referral_estimated_commission = 0.0

    @api.model
    def create_from_referral_payload(self, payload):
        """
        Processes inbound 'referral.created' webhook from Django backend:
        1. Always creates a Lead with type='lead' (not an opportunity / no accounting entries).
        2. Assigns tag [PARTNER_REFERRAL] to distinguish from tour consultation leads ([AI_LEAD]).
        3. If has_contact_info is True:
           - Adds tag [WARM_REFERRAL]
           - Routes to Sales pipeline (assigns Sales Team/User for cross-selling STAR tours).
        4. If has_contact_info is False:
           - Saves solely for partner click analytics and commission tracking.
           - user_id = False, team_id = False (does not disturb Sales team).
        """
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

        booking_id = data.get("booking_id") or payload.get("booking_id")
        item_type = data.get("item_type") or "accommodation_referral"
        item_name = data.get("item_name") or "Dịch Vụ Giới Thiệu Đối Tác"
        partner_name = data.get("referral_partner_name") or "Đối Tác STAR"
        destination = data.get("destination") or ""
        contact_name = data.get("contact_name")
        contact_phone = data.get("contact_phone")
        contact_email = data.get("contact_email")

        # Determine if contact info is actionable
        has_contact = bool(
            data.get("has_contact_info")
            or (contact_name and (contact_phone or contact_email))
            or contact_phone
            or contact_email
        )

        commission_rate = float(
            data.get("partner_commission_rate") or data.get("commission_rate") or 0.0
        )
        estimated_val = float(
            data.get("estimated_value")
            or data.get("price")
            or (2000000.0 if commission_rate > 0 else 0.0)
        )

        # 1. Resolve or Create Tags
        tag_partner = self.env["crm.tag"].search([("name", "=", "[PARTNER_REFERRAL]")], limit=1)
        if not tag_partner:
            tag_partner = self.env["crm.tag"].create({
                "name": "[PARTNER_REFERRAL]",
                "color": 4,  # Distinct color (Cyan/Teal)
            })

        tag_ids = [tag_partner.id]

        # 2. Build Lead Values based on Contact Availability
        if has_contact:
            # WARM REFERRAL: Customer provided contact -> Route to Sales team
            tag_warm = self.env["crm.tag"].search([("name", "=", "[WARM_REFERRAL]")], limit=1)
            if not tag_warm:
                tag_warm = self.env["crm.tag"].create({
                    "name": "[WARM_REFERRAL]",
                    "color": 2,  # Orange (Warm)
                })
            tag_ids.append(tag_warm.id)

            # Find default sales team
            sales_team = self.env["crm.team"].search([], limit=1)
            team_id = sales_team.id if sales_team else False
            assigned_user = sales_team.user_id.id if (sales_team and sales_team.user_id) else False

            cust_display = contact_name or contact_phone or "Khách Quan Tâm"
            lead_name = f"[REFERRAL-WARM] {partner_name} - {item_name} ({cust_display})"
            priority = "1"
        else:
            # STATISTICAL CLICK ONLY: No contact -> Do NOT route to Sales pipeline
            team_id = False
            assigned_user = False
            lead_name = f"[REFERRAL-CLICK] {partner_name} - {item_name} ({destination or 'General'})"
            priority = "0"

        lead_vals = {
            "name": lead_name,
            "type": "lead",  # Strictly 'lead', never 'opportunity'
            "tag_ids": [(6, 0, tag_ids)],
            "x_is_referral": True,
            "x_referral_partner_name": partner_name,
            "x_referral_item_type": item_type if item_type in [x[0] for x in self._fields["x_referral_item_type"].selection] else "other_referral",
            "x_referral_item_name": item_name,
            "x_referral_destination": destination,
            "x_referral_booking_id": str(booking_id) if booking_id else False,
            "x_has_contact_info": has_contact,
            "x_referral_commission_rate": commission_rate,
            "x_referral_estimated_value": estimated_val,
            "contact_name": contact_name or False,
            "phone": contact_phone or False,
            "email_from": contact_email or False,
            "team_id": team_id,
            "user_id": assigned_user,
            "priority": priority,
            "description": (
                f"Sự kiện chuyển tiếp đối tác STAR Travels:\n"
                f"- Đối tác: {partner_name}\n"
                f"- Dịch vụ/Khách sạn: {item_name} (Loại: {item_type})\n"
                f"- Điểm đến: {destination}\n"
                f"- Tỷ lệ hoa hồng thỏa thuận: {commission_rate}%\n"
                f"- Trạng thái khách hàng: {'Có thông tin liên hệ (Warm Lead)' if has_contact else 'Chỉ chuyển hướng click xem trang đối tác'}\n"
            ),
        }

        lead = self.create(lead_vals)
        _logger.info(
            "Created Partner Referral Lead ID #%d for '%s' (Partner: %s, HasContact: %s, RoutedSales: %s)",
            lead.id, item_name, partner_name, has_contact, bool(team_id)
        )
        return lead
