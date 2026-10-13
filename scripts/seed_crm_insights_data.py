# -*- coding: utf-8 -*-
"""
Seed realistic demo leads and marketing attribution for Star Travels Insights Dashboard.
Channels: Website, Facebook, Zalo, Pancake, OTA, AI Assistant
Marketing: Google Ads (GCLID), Facebook Ads (FBCLID), UTM Campaigns
"""
import random
from datetime import datetime, timedelta
import odoo
from odoo import registry

DB_NAME = 'odoo_travel'

SAMPLE_LEADS = [
    {
        'name': '[WEB/GoogleAds] Combo Tour Du Thuyền Hạ Long 3N2D VIP',
        'contact_name': 'Nguyễn Hoàng Long',
        'phone': '0901234567',
        'email': 'hoanglong.nguyen@gmail.com',
        'source_system': 'website',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'ha-long',
        'place_slug': 'canal-cruise',
        'traveler_count': 4,
        'expected_revenue': 28000000.0,
        'stage_name': 'Won',
        'campaign': 'Mua_He_Vang_2026',
        'source': 'Google_Search',
        'medium': 'cpc',
        'utm_term': 'du thuyen ha long 5 sao gia tot',
        'gclid': 'CjwKCAjw_TEST_GCLID_HA_LONG_001',
        'days_ago': 12,
    },
    {
        'name': '[FB/Ads] Tour Lặn San Hô & Cáp Treo Hòn Thơm Phú Quốc',
        'contact_name': 'Trần Mai Phương',
        'phone': '0912345678',
        'email': 'maiphuong.tran@outlook.com',
        'source_system': 'facebook',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'phu-quoc',
        'place_slug': 'scuba-diving',
        'traveler_count': 2,
        'expected_revenue': 14500000.0,
        'stage_name': 'Won',
        'campaign': 'Kham_Pha_Dao_Ngoc',
        'source': 'Facebook_Ads',
        'medium': 'cpc',
        'utm_term': 'lan bien phu quoc cap treo',
        'fbclid': 'IwAR2_TEST_FBCLID_PHU_QUOC_002',
        'days_ago': 8,
    },
    {
        'name': '[ZALO/Chat] Tư vấn Tour Nghỉ Dưỡng Gia Đình Đà Nẵng - Hội An',
        'contact_name': 'Lê Hoàng Nam',
        'phone': '0988112233',
        'email': 'nam.le@vietnamtravel.vn',
        'source_system': 'zalo',
        'inquiry_type': 'consultation',
        'dest_slug': 'da-nang',
        'place_slug': 'hoi-an-lantern-boat',
        'traveler_count': 6,
        'expected_revenue': 42000000.0,
        'stage_name': 'Proposition',
        'campaign': 'Gia_Dinh_Sum_Vay',
        'source': 'Zalo_OA',
        'medium': 'chat',
        'days_ago': 4,
    },
    {
        'name': '[PANCAKE/Fanpage] Đặt Chỗ Săn Mây Tà Xùa & Cắm Trại Cao Cấp',
        'contact_name': 'Vũ Thị Minh Hạnh',
        'phone': '0977445566',
        'email': 'hanh.vu@techcorp.vn',
        'source_system': 'pancake',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'ta-xua',
        'place_slug': 'camping',
        'traveler_count': 5,
        'expected_revenue': 18500000.0,
        'stage_name': 'Won',
        'campaign': 'San_May_Dai_Ngan',
        'source': 'Pancake_POS',
        'medium': 'social_inbox',
        'days_ago': 6,
    },
    {
        'name': '[WEB/SEO] Trekking Chinh Phục Nóc Nhà Đông Dương Fansipan',
        'contact_name': 'Đặng Quốc Huy',
        'phone': '0933556677',
        'email': 'huy.dang@adventure.com',
        'source_system': 'website',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'sa-pa',
        'place_slug': 'hiking',
        'traveler_count': 8,
        'expected_revenue': 36000000.0,
        'stage_name': 'Won',
        'campaign': 'Adventure_Vietnam_2026',
        'source': 'Google_Organic',
        'medium': 'organic',
        'days_ago': 15,
    },
    {
        'name': '[FB/Ads] Trải Nghiệm Du Thuyền Hạ Long 2N1D Cuối Tuần',
        'contact_name': 'Bùi Ngọc Trâm',
        'phone': '0944667788',
        'email': 'tram.bui@gmail.com',
        'source_system': 'facebook',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'ha-long',
        'place_slug': 'ha-long-cruise',
        'traveler_count': 2,
        'expected_revenue': 11000000.0,
        'stage_name': 'Qualified',
        'campaign': 'Weekend_Escape',
        'source': 'Facebook_Ads',
        'medium': 'cpc',
        'fbclid': 'IwAR3_TEST_FBCLID_HALONG_CRUISE_003',
        'days_ago': 3,
    },
    {
        'name': '[AI_ASSISTANT] Tư vấn Lịch trình Khám phá Côn Đảo Tâm Linh & Nghỉ Dưỡng',
        'contact_name': 'Phạm Thu Hương',
        'phone': '0966778899',
        'email': 'thuhuong.pham@fpt.com.vn',
        'source_system': 'ai_assistant',
        'inquiry_type': 'consultation',
        'dest_slug': 'con-dao',
        'traveler_count': 3,
        'expected_revenue': 24000000.0,
        'stage_name': 'New',
        'source': 'AI_Chatbot',
        'medium': 'ai_handoff',
        'days_ago': 1,
    },
    {
        'name': '[OTA/Klook] Khám phá Quần thể Danh thắng Tràng An Ninh Bình',
        'contact_name': 'Alexandre Dupont',
        'phone': '0899112233',
        'email': 'alex.dupont@traveler.fr',
        'source_system': 'ota',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'ninh-binh',
        'place_slug': 'trang-an-boat-tour',
        'traveler_count': 2,
        'expected_revenue': 6500000.0,
        'stage_name': 'Won',
        'source': 'Klook_Partner',
        'medium': 'affiliate_api',
        'days_ago': 10,
    },
    {
        'name': '[WEB/GoogleAds] Trải Nghiệm Chèo Kayak Vịnh Lan Hạ Hoang Sơ',
        'contact_name': 'Trịnh Công Sơn',
        'phone': '0918273645',
        'email': 'son.trinh@music.vn',
        'source_system': 'website',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'ha-long',
        'place_slug': 'kayak-lan-ha',
        'traveler_count': 4,
        'expected_revenue': 16000000.0,
        'stage_name': 'Proposition',
        'campaign': 'Mua_He_Vang_2026',
        'source': 'Google_Search',
        'medium': 'cpc',
        'gclid': 'CjwKCAjw_TEST_GCLID_LAN_HA_004',
        'days_ago': 5,
    },
    {
        'name': '[ZALO/Direct] Tour Khám Phá Cao Nguyên Đá Hà Giang Mùa Hoa Tam Giác Mạch',
        'contact_name': 'Hoàng Văn Bách',
        'phone': '0987654321',
        'email': 'bach.hoang@vinamilk.vn',
        'source_system': 'zalo',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'ha-giang',
        'traveler_count': 12,
        'expected_revenue': 78000000.0,
        'stage_name': 'Won',
        'campaign': 'Mua_Hoa_Tam_Giac_Mach',
        'source': 'Zalo_OA',
        'medium': 'direct_zalo',
        'days_ago': 14,
    },
    {
        'name': '[WEB/GoogleAds] Du Lịch Đà Lạt Thành Phố Ngàn Hoa 3N2D',
        'contact_name': 'Đỗ Mỹ Linh',
        'phone': '0922334455',
        'email': 'mylinh.do@vtv.vn',
        'source_system': 'website',
        'inquiry_type': 'tour_booking',
        'dest_slug': 'da-lat',
        'traveler_count': 2,
        'expected_revenue': 9800000.0,
        'stage_name': 'Qualified',
        'campaign': 'Mua_He_Vang_2026',
        'source': 'Google_Search',
        'medium': 'cpc',
        'gclid': 'CjwKCAjw_TEST_GCLID_DA_LAT_005',
        'days_ago': 2,
    },
]

