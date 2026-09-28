from typing import List, Optional
from pydantic import BaseModel, Field


class OrderLineItem(BaseModel):
    sku: str = Field(..., description="Mã SKU sản phẩm khớp default_code trong Odoo")
    qty: float = Field(..., gt=0, description="Số lượng đặt")
    price_unit: float = Field(..., ge=0, description="Đơn giá niêm yết")


class ShippingAddress(BaseModel):
    street: str
    city: str
    district: Optional[str] = None


class CustomerInfo(BaseModel):
    name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=9, max_length=15)
    email: Optional[str] = None
    shipping_address: ShippingAddress


class CheckoutRequest(BaseModel):
    client_order_ref: str = Field(..., description="Mã đơn hàng duy nhất từ Website Frontend")
    customer: CustomerInfo
    payment_method: str = Field("vnpay", description="vnpay, momo, zalopay, vietqr, cod")
    hold_minutes: int = Field(15, ge=5, le=60, description="Số phút giữ chỗ tồn kho")
    order_lines: List[OrderLineItem]


class CheckoutResponse(BaseModel):
    status: str
    client_order_ref: str
    odoo_order_id: int
    odoo_name: str
    hold_expires_at: str
    total_amount: float
    payment_url: Optional[str] = None
    message: Optional[str] = None
