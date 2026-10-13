# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class TravelCrmInsightReport(models.Model):
    _name = "travel.crm.insight.report"
    _description = "Star Travels - Báo Cáo Insights Bán Hàng & Marketing Attribution Đa Kênh"
    _auto = False
    _rec_name = "name"
    _order = "create_date desc"

    # Lead Dimensions
    lead_id = fields.Many2one("crm.lead", string="Cơ Hội / Lead", readonly=True)
    name = fields.Char(string="Tiêu Đề Yêu Cầu / Lead", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Khách Hàng", readonly=True)
    user_id = fields.Many2one("res.users", string="Nhân Viên Phụ Trách", readonly=True)
    team_id = fields.Many2one("crm.team", string="Đội Ngũ Bán Hàng", readonly=True)
    stage_id = fields.Many2one("crm.stage", string="Giai Đoạn Phễu", readonly=True)
    stage_sequence = fields.Integer(string="Thứ Tự Giai Đoạn", readonly=True)

    # Omnichannel Channel & Inquiry
    source_system = fields.Selection([
        ('website', 'Public Website'),
        ('facebook', 'Facebook'),
        ('zalo', 'Zalo'),
        ('pancake', 'Pancake POS'),
        ('ota', 'Online Travel Agency'),
        ('partner', 'B2B Partner Referral'),
        ('ai_assistant', 'AI Assistant Human Handoff'),
        ('direct', 'Direct Call / Walk-in'),
    ], string="Kênh Tiếp Nhận (Channel)", readonly=True)

    inquiry_type = fields.Selection([
        ('consultation', 'Tư Vấn Tour / Điểm Đến'),
        ('tour_booking', 'Đặt Tour / Trải Nghiệm'),
        ('partner_inquiry', 'Liên Hệ Đối Tác B2B'),
        ('general_support', 'Hỗ Trợ Khách Hàng'),
    ], string="Loại Nhu Cầu (Inquiry)", readonly=True)

    # Travel Interests
    destination_interest_id = fields.Many2one("travel.destination", string="Điểm Đến Quan Tâm", readonly=True)
    place_interest_id = fields.Many2one("travel.place", string="Danh Thắng / Điểm Trải Nghiệm", readonly=True)
    travel_date_intended = fields.Date(string="Ngày Đi Tour Dự Kiến", readonly=True)

    # Marketing UTM Attribution & Ad Click IDs
    campaign_id = fields.Many2one("utm.campaign", string="Chiến Dịch (UTM Campaign)", readonly=True)
    source_id = fields.Many2one("utm.source", string="Nguồn (UTM Source)", readonly=True)
    medium_id = fields.Many2one("utm.medium", string="Kênh (UTM Medium)", readonly=True)
    utm_term = fields.Char(string="Từ Khóa (UTM Term)", readonly=True)
    utm_content = fields.Char(string="Nội Dung Ad (UTM Content)", readonly=True)
    has_gclid = fields.Boolean(string="Google Ads (GCLID)", readonly=True)
    has_fbclid = fields.Boolean(string="Facebook Ads (FBCLID)", readonly=True)
    ad_network = fields.Selection([
        ('google', 'Google Ads'),
        ('facebook', 'Facebook Ads'),
        ('organic_direct', 'Organic / Tự Nhiên / Khác'),
    ], string="Mạng Quảng Cáo (Ad Network)", readonly=True)

    # Dates
    create_date = fields.Datetime(string="Ngày Tiếp Nhận", readonly=True)
    date_closed = fields.Datetime(string="Ngày Chốt Đơn", readonly=True)
    date_deadline = fields.Date(string="Hạn Chót Xử Lý", readonly=True)

    # Status Flags
    is_won = fields.Boolean(string="Đã Chốt Thắng (Won)", readonly=True)
    is_lost = fields.Boolean(string="Thất Bại (Lost)", readonly=True)
    is_active = fields.Boolean(string="Đang Xử Lý (Active)", readonly=True)

    # Quantitative Measures (KPI Metrics)
    lead_count = fields.Integer(string="Số Lượng Leads", readonly=True)
    traveler_count = fields.Integer(string="Số Khách Đi Tour (Pax)", readonly=True)
    expected_revenue = fields.Monetary(
        string="Doanh Thu Dự Kiến (VNĐ)",
        currency_field="company_currency",
        readonly=True,
    )
    won_revenue = fields.Monetary(
        string="Doanh Thu Đã Chốt (VNĐ)",
        currency_field="company_currency",
        readonly=True,
    )
    probability = fields.Float(string="Xác Suất Chốt (%)", readonly=True)
    revenue_per_traveler = fields.Monetary(
        string="Doanh Thu TB / Khách (VNĐ)",
        currency_field="company_currency",
        readonly=True,
    )
    conversion_days = fields.Float(string="Thời Gian Chốt (Ngày)", readonly=True)
    company_currency = fields.Many2one("res.currency", string="Tiền Tệ", readonly=True)
    company_id = fields.Many2one("res.company", string="Công Ty", readonly=True)

    def init(self):
        """Creates or replaces the analytical database view for high-performance BI reporting."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    l.id AS id,
                    l.id AS lead_id,
                    l.name AS name,
                    l.partner_id AS partner_id,
                    l.user_id AS user_id,
                    l.team_id AS team_id,
                    l.stage_id AS stage_id,
                    COALESCE(s.sequence, 0) AS stage_sequence,
                    COALESCE(l.source_system, 'website') AS source_system,
                    COALESCE(l.inquiry_type, 'consultation') AS inquiry_type,
                    l.destination_interest_id AS destination_interest_id,
                    l.place_interest_id AS place_interest_id,
                    l.travel_date_intended AS travel_date_intended,
                    l.campaign_id AS campaign_id,
                    l.source_id AS source_id,
                    l.medium_id AS medium_id,
                    l.utm_term AS utm_term,
                    l.utm_content AS utm_content,
                    (l.gclid IS NOT NULL AND l.gclid != '') AS has_gclid,
                    (l.fbclid IS NOT NULL AND l.fbclid != '') AS has_fbclid,
                    CASE
                        WHEN l.gclid IS NOT NULL AND l.gclid != '' THEN 'google'
                        WHEN l.fbclid IS NOT NULL AND l.fbclid != '' THEN 'facebook'
                        ELSE 'organic_direct'
                    END AS ad_network,
                    l.create_date AS create_date,
                    l.date_closed AS date_closed,
                    l.date_deadline AS date_deadline,
                    COALESCE(s.is_won, FALSE) AS is_won,
                    (l.active = FALSE AND COALESCE(s.is_won, FALSE) = FALSE) AS is_lost,
                    l.active AS is_active,
                    1 AS lead_count,
                    GREATEST(COALESCE(l.traveler_count, 1), 1) AS traveler_count,
                    COALESCE(l.expected_revenue, 0.0) AS expected_revenue,
                    CASE
                        WHEN COALESCE(s.is_won, FALSE) = TRUE THEN COALESCE(l.expected_revenue, 0.0)
                        ELSE 0.0
                    END AS won_revenue,
                    COALESCE(l.probability, 0.0) AS probability,
                    CASE
                        WHEN GREATEST(COALESCE(l.traveler_count, 1), 1) > 0 THEN
                            ROUND((COALESCE(l.expected_revenue, 0.0)::numeric / GREATEST(COALESCE(l.traveler_count, 1), 1)::numeric), 2)
                        ELSE 0.0
                    END AS revenue_per_traveler,
                    CASE
                        WHEN l.date_closed IS NOT NULL THEN
                            ROUND((EXTRACT(EPOCH FROM (l.date_closed - l.create_date)) / 86400.0)::numeric, 1)
                        ELSE NULL
                    END AS conversion_days,
                    COALESCE(c.currency_id, (SELECT currency_id FROM res_company LIMIT 1)) AS company_currency,
                    l.company_id AS company_id
                FROM crm_lead l
                LEFT JOIN crm_stage s ON l.stage_id = s.id
                LEFT JOIN res_company c ON l.company_id = c.id
            )
        """)
