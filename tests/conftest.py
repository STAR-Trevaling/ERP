import hashlib
import hmac
import os
import xmlrpc.client

import pytest

ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo_travel")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "star_travels_super_secret_webhook_key_2026")
API_KEY = os.environ.get("API_KEY", "star_travels_inbound_api_token_2026")


@pytest.fixture(scope="session")
def odoo_url():
    return ODOO_URL


@pytest.fixture(scope="session")
def webhook_secret():
    return WEBHOOK_SECRET


@pytest.fixture(scope="session")
def inbound_api_key():
    return API_KEY


@pytest.fixture(scope="session")
def hmac_signer():
    def _sign(body_bytes: bytes, secret: str = WEBHOOK_SECRET) -> str:
        return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return _sign


@pytest.fixture(scope="session")
def odoo_rpc():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    assert uid, f"Failed to authenticate against Odoo at {ODOO_URL} with DB {ODOO_DB}"
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    class OdooRPCClient:
        def __init__(self, db, uid, password, models_proxy):
            self.db = db
            self.uid = uid
            self.password = password
            self.models = models_proxy

        def execute(self, model, method, *args, **kwargs):
            pos_args = list(args)
            call_kw = dict(kwargs)
            if pos_args and isinstance(pos_args[-1], dict) and not call_kw and method in ("search", "search_read", "read", "search_count"):
                call_kw = pos_args.pop()
            res = self.models.execute_kw(self.db, self.uid, self.password, model, method, pos_args, call_kw)
            if method == "create" and isinstance(res, list) and len(res) == 1:
                return res[0]
            return res

    return OdooRPCClient(ODOO_DB, uid, ODOO_PASSWORD, models)
