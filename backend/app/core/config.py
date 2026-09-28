import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Retail ERP E-commerce Middleware"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ODOO RPC SETTINGS
    ODOO_URL: str = "http://127.0.0.1:8069"
    ODOO_DB: str = "odoo_retail_db"
    ODOO_USER: str = "integration_api_user"
    ODOO_API_KEY: str = "odoo_api_key_placeholder"

    # DATABASE (Idempotency & Transaction log)
    DATABASE_URL: str = "sqlite+aiosqlite:///./ecommerce_bridge.db"

    # PAYMENT GATEWAYS
    VNPAY_TMN_CODE: str = "TEST_TMN"
    VNPAY_HASH_SECRET: str = "SECRET_HASH_KEY_VNPAY_512"
    VNPAY_PAY_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"

    MOMO_PARTNER_CODE: str = "MOMOPARTNER123"
    MOMO_ACCESS_KEY: str = "MOMOACCESSKEY123"
    MOMO_SECRET_KEY: str = "MOMOSECRETKEY123"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
