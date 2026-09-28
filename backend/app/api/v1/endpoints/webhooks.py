import logging
import json
from datetime import datetime
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db, AsyncSessionLocal
from app.models.idempotency import PaymentTransactionRecord
from app.services.payment_verifier import PaymentSignatureVerifier
from app.core.odoo_client import odoo_client, OdooRPCError

logger = logging.getLogger(__name__)
router = APIRouter()


async def background_sync_payment_to_odoo(transaction_id: int):
    """
    Task chạy nền (BackgroundTask): Gọi Odoo 18 để ghi nhận thanh toán
    vào đúng Payment Journal tương ứng của cổng (VNPay/MoMo).
    """
    async with AsyncSessionLocal() as session:
        stmt = select(PaymentTransactionRecord).where(PaymentTransactionRecord.id == transaction_id)
        result = await session.execute(stmt)
        record = result.scalars().first()
        if not record:
            logger.error(f"[BG-SYNC] Cannot find transaction record ID {transaction_id}")
            return

        if record.odoo_synced:
            logger.info(f"[BG-SYNC] Transaction {record.gateway_transaction_id} already synced to Odoo.")
            return

        journal_code = "VNPAY" if record.gateway == "vnpay" else "MOMO"

        try:
            # Tra cứu odoo_order_id nếu chưa có sẵn (tìm qua web_order_ref)
            odoo_order_id = record.odoo_order_id
            if not odoo_order_id:
                search_res = await odoo_client.execute_kw(
                    model="sale.order",
                    method="search",
                    args=[[[("web_order_ref", "=", record.order_ref)]]]
                )
                if search_res:
                    odoo_order_id = search_res[0]
                    record.odoo_order_id = odoo_order_id

            if not odoo_order_id:
                logger.error(f"[BG-SYNC] Order with web_ref {record.order_ref} not found in Odoo.")
                record.odoo_sync_error = f"Order {record.order_ref} not found in Odoo"
                await session.commit()
                return

            # Gọi RPC xác nhận thanh toán
            payment_payload = {
                "odoo_order_id": odoo_order_id,
                "gateway_transaction_id": record.gateway_transaction_id,
                "payment_journal_code": journal_code,
                "amount_paid": record.amount,
                "payment_date": record.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }

            res = await odoo_client.confirm_web_payment(payment_payload)
            if res.get("status") == "success":
                record.odoo_synced = True
                record.odoo_sync_error = None
                logger.info(f"[BG-SYNC] Successfully synced payment {record.gateway_transaction_id} to Odoo Order {odoo_order_id}")
            else:
                record.odoo_sync_error = res.get("message", "Unknown error from Odoo")
                logger.error(f"[BG-SYNC] Failed to confirm payment in Odoo: {record.odoo_sync_error}")

            await session.commit()

        except Exception as e:
            logger.error(f"[BG-SYNC] Exception syncing payment to Odoo: {str(e)}", exc_info=True)
            record.odoo_sync_error = str(e)
            await session.commit()


@router.api_route("/vnpay", methods=["GET", "POST"])
async def vnpay_ipn_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Xử lý Webhook IPN từ VNPay:
    - Bắt buộc kiểm tra chữ ký (Signature Verification)
    - Bắt buộc kiểm tra Idempotency
    - Phản hồi 200 OK ngay lập tức theo định dạng VNPay mong đợi
    - Bắn BackgroundTask đẩy dữ liệu vào Odoo 18
    """
    if request.method == "GET":
        params = dict(request.query_params)
    else:
        # Hỗ trợ cả form data hoặc json
        form_data = await request.form()
        params = dict(form_data) if form_data else await request.json()

    logger.info(f"[VNPAY-WEBHOOK] Received IPN for order {params.get('vnp_TxnRef')}")

    # 1. Verify chữ ký điện tử
    is_valid_signature = PaymentSignatureVerifier.verify_vnpay_signature(params)
    if not is_valid_signature:
        logger.warning(f"[VNPAY-WEBHOOK] Invalid signature for TxnRef: {params.get('vnp_TxnRef')}")
        return {"RspCode": "97", "Message": "Invalid Checksum"}

    order_ref = params.get("vnp_TxnRef", "")
    trans_no = params.get("vnp_TransactionNo", "")
    response_code = params.get("vnp_ResponseCode", "")
    raw_amount = float(params.get("vnp_Amount", "0")) / 100.0  # VNPay nhân 100

    # 2. Kiểm tra Idempotency
    stmt = select(PaymentTransactionRecord).where(
        PaymentTransactionRecord.gateway == "vnpay",
        PaymentTransactionRecord.gateway_transaction_id == trans_no
    )
    result = await db.execute(stmt)
    existing_tx = result.scalars().first()

    if existing_tx and existing_tx.status == "SUCCESS":
        logger.info(f"[VNPAY-WEBHOOK] Transaction {trans_no} already processed (Idempotency).")
        return {"RspCode": "02", "Message": "Order already confirmed"}

    # 3. Ghi nhận giao dịch vào DB
    is_success = (response_code == "00")
    tx_record = PaymentTransactionRecord(
        order_ref=order_ref,
        gateway="vnpay",
        gateway_transaction_id=trans_no,
        amount=raw_amount,
        status="SUCCESS" if is_success else "FAILED",
        signature_verified=True,
        raw_payload=json.dumps(params)
    )
    db.add(tx_record)
    await db.commit()
    await db.refresh(tx_record)

    # 4. Nếu thanh toán thành công -> Đẩy vào BackgroundTasks để đồng bộ Odoo
    if is_success:
        background_tasks.add_task(background_sync_payment_to_odoo, tx_record.id)

    return {"RspCode": "00", "Message": "Confirm Success"}


@router.post("/momo")
async def momo_ipn_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Xử lý Webhook IPN từ MoMo
    """
    payload = await request.json()
    logger.info(f"[MOMO-WEBHOOK] Received IPN for order {payload.get('orderId')}")

    # 1. Verify chữ ký điện tử
    is_valid_signature = PaymentSignatureVerifier.verify_momo_signature(payload)
    if not is_valid_signature:
        logger.warning(f"[MOMO-WEBHOOK] Invalid signature for orderId: {payload.get('orderId')}")
        return {"resultCode": 99, "message": "Invalid signature"}

    order_ref = payload.get("orderId", "")
    trans_id = str(payload.get("transId", ""))
    result_code = payload.get("resultCode", -1)
    amount = float(payload.get("amount", 0))

    # 2. Kiểm tra Idempotency
    stmt = select(PaymentTransactionRecord).where(
        PaymentTransactionRecord.gateway == "momo",
        PaymentTransactionRecord.gateway_transaction_id == trans_id
    )
    res = await db.execute(stmt)
    existing_tx = res.scalars().first()

    if existing_tx and existing_tx.status == "SUCCESS":
        logger.info(f"[MOMO-WEBHOOK] Transaction {trans_id} already confirmed.")
        return {"resultCode": 0, "message": "Order already confirmed"}

    # 3. Ghi nhận giao dịch vào DB
    is_success = (result_code == 0)
    tx_record = PaymentTransactionRecord(
        order_ref=order_ref,
        gateway="momo",
        gateway_transaction_id=trans_id,
        amount=amount,
        status="SUCCESS" if is_success else "FAILED",
        signature_verified=True,
        raw_payload=json.dumps(payload)
    )
    db.add(tx_record)
    await db.commit()
    await db.refresh(tx_record)

    # 4. Chạy background task
    if is_success:
        background_tasks.add_task(background_sync_payment_to_odoo, tx_record.id)

    return {"resultCode": 0, "message": "Success"}
