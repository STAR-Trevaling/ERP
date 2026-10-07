#!/usr/bin/env python3
"""
Seed Odoo 18 CMS with STAR Travels Vietnam Data via XML-RPC.
Can be executed against local running Odoo (http://localhost:8069).
"""

import logging
import os
import xmlrpc.client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("seed_odoo_cms")

ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo_travel")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")


def run_seed():
    logger.info(f"Connecting to Odoo at {ODOO_URL} (DB: {ODOO_DB})...")
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            logger.error("Authentication failed! Check credentials.")
            return False
        logger.info(f"Authenticated successfully as user ID: {uid}")

        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

        # 1. Categories
        categories = [
            ("van-hoa-di-san", "Văn hóa & Di sản", "landmark"),
            ("du-thuyen", "Du thuyền & Nghỉ dưỡng", "ship"),
            ("the-thao-nuoc", "Thể thao nước", "waves"),
            ("trekking-leo-nui", "Trekking & Leo núi", "mountain"),
            ("cam-trai-da-ngoai", "Cắm trại dã ngoại", "tent"),
            ("lan-bien-san-ho", "Lặn biển san hô", "compass"),
            ("kayak-the-thao-nuoc", "Kayak & Chèo SUP", "navigation"),
            ("am-thuc-dia-phuong", "Ẩm thực địa phương", "utensils"),
        ]
        cat_map = {}
        for slug, name, icon in categories:
            cat_ids = models.execute_kw(
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "travel.category",
                "search",
                [[("slug", "=", slug)]],
            )
            if cat_ids:
                cat_id = cat_ids[0]
            else:
                cat_id = models.execute_kw(
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "travel.category",
                    "create",
                    [{"name": name, "slug": slug, "icon": icon, "active": True}],
                )
            cat_map[slug] = cat_id
            logger.info(f"Category '{slug}' -> ID {cat_id}")

        # 2. Check destination count
        dest_count = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD, "travel.destination", "search_count", [[]]
        )
        logger.info(f"Total destinations currently in Odoo: {dest_count}")

        return True
    except (xmlrpc.client.Error, OSError) as e:
        logger.error(f"Network/RPC error connecting or seeding Odoo: {e}")
        return False
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error seeding Odoo: {e}")
        return False


if __name__ == "__main__":
    run_seed()
