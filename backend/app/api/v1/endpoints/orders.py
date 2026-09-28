import logging
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.idempotency import IdempotencyRecord
from app.schemas.order import CheckoutRequest, CheckoutResponse
from app.core.odoo_client import odoo_client, OdooRPCError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout_order(
    request: CheckoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Tạo đơn hàng online & khóa giữ tồn kho tạm thời (15 phút) trong Odoo 18.
    Bảo vệ Idempotency bằng client_order_ref.
    """
    idempotency_key = f"checkout_{request.client_order_ref}"

    # 1. Kiểm tra Idempotency DB
    stmt = select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key)
    result = await db.execute(stmt)
    existing_rec = result.scalars().first()

    if existing_rec and existing_rec.status == "SUCCESS" and existing_rec.response_payload:
        logger.info(f"[CHECKOUT] Returning cached response for idempotency key: {idempotency_key}")
        return json.loads(existing_rec.response_payload)

    # Đánh dấu đang xử lý
    if not existing_rec:
        rec = IdempotencyRecord(
            idempotency_key=idempotency_key,
            endpoint="/api/v1/orders/checkout",
            request_hash=request.client_order_ref,
            status="PROCESSING"
        )
        db.add(rec)
        await db.commit()

    # 2. Gọi sang Odoo 18 Atomic API
    try:
        odoo_payload = {
            "client_order_ref": request.client_order_ref,
            "customer": request.customer.model_dump(),
            "hold_minutes": request.hold_minutes,
            "payment_method": request.payment_method,
            "order_lines": [item.model_dump() for item in request.order_lines]
        }

        odoo_res = await odoo_client.create_web_order_atomic(odoo_payload)

        if odoo_res.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": odoo_res.get("code", "UNKNOWN_ERROR"),
                    "message": odoo_res.get("message", "Không thể tạo đơn hàng trên Odoo")
                }
            )

        # 3. Giả lập URL thanh toán chuyển tiếp tới cổng
        payment_url = None
        if request.payment_method == "vnpay":
            payment_url = f"https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_TxnRef={request.client_order_ref}&vnp_Amount={int(odoo_res['amount_total'] * 100)}"
        elif request.payment_method == "momo":
            payment_url = f"https://test-payment.momo.vn/v2/gateway/pay?orderId={request.client_order_ref}&amount={int(odoo_res['amount_total'])}"

        response_data = {
            "status": "success",
            "client_order_ref": request.client_order_ref,
            "odoo_order_id": odoo_res["odoo_order_id"],
            "odoo_name": odoo_res["odoo_name"],
            "hold_expires_at": odoo_res["hold_expires_at"],
            "total_amount": odoo_res["amount_total"],
            "payment_url": payment_url,
            "message": "Đơn hàng đã được tạo và giữ tồn kho thành công"
        }

        # 4. Cập nhật Idempotency DB thành công
        rec_update = await db.execute(stmt)
        record_to_update = rec_update.scalars().first()
        if record_to_update:
            record_to_update.status = "SUCCESS"
            record_to_update.response_payload = json.dumps(response_data)
            await db.commit()

        return response_data

    except HTTPException:
        raise
    except OdooRPCError as e:
        logger.error(f"[CHECKOUT] Odoo RPC error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error_code": e.code, "message": e.message}
        )
    except Exception as e:
        logger.error(f"[CHECKOUT] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)}
        )
