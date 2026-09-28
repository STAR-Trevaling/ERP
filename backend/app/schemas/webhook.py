from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class VNPayWebhookPayload(BaseModel):
    vnp_TmnCode: str
    vnp_Amount: str
    vnp_BankCode: Optional[str] = None
    vnp_BankTranNo: Optional[str] = None
    vnp_CardType: Optional[str] = None
    vnp_PayDate: Optional[str] = None
    vnp_OrderInfo: Optional[str] = None
    vnp_TransactionNo: str
    vnp_ResponseCode: str
    vnp_TransactionStatus: str
    vnp_TxnRef: str  # client_order_ref
    vnp_SecureHash: str


class MoMoWebhookPayload(BaseModel):
    partnerCode: str
    orderId: str  # client_order_ref
    requestId: str
    amount: int
    orderInfo: Optional[str] = None
    orderType: Optional[str] = None
    transId: int
    resultCode: int  # 0: Thành công
    message: Optional[str] = None
    payType: Optional[str] = None
    responseTime: int
    extraData: Optional[str] = ""
    signature: str


class WebhookResponse(BaseModel):
    RspCode: str = Field(..., description="Mã phản hồi cho cổng (VD: 00 là thành công cho VNPay)")
    Message: str