def seed_insights():
    reg = registry(DB_NAME)
    with reg.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

        dest_model = env['travel.destination']
        place_model = env['travel.place']
        stage_model = env['crm.stage']
        partner_model = env['res.partner']
        lead_model = env['crm.lead']
        camp_model = env['utm.campaign']
        source_model = env['utm.source']
        med_model = env['utm.medium']

        stages = {s.name: s for s in stage_model.search([])}
        now = datetime.now()

        created_count = 0
        for item in SAMPLE_LEADS:
            # Match destination
            dest = dest_model.search([('slug', '=', item.get('dest_slug'))], limit=1)
            place = place_model.search([('slug', '=', item.get('place_slug'))], limit=1) if item.get('place_slug') else False

            # Match partner
            partner = partner_model.search([('phone', '=', item['phone'])], limit=1)
            if not partner:
                partner = partner_model.create({
                    'name': item['contact_name'],
                    'phone': item['phone'],
                    'email': item['email'],
                })

            # Match UTM
            camp_id = False
            if item.get('campaign'):
                c = camp_model.search([('name', '=ilike', item['campaign'])], limit=1)
                camp_id = c.id if c else camp_model.create({'name': item['campaign']}).id

            source_id = False
            if item.get('source'):
                s = source_model.search([('name', '=ilike', item['source'])], limit=1)
                source_id = s.id if s else source_model.create({'name': item['source']}).id

            med_id = False
            if item.get('medium'):
                m = med_model.search([('name', '=ilike', item['medium'])], limit=1)
                med_id = m.id if m else med_model.create({'name': item['medium']}).id

            # Stage
            stg = stages.get(item['stage_name']) or stages.get('New')
            is_won = bool(stg and stg.is_won)

            create_dt = now - timedelta(days=item.get('days_ago', 1))
            close_dt = (create_dt + timedelta(days=random.randint(1, 4))) if is_won else None

            # Check if lead exists
            existing = lead_model.search([('name', '=', item['name'])], limit=1)
            if existing:
                continue

            lead_vals = {
                'name': item['name'],
                'partner_id': partner.id,
                'contact_name': item['contact_name'],
                'phone': item['phone'],
                'email_from': item['email'],
                'source_system': item['source_system'],
                'inquiry_type': item['inquiry_type'],
                'destination_interest_id': dest.id if dest else False,
                'place_interest_id': place.id if place else False,
                'traveler_count': item.get('traveler_count', 2),
                'expected_revenue': item.get('expected_revenue', 0.0),
                'probability': 100.0 if is_won else (70.0 if stg.name == 'Proposition' else (40.0 if stg.name == 'Qualified' else 10.0)),
                'stage_id': stg.id if stg else False,
                'campaign_id': camp_id,
                'source_id': source_id,
                'medium_id': med_id,
                'utm_term': item.get('utm_term'),
                'gclid': item.get('gclid'),
                'fbclid': item.get('fbclid'),
                'travel_date_intended': (now + timedelta(days=random.randint(15, 60))).date(),
                'create_date': create_dt,
                'date_closed': close_dt,
            }
            lead = lead_model.create(lead_vals)
            # Update dates via SQL since create_date is overridden on create
            cr.execute(
                "UPDATE crm_lead SET create_date = %s, date_closed = %s WHERE id = %s",
                (create_dt, close_dt, lead.id)
            )
            created_count += 1

        cr.commit()
        print(f"Successfully seeded {created_count} realistic omnichannel CRM insights leads into database {DB_NAME}.")

if __name__ == '__main__':
    seed_insights()
