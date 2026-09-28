from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float
from app.db.session import Base


def utc_now():
    return datetime.now(timezone.utc)


class IdempotencyRecord(Base):
    """
    Bảng lưu vết Idempotency để ngăn chặn double-submission và duplicate webhook
    """
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    endpoint = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_payload = Column(Text, nullable=True)
    status = Column(String(32), default="PROCESSING", index=True)  # PROCESSING, SUCCESS, FAILED
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PaymentTransactionRecord(Base):
    """
    Bảng lưu vết toàn bộ Webhook/IPN nhận từ các cổng thanh toán
    """
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    order_ref = Column(String(64), index=True, nullable=False)
    gateway = Column(String(32), nullable=False)  # vnpay, momo, zalopay, vietqr
    gateway_transaction_id = Column(String(128), index=True, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(32), default="PENDING")  # SUCCESS, FAILED, PENDING
    signature_verified = Column(Boolean, default=False)
    raw_payload = Column(Text, nullable=False)
    odoo_order_id = Column(Integer, nullable=True)
    odoo_synced = Column(Boolean, default=False)
    odoo_sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
